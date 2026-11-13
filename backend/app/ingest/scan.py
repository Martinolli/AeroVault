"""Library scanner: discover PDFs, classify collections, detect changes by SHA-256."""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .collections import COLLECTIONS, EXCLUDE_PARTS, classify_path


def sha256_file(path: Path, buf_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(buf_size):
            h.update(chunk)
    return h.hexdigest()


def iter_pdfs(root: Path):
    """Walk only the three collection folders (never the whole library root)."""
    for prefix in COLLECTIONS.values():
        collection_root = root / Path(prefix)
        if not collection_root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(collection_root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_PARTS]
            for name in filenames:
                if name.lower().endswith(".pdf"):
                    yield Path(dirpath) / name


def scan(root: Path, conn) -> dict:
    """Walk the library and upsert documents. Returns counts by status."""
    existing = {
        r["rel_path"]: (r["id"], r["sha256"], r["status"])
        for r in conn.execute("SELECT id, rel_path, sha256, status FROM documents")
    }
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    counts = {"new": 0, "changed": 0, "unchanged": 0, "unreadable": 0, "skipped": 0}
    seen = 0

    for path in iter_pdfs(root):
        seen += 1
        if seen % 25 == 0:
            print(f"  scanned {seen} files...", file=sys.stderr, flush=True)
        rel = path.relative_to(root).as_posix()
        collection = classify_path(rel)
        if collection is None:
            counts["skipped"] += 1
            continue
        try:
            sha = sha256_file(path)
            size_mb = round(path.stat().st_size / (1024 * 1024), 3)
        except OSError:
            counts["unreadable"] += 1
            continue

        prev = existing.get(rel)
        if prev is None:
            status = "pending"
            counts["new"] += 1
        elif prev[1] == sha:
            status = prev[2]
            counts["unchanged"] += 1
        else:
            status = "pending"
            counts["changed"] += 1

        conn.execute(
            "INSERT INTO documents (rel_path, collection, title, size_mb, sha256, status, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(rel_path) DO UPDATE SET "
            "collection = excluded.collection, title = excluded.title, size_mb = excluded.size_mb, "
            "sha256 = excluded.sha256, status = excluded.status, updated_at = excluded.updated_at",
            (rel, collection, path.stem, size_mb, sha, status, now),
        )

    conn.commit()
    return counts
