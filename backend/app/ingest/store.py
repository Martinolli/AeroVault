"""SQLite storage: documents, page text, chunks and FTS5 full-text index."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rel_path TEXT UNIQUE NOT NULL,
    collection TEXT NOT NULL,
    title TEXT NOT NULL,
    size_mb REAL,
    sha256 TEXT,
    pages INTEGER,
    text_pages INTEGER,
    ocr_pages INTEGER,
    vectors INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no INTEGER NOT NULL,
    chars INTEGER NOT NULL,
    has_text INTEGER NOT NULL,
    ocr_used INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    PRIMARY KEY (document_id, page_no)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no INTEGER NOT NULL,
    chunk_no INTEGER NOT NULL,
    text TEXT NOT NULL,
    tokens_est INTEGER NOT NULL,
    UNIQUE (document_id, page_no, chunk_no)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compliance_runs (
    run_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    document_id INTEGER,
    mode TEXT NOT NULL DEFAULT 'gap',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    model TEXT NOT NULL,
    standards_json TEXT NOT NULL DEFAULT '[]',
    authorities_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'ready',
    progress INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT ''
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Streaming responses run in a worker thread; the connection may be closed
    # from a different thread than the one that opened it.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=8000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    # Migration for databases created before the vectors column existed.
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN vectors INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    return conn


def reset_document(conn: sqlite3.Connection, doc_id: int) -> None:
    conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
    conn.execute("DELETE FROM pages WHERE document_id = ?", (doc_id,))


def save_pages(conn: sqlite3.Connection, doc_id: int, pages) -> None:
    conn.executemany(
        "INSERT INTO pages (document_id, page_no, chars, has_text, ocr_used, text) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (doc_id, p.page_no, len(p.text), int(len(p.text.strip()) >= 50), int(p.ocr_used), p.text)
            for p in pages
        ],
    )


def save_chunks(conn: sqlite3.Connection, doc_id: int, chunks) -> None:
    conn.executemany(
        "INSERT INTO chunks (document_id, page_no, chunk_no, text, tokens_est) "
        "VALUES (?, ?, ?, ?, ?)",
        [(doc_id, page_no, chunk_no, text, tokens) for page_no, chunk_no, text, tokens in chunks],
    )


def set_status(
    conn: sqlite3.Connection,
    doc_id: int,
    status: str,
    pages: int | None = None,
    text_pages: int | None = None,
    ocr_pages: int | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "UPDATE documents SET status = ?, pages = COALESCE(?, pages), "
        "text_pages = COALESCE(?, text_pages), ocr_pages = COALESCE(?, ocr_pages), error = ? "
        "WHERE id = ?",
        (status, pages, text_pages, ocr_pages, error, doc_id),
    )


def set_vectors(conn: sqlite3.Connection, doc_id: int, ok: bool) -> None:
    conn.execute("UPDATE documents SET vectors = ? WHERE id = ?", (int(ok), doc_id))


def stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT collection, status, COUNT(*) AS n FROM documents GROUP BY collection, status"
    ).fetchall()
    out: dict = {"collections": {}, "documents": 0, "chunks": 0, "vectors_done": 0}
    for r in rows:
        out["collections"].setdefault(r["collection"], {})[r["status"]] = r["n"]
        out["documents"] += r["n"]
    out["chunks"] = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    out["vectors_done"] = conn.execute("SELECT COUNT(*) FROM documents WHERE vectors = 1").fetchone()[0]
    return out
