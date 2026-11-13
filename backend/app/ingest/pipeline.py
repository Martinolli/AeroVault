"""Ingestion CLI.

Usage (inside the backend container):
    python -m app.ingest.pipeline scan  [--root /library]
    python -m app.ingest.pipeline ingest [--limit N] [--collection NAME] [--ocr] [--no-vectors]
    python -m app.ingest.pipeline status
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
from .store import connect, reset_document, save_chunks, save_pages, set_status, stats


def _lance_upsert(lance_dir: Path, doc_id: int, records: list[dict]) -> None:
    import lancedb

    db = lancedb.connect(str(lance_dir))
    if "chunks" in db.table_names():
        table = db.open_table("chunks")
        table.delete(f"document_id = {doc_id}")
        if records:
            table.add(records)
    elif records:
        db.create_table("chunks", data=records)


def cmd_scan(args: argparse.Namespace, conn) -> None:
    root = Path(args.root)
    if not root.exists():
        sys.exit(f"Library root not found: {root}")
    t0 = time.time()
    counts = scan(root, conn)
    print(json.dumps({"root": str(root), "seconds": round(time.time() - t0, 1), **counts}))


def cmd_status(args: argparse.Namespace, conn) -> None:
    print(json.dumps(stats(conn), indent=2))


def cmd_ingest(args: argparse.Namespace, conn) -> None:
    root = Path(args.root)
    lance_dir = Path(args.lance)
    sql = "SELECT * FROM documents WHERE status IN ('pending', 'partial')"
    params: list = []
    if args.collection:
        sql += " AND collection = ?"
        params.append(args.collection)
    if args.force:
        sql = "SELECT * FROM documents WHERE 1 = 1"
        params = []
        if args.collection:
            sql += " AND collection = ?"
            params.append(args.collection)
    sql += " ORDER BY size_mb ASC"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    docs = conn.execute(sql, params).fetchall()
    if not docs:
        print("Nothing to ingest.")
        return

    api_key = settings.openai_api_key
    use_vectors = not args.no_vectors and bool(api_key)
    if not use_vectors:
        print("Vectors disabled (no API key or --no-vectors); text index only.")

    done = 0
    for doc in docs:
        path = root / doc["rel_path"]
        t0 = time.time()
        try:
            pages, engine = extract_pages(path, ocr=args.ocr)
        except Exception as exc:  # noqa: BLE001
            set_status(conn, doc["id"], "error", error=f"{type(exc).__name__}: {exc}"[:500])
            conn.commit()
            print(f"ERROR  {doc['rel_path']}: {exc}")
            continue

        text_pages = sum(1 for p in pages if len(p.text.strip()) >= 50)
        ocr_pages = sum(1 for p in pages if p.ocr_used)
        status = "indexed" if text_pages >= 0.9 * max(len(pages), 1) else "partial"

        reset_document(conn, doc["id"])
        save_pages(conn, doc["id"], pages)
        chunk_rows: list[tuple] = []
        chunk_texts: list[str] = []
        for p in pages:
            for i, text in enumerate(chunk_page(p.text)):
                chunk_rows.append((p.page_no, i, text, estimate_tokens(text)))
                chunk_texts.append(text)
        save_chunks(conn, doc["id"], chunk_rows)
        set_status(conn, doc["id"], status, len(pages), text_pages, ocr_pages, None)
        conn.commit()

        if use_vectors and chunk_texts:
            vectors = embed_texts(chunk_texts, settings.embedding_model, api_key)
            ids = [r[0] for r in conn.execute(
                "SELECT id FROM chunks WHERE document_id = ? ORDER BY id", (doc["id"],)
            ).fetchall()]
            records = [
                {
                    "vector": vec,
                    "document_id": doc["id"],
                    "page_no": chunk_rows[i][0],
                    "chunk_id": ids[i],
                }
                for i, vec in enumerate(vectors)
            ]
            _lance_upsert(lance_dir, doc["id"], records)

        done += 1
        print(
            f"[{done}/{len(docs)}] {status:8s} {len(pages):5d} pp  "
            f"{len(chunk_texts):5d} ch  {engine:7s} {time.time() - t0:5.1f}s  {doc['rel_path']}"
        )

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
    p_ingest.add_argument("--ocr", action="store_true")
    p_ingest.add_argument("--no-vectors", action="store_true")
    p_ingest.add_argument("--force", action="store_true")
    p_ingest.set_defaults(func=cmd_ingest)

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
