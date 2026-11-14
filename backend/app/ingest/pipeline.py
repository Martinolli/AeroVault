"""Ingestion CLI.

Usage (inside the backend container or natively):
    python -m app.ingest.pipeline scan  [--root /library]
    python -m app.ingest.pipeline ingest [--limit N] [--collection NAME] [--ocr] [--no-vectors] [--force]
    python -m app.ingest.pipeline vectors-only [--limit N]
    python -m app.ingest.pipeline status

Statuses: pending -> text_only (text index done, vectors pending) -> indexed (vectors done);
partial = low text coverage; error = unreadable.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.config import settings

from .chunk import chunk_page, estimate_tokens
from .embed import embed_texts
from .extract import extract_pages
from .scan import scan
from .store import (
    connect,
    reset_document,
    save_chunks,
    save_pages,
    set_status,
    set_vectors,
    stats,
)


def _lance_upsert(lance_dir: Path, doc_id: int, records: list[dict]) -> None:
    import lancedb

    db = lancedb.connect(str(lance_dir))
    if "chunks" in db.list_tables().tables:
        table = db.open_table("chunks")
        table.delete(f"document_id = {doc_id}")
        if records:
            table.add(records)
    elif records:
        db.create_table("chunks", data=records)


def _embed_document(conn, lance_dir: Path, doc_id: int, api_key: str) -> int:
    """Embed all chunks of a document and upsert vectors. Returns chunk count."""
    rows = conn.execute(
        "SELECT id, page_no, text FROM chunks WHERE document_id = ? ORDER BY id", (doc_id,)
    ).fetchall()
    if not rows:
        return 0
    vectors = embed_texts([r["text"] for r in rows], settings.embedding_model, api_key)
    records = [
        {"vector": vec, "document_id": doc_id, "page_no": rows[i]["page_no"], "chunk_id": rows[i]["id"]}
        for i, vec in enumerate(vectors)
    ]
    _lance_upsert(lance_dir, doc_id, records)
    return len(rows)


def cmd_scan(args: argparse.Namespace, conn) -> None:
    root = Path(args.root)
    if not root.exists():
        sys.exit(f"Library root not found: {root}")
    t0 = time.time()
    counts = scan(root, conn)
    print(json.dumps({"root": str(root), "seconds": round(time.time() - t0, 1), **counts}))


def cmd_status(args: argparse.Namespace, conn) -> None:
    print(json.dumps(stats(conn), indent=2))


def _select_docs(conn, args, where: str, extra: str = ""):
    sql = f"SELECT * FROM documents WHERE {where}"
    params: list = []
    if args.collection:
        sql += " AND collection = ?"
        params.append(args.collection)
    if getattr(args, "path_substring", None):
        sql += " AND rel_path LIKE ?"
        params.append(f"%{args.path_substring}%")
    sql += extra
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"
    return conn.execute(sql, params).fetchall()


def _load_passwords(data_dir: Path) -> dict:
    path = data_dir / "pdf_passwords.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def cmd_ingest(args: argparse.Namespace, conn) -> None:
    root = Path(args.root)
    lance_dir = Path(args.lance)
    passwords = _load_passwords(Path(args.db).parent)
    if getattr(args, "only_ocr", False):
        where = "status = 'text_only' AND pages > 0"
        order = (
            " ORDER BY CASE collection WHEN 'Aviation HF' THEN 0 "
            "WHEN 'Quality ISO SAE' THEN 1 ELSE 2 END, pages ASC"
        )
    else:
        where = "status IN ('pending', 'partial')" if not args.force else "1 = 1"
        order = " ORDER BY size_mb ASC"
    docs = _select_docs(conn, args, where, order)
    if not docs:
        print("Nothing to ingest.")
        return

    api_key = settings.openai_api_key
    use_vectors = not args.no_vectors and bool(api_key)
    if not use_vectors:
        print("Vectors disabled: text index only (run 'vectors-only' later to backfill).")

    done = 0
    for doc in docs:
        path = root / doc["rel_path"]
        t0 = time.time()
        try:
            pages, engine = extract_pages(
                path, ocr=args.ocr, password=passwords.get(doc["rel_path"], "")
            )
        except Exception as exc:  # noqa: BLE001
            set_status(conn, doc["id"], "error", error=f"{type(exc).__name__}: {exc}"[:500])
            conn.commit()
            print(f"ERROR  {doc['rel_path']}: {exc}")
            continue

        text_pages = sum(1 for p in pages if len(p.text.strip()) >= 50)
        ocr_pages = sum(1 for p in pages if p.ocr_used)
        status = "indexed" if text_pages >= 0.9 * max(len(pages), 1) else "partial"
        if not use_vectors:
            status = "text_only"
        if getattr(args, "only_ocr", False) and text_pages == 0:
            set_status(conn, doc["id"], "error", error="OCR produced no text", pages=len(pages))
            conn.commit()
            print(f"OCR EMPTY {doc['rel_path']}")
            continue

        reset_document(conn, doc["id"])
        save_pages(conn, doc["id"], pages)
        chunk_rows: list[tuple] = []
        for p in pages:
            for i, text in enumerate(chunk_page(p.text)):
                chunk_rows.append((p.page_no, i, text, estimate_tokens(text)))
        save_chunks(conn, doc["id"], chunk_rows)
        set_status(conn, doc["id"], status, len(pages), text_pages, ocr_pages, None)
        set_vectors(conn, doc["id"], False)
        conn.commit()

        vector_note = ""
        if use_vectors:
            try:
                n = _embed_document(conn, lance_dir, doc["id"], api_key)
                set_vectors(conn, doc["id"], True)
                conn.commit()
                vector_note = f" vectors={n}"
            except Exception as exc:  # noqa: BLE001
                set_status(conn, doc["id"], "text_only", error=f"vectors: {exc}"[:500])
                conn.commit()
                print(f"VECTORS FAILED {doc['rel_path']}: {exc}")

        done += 1
        print(
            f"[{done}/{len(docs)}] {status:9s} {len(pages):5d} pp  "
            f"{len(chunk_rows):5d} ch  {engine:7s} {time.time() - t0:5.1f}s  {doc['rel_path']}{vector_note}"
        )

    print(json.dumps(stats(conn), indent=2))


def cmd_ocr(args: argparse.Namespace, conn) -> None:
    """OCR documents that have no text layer (status text_only, pages > 0)."""
    args.only_ocr = True
    args.ocr = True
    args.force = False
    cmd_ingest(args, conn)


def cmd_vectors_only(args: argparse.Namespace, conn) -> None:
    lance_dir = Path(args.lance)
    api_key = settings.openai_api_key
    if not api_key:
        sys.exit("No AEROVAULT_OPENAI_API_KEY set.")
    docs = _select_docs(
        conn, args, "vectors = 0 AND status IN ('text_only', 'indexed', 'partial')",
        " AND id IN (SELECT DISTINCT document_id FROM chunks) ORDER BY id",
    )
    if not docs:
        print("No documents need vectors.")
        return
    for i, doc in enumerate(docs, start=1):
        try:
            n = _embed_document(conn, lance_dir, doc["id"], api_key)
            set_vectors(conn, doc["id"], True)
            set_status(conn, doc["id"], "indexed", error=None)
            conn.commit()
            print(f"[{i}/{len(docs)}] vectors={n:5d}  {doc['rel_path']}")
        except Exception as exc:  # noqa: BLE001
            set_status(conn, doc["id"], "text_only", error=f"vectors: {exc}"[:500])
            conn.commit()
            print(f"[{i}/{len(docs)}] FAILED {doc['rel_path']}: {exc}")
            break
    print(json.dumps(stats(conn), indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aerovault-ingest")
    parser.add_argument("--root", default=settings.library_root)
    parser.add_argument("--db", default=str(Path(settings.data_dir) / "aerovault.db"))
    parser.add_argument("--lance", default=str(Path(settings.data_dir) / "lancedb"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan")
    p_scan.set_defaults(func=cmd_scan)

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--limit", type=int, default=0)
    p_ingest.add_argument("--collection", default=None)
    p_ingest.add_argument("--path-substring", default=None)
    p_ingest.add_argument("--ocr", action="store_true")
    p_ingest.add_argument("--no-vectors", action="store_true")
    p_ingest.add_argument("--force", action="store_true")
    p_ingest.set_defaults(func=cmd_ingest)

    p_ocr = sub.add_parser("ocr")
    p_ocr.add_argument("--limit", type=int, default=0)
    p_ocr.add_argument("--collection", default=None)
    p_ocr.add_argument("--path-substring", default=None)
    p_ocr.add_argument("--no-vectors", action="store_true")
    p_ocr.set_defaults(func=cmd_ocr)

    p_vec = sub.add_parser("vectors-only")
    p_vec.add_argument("--limit", type=int, default=0)
    p_vec.add_argument("--collection", default=None)
    p_vec.add_argument("--path-substring", default=None)
    p_vec.set_defaults(func=cmd_vectors_only)

    p_status = sub.add_parser("status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    conn = connect(Path(args.db))
    try:
        args.func(args, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
