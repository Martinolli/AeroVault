"""Phase 3 API: authentication, library browsing and page access."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.auth import (
    COOKIE_NAME,
    authenticate,
    create_session,
    create_user,
    delete_session,
    require_user,
    session_user,
    users_exist,
)
from app.chat import (
    ALLOWED_MODELS,
    DEFAULT_MODEL,
    add_message,
    build_messages,
    chat_exists,
    create_chat,
    delete_chat,
    get_chat,
    get_history,
    list_chats,
    retrieve,
    stream_answer,
)
from app.config import settings
from app.ingest.store import connect

router = APIRouter(prefix="/api")


def get_conn():
    conn = connect(Path(settings.data_dir) / "aerovault.db")
    try:
        yield conn
    finally:
        conn.close()


def current_user(request: Request, conn=Depends(get_conn)) -> dict:
    return require_user(request, conn)


class PasswordBody(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class LoginBody(PasswordBody):
    remember: bool = False


class ChatBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    chat_id: int | None = None
    model: str | None = None


@router.get("/auth/status")
def auth_status(conn=Depends(get_conn)) -> dict:
    return {"configured": users_exist(conn)}


@router.post("/auth/setup")
def auth_setup(body: PasswordBody, response: Response, conn=Depends(get_conn)) -> dict:
    user_id = create_user(conn, body.password)
    token, max_age = create_session(conn, user_id)
    response.set_cookie(COOKIE_NAME, token, max_age=max_age, httponly=True, samesite="strict")
    return {"ok": True}


@router.post("/auth/login")
def auth_login(body: LoginBody, response: Response, conn=Depends(get_conn)) -> dict:
    user_id = authenticate(conn, body.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid password")
    token, max_age = create_session(conn, user_id, body.remember)
    response.set_cookie(COOKIE_NAME, token, max_age=max_age, httponly=True, samesite="strict")
    return {"ok": True}


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response, conn=Depends(get_conn)) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        delete_session(conn, token)
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/auth/me")
def auth_me(request: Request, conn=Depends(get_conn)) -> dict:
    user = session_user(conn, request.cookies.get(COOKIE_NAME))
    return {"authenticated": user is not None}


@router.get("/library")
def library(
    q: str = Query("", max_length=200),
    collection: str = Query("", max_length=100),
    limit: int = Query(100, ge=1, le=300),
    user=Depends(current_user),
    conn=Depends(get_conn),
) -> dict:
    where = ["status IN ('indexed', 'text_only', 'partial')"]
    params: list = []
    if q:
        where.append("(lower(title) LIKE ? OR lower(rel_path) LIKE ?)")
        params += [f"%{q.lower()}%", f"%{q.lower()}%"]
    if collection:
        where.append("collection = ?")
        params.append(collection)
    rows = conn.execute(
        "SELECT id, title, collection, pages, status, vectors FROM documents "
        f"WHERE {' AND '.join(where)} ORDER BY title LIMIT ?",
        [*params, limit],
    ).fetchall()
    return {"documents": [dict(r) for r in rows], "count": len(rows)}


def _document(conn, doc_id: int) -> dict:
    row = conn.execute(
        "SELECT id, rel_path, title, collection, pages, status, vectors FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(row)


@router.get("/documents/{doc_id}")
def document(doc_id: int, user=Depends(current_user), conn=Depends(get_conn)) -> dict:
    return _document(conn, doc_id)


@router.get("/documents/{doc_id}/pages/{page_no}")
def page_text(
    doc_id: int, page_no: int, user=Depends(current_user), conn=Depends(get_conn)
) -> dict:
    _document(conn, doc_id)
    row = conn.execute(
        "SELECT page_no, text, ocr_used FROM pages WHERE document_id = ? AND page_no = ?",
        (doc_id, page_no),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"document_id": doc_id, "page_no": row["page_no"], "text": row["text"], "ocr": bool(row["ocr_used"])}


@router.get("/documents/{doc_id}/file")
def document_file(doc_id: int, user=Depends(current_user), conn=Depends(get_conn)) -> FileResponse:
    doc = _document(conn, doc_id)
    root = Path(settings.library_root).resolve()
    path = (root / doc["rel_path"]).resolve()
    if not str(path).startswith(str(root)) or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), media_type="application/pdf", filename=path.name)


@router.post("/chat")
def chat(body: ChatBody, user=Depends(current_user), conn=Depends(get_conn)):
    model = body.model or DEFAULT_MODEL
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")
    question = body.question.strip()
    chat_id = body.chat_id
    if chat_id is not None and not chat_exists(conn, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    history = get_history(conn, chat_id) if chat_id is not None else []
    hits = retrieve(conn, question)
    if not hits:
        raise HTTPException(status_code=422, detail="No library sources matched this question")
    if chat_id is None:
        chat_id = create_chat(conn, question, model)
    add_message(conn, chat_id, "user", question)
    conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), chat_id))
    conn.commit()
    messages, sources = build_messages(question, hits, history)
    return StreamingResponse(
        stream_answer(Path(settings.data_dir) / "aerovault.db", chat_id, model, messages, sources),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chats")
def chats(
    q: str = Query("", max_length=200),
    limit: int = Query(100, ge=1, le=300),
    user=Depends(current_user),
    conn=Depends(get_conn),
) -> dict:
    rows = list_chats(conn, q, limit)
    return {"chats": rows, "count": len(rows)}


@router.get("/chats/{chat_id}")
def chat_detail(chat_id: int, user=Depends(current_user), conn=Depends(get_conn)) -> dict:
    chat = get_chat(conn, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/chats/{chat_id}")
def chat_delete(chat_id: int, user=Depends(current_user), conn=Depends(get_conn)) -> dict:
    if not delete_chat(conn, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"ok": True}
