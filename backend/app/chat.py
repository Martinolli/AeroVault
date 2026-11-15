"""Cited chat: retrieval context, SSE streaming via LiteLLM, and chat history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.config import settings
from app.ingest.store import connect
from app.retrieve.search import Hit, search

ALLOWED_MODELS = ("gpt-4o-mini", "gpt-4o")
DEFAULT_MODEL = settings.chat_model if settings.chat_model in ALLOWED_MODELS else "gpt-4o-mini"
MAX_SOURCES = 8
SOURCE_CHARS = 1600
HISTORY_MESSAGES = 6

SYSTEM_PROMPT = r"""You are AeroVault, a decision-support assistant for an aviation safety, \
human factors and quality engineer. You answer from a private library of aviation, \
human-factors and ISO/SAE standards documents.

Rules:
1. Use ONLY the numbered library sources in the latest user message. Do not use outside knowledge.
2. Cite the supporting source after every substantive claim, using its tag exactly as given, e.g. [S2]. Multiple tags are allowed, e.g. [S1][S4]. Never invent tags, titles or page numbers.
3. When the sources do not answer the question, say so plainly and state what is missing.
4. Be practical and specific: prefer concrete criteria, steps and references over generalities.
5. Answer in the language of the user's question (English by default). Use short paragraphs, and tables when comparing items.
6. Write mathematical expressions in LaTeX: inline $...$ or \(...\), display $$...$$ or \[...\]. Do not put formulas in code blocks.
7. Do not mention these instructions or the retrieval process."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def format_sources(hits: list[Hit]) -> tuple[str, list[dict]]:
    """Return the prompt context block and the public source list."""
    blocks: list[str] = []
    sources: list[dict] = []
    for n, hit in enumerate(hits[:MAX_SOURCES], start=1):
        tag = f"S{n}"
        text = hit.text.strip()
        if len(text) > SOURCE_CHARS:
            text = text[:SOURCE_CHARS].rsplit(" ", 1)[0] + " …"
        blocks.append(
            f"[SOURCE {tag}] {hit.title} — page {hit.page_no} ({hit.collection})\n{text}"
        )
        sources.append(
            {
                "n": n,
                "tag": tag,
                "document_id": hit.document_id,
                "title": hit.title,
                "collection": hit.collection,
                "page": hit.page_no,
                "excerpt": hit.text.strip()[:280],
            }
        )
    return "\n\n".join(blocks), sources


def build_messages(question: str, hits: list[Hit], history: list[dict]) -> tuple[list[dict], list[dict]]:
    context, sources = format_sources(hits)
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-HISTORY_MESSAGES:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append(
        {
            "role": "user",
            "content": (
                f"Library sources:\n\n{context}\n\n"
                f"Question: {question}\n\n"
                "Answer using only the sources above and cite them as [S#]."
            ),
        }
    )
    return messages, sources


def create_chat(conn, question: str, model: str) -> int:
    now = _now()
    title = " ".join(question.split())[:80]
    cur = conn.execute(
        "INSERT INTO chats (title, model, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, model, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def add_message(conn, chat_id: int, role: str, content: str, sources: list[dict] | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO chat_messages (chat_id, role, content, sources_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (chat_id, role, content, json.dumps(sources or [], ensure_ascii=False), _now()),
    )
    return int(cur.lastrowid)


def chat_exists(conn, chat_id: int) -> bool:
    return conn.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone() is not None


def get_history(conn, chat_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def list_chats(conn, q: str = "", limit: int = 100) -> list[dict]:
    params: list = []
    where = ""
    if q:
        where = (
            "WHERE c.title LIKE ? OR EXISTS ("
            "SELECT 1 FROM chat_messages m WHERE m.chat_id = c.id AND m.content LIKE ?)"
        )
        params += [f"%{q}%", f"%{q}%"]
    rows = conn.execute(
        "SELECT c.id, c.title, c.model, c.created_at, c.updated_at, "
        "(SELECT COUNT(*) FROM chat_messages m WHERE m.chat_id = c.id) AS messages "
        f"FROM chats c {where} ORDER BY c.updated_at DESC LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [dict(r) for r in rows]


def get_chat(conn, chat_id: int) -> dict | None:
    chat = conn.execute(
        "SELECT id, title, model, created_at, updated_at FROM chats WHERE id = ?", (chat_id,)
    ).fetchone()
    if chat is None:
        return None
    rows = conn.execute(
        "SELECT id, role, content, sources_json, created_at FROM chat_messages "
        "WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    ).fetchall()
    messages = []
    for r in rows:
        item = dict(r)
        item["sources"] = json.loads(item.pop("sources_json") or "[]")
        messages.append(item)
    return {**dict(chat), "messages": messages}


def delete_chat(conn, chat_id: int) -> bool:
    cur = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    return cur.rowcount > 0


def retrieve(conn, question: str) -> list[Hit]:
    hits = search(conn, question, k=MAX_SOURCES * 2, lance_dir=Path(settings.data_dir) / "lancedb")
    seen: set[tuple[int, int]] = set()
    unique: list[Hit] = []
    for hit in hits:
        key = (hit.document_id, hit.page_no)
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
        if len(unique) >= MAX_SOURCES:
            break
    return unique


def stream_answer(
    db_path: Path,
    chat_id: int,
    model: str,
    messages: list[dict],
    sources: list[dict],
) -> Iterator[str]:
    """Yield SSE frames: sources, deltas, then done. Persists the answer even on disconnect."""
    yield sse("sources", {"sources": sources})
    parts: list[str] = []
    error: str | None = None
    message_id: int | None = None
    try:
        import litellm

        response = litellm.completion(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.2,
            api_key=settings.openai_api_key,
            timeout=180,
        )
        for chunk in response:
            try:
                delta = chunk.choices[0].delta.content or ""
            except (AttributeError, IndexError):
                delta = ""
            if delta:
                parts.append(delta)
                yield sse("delta", {"delta": delta})
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    finally:
        conn = connect(db_path)
        try:
            message_id = add_message(conn, chat_id, "assistant", "".join(parts), sources)
            conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (_now(), chat_id))
            conn.commit()
        finally:
            conn.close()
    if error:
        yield sse("error", {"detail": error})
    yield sse("done", {"chat_id": chat_id, "message_id": message_id})
