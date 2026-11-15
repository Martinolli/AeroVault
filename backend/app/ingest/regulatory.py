"""Manifest-driven fetcher for official aviation regulatory sources.

This is deliberately a controlled downloader, not a web crawler. Each source
has an explicit URL, authority, document type, version/effective date and
checksum in a JSON manifest. The fetcher:

- accepts HTTPS URLs only;
- writes into ``data/regulatory_library/<authority>/``;
- refuses to overwrite a changed file unless ``--force`` is supplied;
- records SHA-256, bytes, content type, fetch time and HTTP status;
- keeps the original file (PDF/XML/HTML) and, for eCFR XML, a plain-text
  companion that the normal ingestion pipeline can index later.

Usage (from the project root, with the backend import path configured):

    py -3 -m app.ingest.regulatory --manifest data/regulatory_sources.json --dry-run
    py -3 -m app.ingest.regulatory --manifest data/regulatory_sources.json --only faa-14cfr-121
    py -3 -m app.ingest.regulatory --manifest data/regulatory_sources.json

The manifest is intentionally editable. Add only official sources and respect
each site's terms, robots policy and licensing. ICAO and EASA material may be
copyrighted; do not redistribute downloaded files.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "AeroVault/0.1 local research downloader (contact: library owner)"
MAX_BYTES = 150 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".xml", ".html", ".htm", ".txt", ".zip"}
ECFR_API = "https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title}.xml?part={part}"


@dataclass
class Source:
    id: str
    authority: str
    document_type: str
    title: str
    url: str
    version: str = ""
    effective_date: str = ""
    applicability: str = ""
    access_note: str = ""
    filename: str = ""
    local_path: str = ""
    sha256: str = ""
    bytes: int = 0
    content_type: str = ""
    fetched_at: str = ""
    status: str = "planned"
    error: str = ""
    tags: list[str] = field(default_factory=list)


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ValueError("Manifest must be a JSON object with a 'sources' array")
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_name(value: str, fallback: str = "source") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", value).strip(" .")
    return cleaned[:120] or fallback


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Only absolute HTTPS URLs are allowed")


def _xml_to_text(raw: bytes) -> str:
    """Convert eCFR-style XML/HTML into readable text without external tools."""
    try:
        root = ET.fromstring(raw)
        chunks = []
        for element in root.iter():
            tag = element.tag.lower().rsplit("}", 1)[-1]
            if tag in ("p", "head", "title", "div", "section", "article", "li", "tr"):
                text = " ".join("".join(element.itertext()).split())
                if text:
                    chunks.append(text)
        if chunks:
            return "\n\n".join(dict.fromkeys(chunks))
    except ET.ParseError:
        pass
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return "\n".join(line.strip() for line in html.unescape(text).splitlines() if line.strip())


def fetch(source: Source, root: Path, force: bool = False, timeout: int = 90) -> Source:
    _validate_url(source.url)
    suffix = Path(urllib.parse.urlparse(source.url).path).suffix.lower()
    filename = _safe_name(source.filename or f"{source.id}{suffix or '.bin'}")
    target_dir = root / _safe_name(source.authority.lower(), "other")
    target = target_dir / filename
    target_dir.mkdir(parents=True, exist_ok=True)

    if target.exists() and not force:
        source.local_path = str(target.relative_to(root.parent)) if root.parent in target.parents else str(target)
        source.sha256 = _sha256(target)
        source.bytes = target.stat().st_size
        source.status = "cached"
        source.fetched_at = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc).isoformat()
        return source

    request = urllib.request.Request(
        source.url,
        # eCFR returns 406 when the Accept list mixes PDF/XML/HTML. A wildcard
        # keeps both the eCFR XML API and ordinary PDF downloads working.
        headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "gzip"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            data = response.read(MAX_BYTES + 1)
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                data = gzip.decompress(data)
            if len(data) > MAX_BYTES:
                raise ValueError("Response exceeds the 150 MB limit")
            if not data:
                raise ValueError("Empty response")
            target.write_bytes(data)
            source.content_type = content_type
            source.bytes = len(data)
            source.sha256 = hashlib.sha256(data).hexdigest()
            source.local_path = str(target.relative_to(root.parent)) if root.parent in target.parents else str(target)
            source.fetched_at = datetime.now(timezone.utc).isoformat()
            source.status = "downloaded"
            source.error = ""
            if suffix == ".xml" or "xml" in content_type:
                text_target = target.with_suffix(".txt")
                text_target.write_text(_xml_to_text(data), encoding="utf-8")
                source.tags = sorted(set(source.tags + ["text_companion"]))
            return source
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as exc:
        source.status = "error"
        source.error = f"{type(exc).__name__}: {exc}"[:400]
        return source


def fetch_manifest(
    manifest_path: Path,
    root: Path,
    only: set[str] | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> list[Source]:
    data = load_manifest(manifest_path)
    results: list[Source] = []
    for raw in data["sources"]:
        if not isinstance(raw, dict):
            continue
        source = Source(**{k: v for k, v in raw.items() if k in Source.__dataclass_fields__})
        if only and source.id not in only:
            continue
        if dry_run:
            source.status = "planned"
            results.append(source)
            continue
        results.append(fetch(source, root, force=force))
    if not dry_run:
        by_id = {s.id: asdict(s) for s in results}
        for i, raw in enumerate(data["sources"]):
            if isinstance(raw, dict) and raw.get("id") in by_id:
                data["sources"][i] = by_id[raw["id"]]
        save_manifest(manifest_path, data)
    return results


def build_ecfr_entry(title: int, part: int, date: str = "current") -> dict[str, Any]:
    """Return a manifest entry for one eCFR part using the official API."""
    return {
        "id": f"faa-14cfr-{part}",
        "authority": "FAA",
        "document_type": "regulation",
        "title": f"14 CFR Part {part}",
        "url": ECFR_API.format(date=date, title=title, part=part),
        "version": "current" if date == "current" else date,
        "effective_date": "",
        "applicability": "US aviation operations and/or safety management, depending on part",
        "access_note": "Official eCFR API. Verify the current version before operational use.",
        "filename": f"14_CFR_Part_{part}.xml",
        "tags": ["ecfr", "primary", "us"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch official aviation regulatory sources from a manifest")
    parser.add_argument("--manifest", default="data/regulatory_sources.json")
    parser.add_argument("--root", default="data/regulatory_library")
    parser.add_argument("--only", action="append", default=[], help="Fetch only this source id (repeatable)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-download and overwrite existing files")
    args = parser.parse_args(argv)
    results = fetch_manifest(
        Path(args.manifest),
        Path(args.root),
        only=set(args.only) or None,
        dry_run=args.dry_run,
        force=args.force,
    )
    for source in results:
        print(f"{source.status:10} {source.id:24} {source.local_path or source.url} {source.error}")
    return 1 if any(s.status == "error" for s in results) else 0


if __name__ == "__main__":
    sys.exit(main())
