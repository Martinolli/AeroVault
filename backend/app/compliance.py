"""Compliance workspace (W3): clause-level comparison of an uploaded procedure
against selected indexed standards.

Uploads are transient: the file is extracted to memory, deleted immediately and
never written to SQLite/FTS/LanceDB. Runs live in memory and expire after 2 h.
"""

from __future__ import annotations

import io
import json
import re
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import require_user
from app.config import settings
from app.ingest.embed import embed_texts
from app.ingest.extract import extract_pages
from app.ingest.store import connect
from app.retrieve.search import Hit, fts_search, _enrich, rrf_merge

router = APIRouter(prefix="/api/compliance")

MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 200
MAX_CLAUSES = 60
MAX_STANDARDS = 5
MAX_EXTRA_COLUMNS = 3
RUN_TTL_SECONDS = 2 * 60 * 60
ALLOWED_MODELS = ("gpt-4o-mini", "gpt-4o")
DEFAULT_MODEL = "gpt-4o-mini"

STATUSES = ("Compliant", "Partial", "Gap", "Not applicable", "Unclear")
HEADING_RE = re.compile(r"^(?:(?:Section|Clause|Article)\s+)?(\d+(?:\.\d+){0,3}|[A-Z]\.\d+(?:\.\d+)*)\s+(.{3,120})$")


@dataclass
class Run:
    id: str
    filename: str
    created: float
    clauses: list[dict]
    standards: list[dict]
    model: str
    extra_columns: list[str]
    instructions: str
    ocr: bool
    mode: str = "gap"
    problem_brief: str = ""
    authorities: list[str] = field(default_factory=list)
    document_id: int | None = None
    source_pages: list[dict] = field(default_factory=list)
    narrative: dict = field(default_factory=dict)
    status: str = "ready"
    progress: int = 0
    results: list[dict] = field(default_factory=list)
    error: str = ""
    cancel: threading.Event = field(default_factory=threading.Event)


_RUNS: dict[str, Run] = {}
_LOCK = threading.Lock()


def _get_conn():
    conn = connect(Path(settings.data_dir) / "aerovault.db")
    try:
        yield conn
    finally:
        conn.close()


def _user(request: Request, conn=Depends(_get_conn)) -> dict:
    return require_user(request, conn)


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _cleanup() -> None:
    cutoff = _now() - RUN_TTL_SECONDS
    with _LOCK:
        for rid in [k for k, v in _RUNS.items() if v.created < cutoff]:
            _RUNS.pop(rid, None)
    try:
        conn = connect(Path(settings.data_dir) / "aerovault.db")
        try:
            conn.execute("DELETE FROM compliance_runs WHERE expires_at < ?", (datetime.now(timezone.utc).isoformat(),))
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass


def _save_meta(run: Run) -> None:
    """Persist metadata only: never procedure text, briefs, clauses or answers."""
    created = datetime.fromtimestamp(run.created, tz=timezone.utc)
    expires = created + timedelta(seconds=RUN_TTL_SECONDS)
    try:
        conn = connect(Path(settings.data_dir) / "aerovault.db")
        try:
            conn.execute(
                "INSERT INTO compliance_runs "
                "(run_id, filename, document_id, mode, created_at, expires_at, model, "
                "standards_json, authorities_json, status, progress, total, error) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET model=excluded.model, "
                "standards_json=excluded.standards_json, authorities_json=excluded.authorities_json, "
                "status=excluded.status, progress=excluded.progress, total=excluded.total, error=excluded.error",
                (
                    run.id,
                    run.filename[:240],
                    run.document_id,
                    run.mode,
                    created.isoformat(),
                    expires.isoformat(),
                    run.model,
                    json.dumps([{"id": s.get("id"), "title": s.get("title", ""), "collection": s.get("collection", "")} for s in run.standards])[:4000],
                    json.dumps(run.authorities)[:1000],
                    run.status,
                    run.progress,
                    len(run.clauses),
                    run.error[:400],
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass


def _meta_row(row) -> dict:
    item = dict(row)
    try:
        item["standards"] = json.loads(item.pop("standards_json") or "[]")
    except (TypeError, ValueError):
        item["standards"] = []
    try:
        item["authorities"] = json.loads(item.pop("authorities_json") or "[]")
    except (TypeError, ValueError):
        item["authorities"] = []
    return item


def _run_or_404(run_id: str) -> Run:
    with _LOCK:
        run = _RUNS.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Compliance run not found or expired")
    return run


def _public(run: Run) -> dict:
    return {
        "run_id": run.id,
        "filename": run.filename,
        "document_id": run.document_id,
        "mode": run.mode,
        "problem_brief": run.problem_brief,
        "authorities": run.authorities,
        "status": run.status,
        "progress": run.progress,
        "total": len(run.clauses),
        "model": run.model,
        "standards": run.standards,
        "extra_columns": run.extra_columns,
        "instructions": run.instructions,
        "clauses": run.clauses,
        "results": run.results,
        "narrative": run.narrative,
        "error": run.error,
    }


def _docx_parts(path: Path) -> list[tuple[str, str]]:
    from docx import Document

    doc = Document(str(path))
    parts: list[tuple[str, str]] = []
    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if text:
            style = para.style.name if para.style is not None else ""
            parts.append((style or "", text))
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(("", " | ".join(cells)))
    return parts


def _pdf_parts(path: Path, ocr: bool) -> tuple[list[tuple[str, str]], int, list[str]]:
    pages, _engine = extract_pages(path, ocr=ocr)
    if len(pages) > MAX_PAGES:
        raise HTTPException(status_code=400, detail=f"Procedure has {len(pages)} pages; the limit is {MAX_PAGES}")
    parts: list[tuple[str, str]] = []
    warnings: list[str] = []
    ocr_pages = 0
    for page in pages:
        for line in (page.text or "").splitlines():
            line = line.strip()
            if line:
                parts.append(("", line))
        if page.ocr_used:
            ocr_pages += 1
    empty = sum(1 for p in pages if len((p.text or "").strip()) < 20)
    if empty:
        warnings.append(f"{empty} page(s) had little or no text; enable OCR if this is a scanned procedure.")
    return parts, ocr_pages, warnings


def _is_heading(text: str, style: str) -> bool:
    if style.lower().startswith("heading") and len(text) <= 140:
        return True
    if len(text) > 140 or text.endswith("."):
        return False
    m = HEADING_RE.match(text)
    return bool(m)


def _segment(parts: list[tuple[str, str]]) -> list[dict]:
    clauses: list[dict] = []
    current: dict | None = None

    def push() -> None:
        nonlocal current
        if current and (current["heading"] or current["text"].strip()):
            current["text"] = current["text"].strip()[:6000]
            clauses.append(current)
        current = None

    for style, text in parts:
        if current is None and not clauses and style.lower() in ("title", "subtitle"):
            continue
        if _is_heading(text, style):
            push()
            current = {"id": str(len(clauses) + 1), "heading": text[:200], "text": ""}
        else:
            if current is None:
                current = {"id": str(len(clauses) + 1), "heading": "", "text": ""}
            current["text"] += text + "\n"
    push()

    if not clauses:
        # No headings at all: group paragraphs into readable blocks.
        block, size = [], 0
        for _style, text in parts:
            block.append(text)
            size += len(text)
            if size >= 1200:
                clauses.append({"id": str(len(clauses) + 1), "heading": f"Block {len(clauses) + 1}", "text": "\n".join(block)[:6000]})
                block, size = [], 0
        if block:
            clauses.append({"id": str(len(clauses) + 1), "heading": f"Block {len(clauses) + 1}", "text": "\n".join(block)[:6000]})

    # Re-id after any merge and enforce the cap.
    clauses = clauses[:MAX_CLAUSES]
    for i, clause in enumerate(clauses, start=1):
        clause["id"] = str(i)
    return clauses


def _extract_upload(path: Path, suffix: str, ocr: bool) -> tuple[list[dict], int, list[str]]:
    if suffix == ".docx":
        parts = _docx_parts(path)
        return _segment(parts), 0, []
    parts, ocr_pages, warnings = _pdf_parts(path, ocr)
    return _segment(parts), ocr_pages, warnings


class ClauseBody(BaseModel):
    id: str = Field(max_length=20)
    heading: str = Field(default="", max_length=200)
    text: str = Field(default="", max_length=8000)


class RunBody(BaseModel):
    standard_ids: list[int] = Field(default_factory=list, max_length=MAX_STANDARDS)
    model: str | None = None
    clauses: list[ClauseBody] = Field(default_factory=list, max_length=MAX_CLAUSES)
    extra_columns: list[str] = Field(default_factory=list, max_length=MAX_EXTRA_COLUMNS)
    instructions: str = Field(default="", max_length=1000)
    mode: str = Field(default="gap", max_length=20)
    problem_brief: str = Field(default="", max_length=6000)
    authorities: list[str] = Field(default_factory=list, max_length=10)


@router.post("/upload")
async def upload(file: UploadFile = File(...), ocr: bool = Form(False), _user=Depends(_user)) -> dict:
    _cleanup()
    filename = file.filename or "procedure"
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX procedures are supported")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is larger than 25 MB")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = Path(tmp.name)
    try:
        tmp.write(data)
        tmp.close()
        clauses, ocr_pages, warnings = _extract_upload(tmp_path, suffix, ocr)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read the procedure: {exc}") from exc
    finally:
        try:
            tmp.close()
        except Exception:  # noqa: BLE001
            pass
        tmp_path.unlink(missing_ok=True)

    if not clauses:
        raise HTTPException(status_code=400, detail="No readable text found in the procedure")
    run = Run(
        id=uuid.uuid4().hex[:16],
        filename=filename,
        created=_now(),
        clauses=clauses,
        standards=[],
        model=DEFAULT_MODEL,
        extra_columns=[],
        instructions="",
        ocr=ocr,
    )
    with _LOCK:
        _RUNS[run.id] = run
    _save_meta(run)
    if ocr_pages:
        warnings.append(f"OCR was used on {ocr_pages} page(s).")
    return {"run_id": run.id, "filename": filename, "clauses": clauses, "warnings": warnings}


@router.post("/library/{doc_id}")
def library_run(doc_id: int, conn=Depends(_get_conn), _user=Depends(_user)) -> dict:
    """Use an indexed library document as the procedure/evidence source.

    The library text is already local; this endpoint only copies the needed
    pages into the transient in-memory run. It does not create a new index or
    upload a duplicate file.
    """
    _cleanup()
    doc = conn.execute(
        "SELECT id, title, collection, pages, status FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    if doc is None:
        raise HTTPException(status_code=404, detail="Library document not found")
    rows = conn.execute(
        "SELECT page_no, text, ocr_used FROM pages WHERE document_id = ? ORDER BY page_no",
        (doc_id,),
    ).fetchall()
    if not rows:
        raise HTTPException(status_code=400, detail="This library document has no extracted text")
    if len(rows) > MAX_PAGES:
        raise HTTPException(status_code=400, detail=f"Document has {len(rows)} pages; the limit is {MAX_PAGES}")
    parts: list[tuple[str, str]] = []
    source_pages: list[dict] = []
    ocr_pages = 0
    for row in rows:
        text = (row["text"] or "").strip()
        if not text:
            continue
        source_pages.append({"page": row["page_no"], "text": text[:12000], "ocr": bool(row["ocr_used"])})
        for line in text.splitlines():
            if line.strip():
                parts.append(("", line.strip()))
        if row["ocr_used"]:
            ocr_pages += 1
    clauses = _segment(parts)
    if not clauses:
        raise HTTPException(status_code=400, detail="No readable text found in the library document")
    run = Run(
        id=uuid.uuid4().hex[:16],
        filename=doc["title"],
        created=_now(),
        clauses=clauses,
        standards=[],
        model=DEFAULT_MODEL,
        extra_columns=[],
        instructions="",
        ocr=bool(ocr_pages),
        mode="problem",
        document_id=doc_id,
        source_pages=source_pages,
    )
    with _LOCK:
        _RUNS[run.id] = run
    _save_meta(run)
    warnings = []
    if ocr_pages:
        warnings.append(f"OCR text was used on {ocr_pages} page(s).")
    return {
        "run_id": run.id,
        "filename": doc["title"],
        "document_id": doc_id,
        "collection": doc["collection"],
        "clauses": clauses,
        "warnings": warnings,
    }


@router.get("/standards")
def standards(q: str = "", limit: int = 30, conn=Depends(_get_conn), _user=Depends(_user)) -> dict:
    limit = max(1, min(limit, 100))
    if q.strip():
        rows = conn.execute(
            "SELECT id, title, collection, pages, status FROM documents WHERE lower(title) LIKE ? "
            "ORDER BY CASE status WHEN 'indexed' THEN 0 ELSE 1 END, title LIMIT ?",
            (f"%{q.strip().lower()}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, collection, pages, status FROM documents "
            "ORDER BY CASE status WHEN 'indexed' THEN 0 ELSE 1 END, title LIMIT ?",
            (limit,),
        ).fetchall()
    return {"standards": [dict(r) for r in rows]}


def _standards(conn, ids: list[int]) -> list[dict]:
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT id, title, collection, pages, status FROM documents WHERE id IN ({marks})", ids
    ).fetchall()
    if len(rows) != len(set(ids)):
        raise HTTPException(status_code=400, detail="One or more selected standards were not found")
    return [dict(r) for r in rows]


def _retrieve(
    conn,
    query: str,
    doc_ids: list[int] | None,
    lance_dir: Path,
    k: int = 3,
    authorities: list[str] | None = None,
    exclude_doc_id: int | None = None,
) -> list[Hit]:
    """Retrieve standards/procedure passages.

    ``doc_ids`` empty/None means search the whole indexed library. Authorities
    are collection labels (FAA, EASA, BOOKS, ...), not file extensions.
    """
    allowed = {a.strip().lower() for a in (authorities or []) if a.strip()}
    fts = fts_search(conn, query, 40)
    if doc_ids:
        fts = [h for h in fts if h.document_id in doc_ids]
    if allowed:
        fts = [h for h in fts if h.collection.strip().lower() in allowed]
    if exclude_doc_id:
        fts = [h for h in fts if h.document_id != exclude_doc_id]
    try:
        import lancedb

        qvec = embed_texts([query], settings.embedding_model, settings.openai_api_key)[0]
        table = lancedb.connect(str(lance_dir)).open_table("chunks")
        search = table.search(qvec)
        if doc_ids:
            where = "document_id IN (" + ",".join(str(int(x)) for x in doc_ids) + ")"
            search = search.where(where)
        raw = search.limit(40).to_list()
        by_id = _enrich(conn, [r["chunk_id"] for r in raw])
        vec = []
        for r in raw:
            hit = by_id.get(r["chunk_id"])
            if (
                hit is not None
                and (not allowed or hit.collection.strip().lower() in allowed)
                and (not exclude_doc_id or hit.document_id != exclude_doc_id)
            ):
                hit.score = 1.0 / (1.0 + float(r.get("_distance", 0.0)))
                vec.append(hit)
    except Exception:  # noqa: BLE001
        vec = []
    return rrf_merge([fts, vec])[:k]


SYSTEM_PROMPT = """You are AeroVault's compliance analyst. Compare one procedure clause with the supplied \
standard passages. Use ONLY the passages. Never invent clause numbers, pages or requirements.

Return JSON only with this shape:
{"status": "Compliant|Partial|Gap|Not applicable|Unclear",
 "requirement": "short paraphrase of the applicable requirement",
 "standard_clause": "clause number if visible, else empty",
 "evidence": "short quote from the passage, max 40 words",
 "page": 12,
 "rationale": "why the procedure does or does not satisfy it",
 "action": "specific recommended action, or empty",
 "confidence": "High|Medium|Low",
 "extras": {"Column name": "value"}}

Rules:
- Compliant: the procedure clearly meets the requirement.
- Partial: partly meets it or lacks evidence.
- Gap: the procedure conflicts with it or omits it.
- Not applicable: the requirement does not apply to this procedure.
- Unclear: the passages or procedure do not provide enough evidence.
- page must be one of the supplied passage pages.
- Fill requested extra columns only when the answer is supported; otherwise use an empty string.
- Keep the rationale practical and specific."""


def _compare(run: Run, clause: dict, hits: list[Hit]) -> dict:
    base = {
        "clause_id": clause["id"],
        "clause_heading": clause.get("heading", ""),
        "clause_excerpt": (clause.get("text") or "")[:400],
        "status": "Unclear",
        "requirement": "",
        "standard": "",
        "standard_clause": "",
        "page": 0,
        "document_id": 0,
        "evidence": "",
        "rationale": "",
        "action": "",
        "confidence": "Low",
        "extras": {},
    }
    if not hits:
        base["rationale"] = "No relevant passage was found in the selected standards."
        base["action"] = "Review the clause manually or select a different standard."
        return base

    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[S{i}] {hit.title} — page {hit.page_no} ({hit.collection})\n{hit.text.strip()[:1800]}"
        )
    extras = run.extra_columns
    user = (
        f"Procedure: {run.filename}\n"
        f"Clause {clause['id']}: {clause.get('heading', '')}\n"
        f"{clause.get('text', '')[:4000]}\n\n"
        + (f"Owner instructions: {run.instructions}\n\n" if run.instructions else "")
        + ("Requested extra columns: " + ", ".join(extras) + "\n\n" if extras else "")
        + "Standard passages:\n\n"
        + "\n\n".join(blocks)
    )
    try:
        import litellm

        response = litellm.completion(
            model=run.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=700,
            response_format={"type": "json_object"},
            api_key=settings.openai_api_key,
            timeout=90,
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:  # noqa: BLE001
        base["rationale"] = f"Comparison failed: {type(exc).__name__}: {str(exc)[:200]}"
        base["action"] = "Retry this clause."
        return base

    status = data.get("status") if data.get("status") in STATUSES else "Unclear"
    pages = {h.page_no for h in hits}
    try:
        page = int(data.get("page") or 0)
    except (TypeError, ValueError):
        page = 0
    if page not in pages:
        page = hits[0].page_no
    hit = next((h for h in hits if h.page_no == page), hits[0])
    extras_out = data.get("extras") if isinstance(data.get("extras"), dict) else {}
    base.update(
        {
            "status": status,
            "requirement": str(data.get("requirement") or "")[:600],
            "standard": hit.title,
            "standard_clause": str(data.get("standard_clause") or "")[:60],
            "page": page,
            "document_id": hit.document_id,
            "evidence": str(data.get("evidence") or "")[:400],
            "rationale": str(data.get("rationale") or "")[:800],
            "action": str(data.get("action") or "")[:600],
            "confidence": data.get("confidence") if data.get("confidence") in ("High", "Medium", "Low") else "Low",
            "extras": {k: str(v)[:200] for k, v in extras_out.items() if k in extras},
        }
    )
    return base


PROBLEM_PROMPT = """You are AeroVault's aviation safety and compliance analyst. \
Help the owner understand a real operational or quality problem using ONLY the supplied \
procedure text and library passages. Never invent requirements, clause numbers, pages, \
organisations, or facts. Distinguish clearly between what the evidence says and what you infer.

Return JSON only with this shape:
{
 "problem_understanding": "concise restatement of the problem and the decision needed",
 "applicable_requirements": [
   {"requirement": "short paraphrase", "authority": "FAA/EASA/ICAO/company/unknown",
    "document": "source title", "clause": "visible clause or empty", "page": 12,
    "evidence": "short quote, max 40 words", "relevance": "why it applies"}
 ],
 "procedure_evidence": [
   {"finding": "what the procedure says or omits", "document": "procedure/document",
    "clause": "section or empty", "page": 0, "evidence": "short quote"}
 ],
 "gaps_or_conflicts": [
   {"issue": "specific gap, conflict or ambiguity", "why_it_matters": "operational consequence",
    "severity": "High|Medium|Low", "evidence": "supporting quote or reference"}
 ],
 "contributing_factors": [
   {"factor": "likely contributing factor", "explanation": "evidence-based explanation",
    "confidence": "High|Medium|Low"}
 ],
 "risk_assessment": {"likelihood": "High|Medium|Low|Unclear", "severity": "High|Medium|Low|Unclear",
   "risk_level": "High|Medium|Low|Unclear", "rationale": "why"},
 "corrective_actions": [
   {"action": "specific action", "owner": "suggested function", "priority": "High|Medium|Low",
    "verification": "how to verify effectiveness"}
 ],
 "verification": "how to confirm the fix works",
 "limitations": "what the available evidence cannot establish"
}

Rules:
- Use the supplied passages; do not rely on general aviation knowledge for a requirement.
- Page numbers must be visible in the supplied passage labels. If unknown, use 0.
- If evidence is insufficient, say so in limitations rather than filling gaps.
- Make the analysis useful for a manager: practical, specific and proportionate to the risk.
- Do not produce a compliance matrix unless the user explicitly asks for one."""


def _problem_source_excerpt(run: Run) -> str:
    if run.source_pages:
        blocks = []
        used = 0
        for page in run.source_pages:
            text = (page.get("text") or "").strip()
            if not text:
                continue
            block = f"[Document page {page.get('page')}] {text}"
            if used + len(block) > 12000:
                break
            blocks.append(block)
            used += len(block)
        return "\n\n".join(blocks)
    blocks = []
    used = 0
    for clause in run.clauses:
        block = f"[{clause.get('heading') or 'Section ' + str(clause.get('id'))}] {clause.get('text', '')}"
        if used + len(block) > 12000:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


_WORD_RE = re.compile(r"[a-z0-9]+")


def _norm_words(value: str) -> list[str]:
    return _WORD_RE.findall((value or "").lower())


def _evidence_score(evidence: str, text: str) -> float:
    """Return a conservative 0–1 score for a quote against a page/chunk.

    The model sometimes attaches the right quote to the wrong page. Exact
    normalised containment is preferred; a long prefix/suffix and token
    coverage are fallbacks for PDF extraction differences.
    """
    quote = _norm_words(evidence)
    haystack = _norm_words(text)
    if not quote or not haystack:
        return 0.0
    qtext = " ".join(quote)
    htext = " ".join(haystack)
    if qtext in htext:
        return 1.0
    for size in (12, 8, 6):
        if len(quote) >= size:
            if " ".join(quote[:size]) in htext or " ".join(quote[-size:]) in htext:
                return 0.88
    qset = {word for word in quote if len(word) > 2}
    if not qset:
        return 0.0
    return len(qset & set(haystack)) / len(qset)


def _verify_problem_citations(conn, narrative: dict, hits: list[Hit], run: Run) -> None:
    """Correct or reject page numbers that are not supported by the quote."""
    cache: dict[int, list[tuple[int, str]]] = {}

    def pages_for(document_id: int) -> list[tuple[int, str]]:
        if document_id not in cache:
            rows = conn.execute(
                "SELECT page_no, text FROM pages WHERE document_id = ? ORDER BY page_no",
                (document_id,),
            ).fetchall()
            cache[document_id] = [(int(row["page_no"]), row["text"] or "") for row in rows]
        return cache[document_id]

    def best_page(document_id: int, evidence: str) -> tuple[int, float]:
        scored = [(_evidence_score(evidence, text), page) for page, text in pages_for(document_id)]
        if not scored:
            return 0, 0.0
        score, page = max(scored)
        return (page, score) if score >= 0.72 else (0, score)

    def resolve_document(item: dict) -> int | None:
        raw = (item.get("document") or "").strip().lower()
        if not raw:
            return None
        match = next((hit for hit in hits if hit.title.lower() == raw), None)
        if match is None:
            match = next((hit for hit in hits if raw in hit.title.lower()), None)
        if match is None:
            return None
        item["document"] = match.title
        item["document_id"] = match.document_id
        return match.document_id

    unverified = 0
    for item in narrative.get("applicable_requirements", []):
        document_id = resolve_document(item)
        if document_id is None:
            item["page"] = 0
            item["citation_verified"] = False
            unverified += 1
            continue
        page, score = best_page(document_id, item.get("evidence", ""))
        item["page"] = page
        item["citation_verified"] = bool(page and score >= 0.72)
        if not item["citation_verified"]:
            unverified += 1

    # Procedure findings are often inferences, not literal quotes. Verify the
    # page only when the source text actually supports the stated evidence.
    source_pages = [(int(page.get("page") or 0), page.get("text") or "") for page in run.source_pages]
    for item in narrative.get("procedure_evidence", []):
        evidence = item.get("evidence", "")
        if not source_pages or not evidence:
            item["page"] = 0
            item["citation_verified"] = False
            continue
        scored = [(_evidence_score(evidence, text), page) for page, text in source_pages]
        score, page = max(scored)
        item["page"] = page if score >= 0.72 else 0
        item["citation_verified"] = bool(item["page"])

    if unverified:
        note = (
            f"{unverified} requirement citation(s) could not be matched to the supplied text; "
            "their page is shown as 0 rather than guessing."
        )
        narrative["limitations"] = (narrative.get("limitations", "") + " " + note).strip()


def _analyse_problem(run: Run, hits: list[Hit], conn=None) -> dict:
    base: dict[str, Any] = {
        "problem_understanding": run.problem_brief,
        "applicable_requirements": [],
        "procedure_evidence": [],
        "gaps_or_conflicts": [],
        "contributing_factors": [],
        "risk_assessment": {
            "likelihood": "Unclear",
            "severity": "Unclear",
            "risk_level": "Unclear",
            "rationale": "",
        },
        "corrective_actions": [],
        "verification": "",
        "limitations": "",
        "citations": [],
    }
    if not hits:
        base["limitations"] = (
            "No matching library passages were found. Broaden the authority/source selection "
            "or index the applicable standard before relying on this analysis."
        )
        return base

    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[S{i}] {hit.title} — page {hit.page_no} ({hit.collection})\n{hit.text.strip()[:2200]}"
        )
    user = (
        f"Problem brief:\n{run.problem_brief.strip() or 'No separate brief supplied; infer the problem from the document.'}\n\n"
        f"Procedure / document under review: {run.filename}\n{_problem_source_excerpt(run)}\n\n"
        + (f"Owner instructions: {run.instructions}\n\n" if run.instructions else "")
        + "Library passages (cite by [S#], document title and page):\n\n"
        + "\n\n".join(blocks)
    )
    try:
        import litellm

        response = litellm.completion(
            model=run.model,
            messages=[
                {"role": "system", "content": PROBLEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=3000,
            response_format={"type": "json_object"},
            api_key=settings.openai_api_key,
            timeout=150,
        )
        data = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:  # noqa: BLE001
        base["limitations"] = f"Analysis failed: {type(exc).__name__}: {str(exc)[:240]}"
        return base

    def text(value: Any, limit: int = 4000) -> str:
        return str(value or "").strip()[:limit]

    base["problem_understanding"] = text(data.get("problem_understanding"), 5000) or base["problem_understanding"]
    for key, fields in (
        ("applicable_requirements", ("requirement", "authority", "document", "clause", "evidence", "relevance")),
        ("procedure_evidence", ("finding", "document", "clause", "evidence")),
        ("gaps_or_conflicts", ("issue", "why_it_matters", "severity", "evidence")),
        ("contributing_factors", ("factor", "explanation", "confidence")),
        ("corrective_actions", ("action", "owner", "priority", "verification")),
    ):
        raw = data.get(key)
        if not isinstance(raw, list):
            continue
        clean = []
        for item in raw[:12]:
            if not isinstance(item, dict):
                continue
            row = {field: text(item.get(field), 1200) for field in fields}
            if "page" in item:
                try:
                    row["page"] = int(item.get("page") or 0)
                except (TypeError, ValueError):
                    row["page"] = 0
            clean.append(row)
        base[key] = clean
    risk = data.get("risk_assessment")
    if isinstance(risk, dict):
        base["risk_assessment"] = {
            k: text(risk.get(k), 800)
            for k in ("likelihood", "severity", "risk_level", "rationale")
        }
    base["verification"] = text(data.get("verification"), 3000)
    base["limitations"] = text(data.get("limitations"), 3000)
    by_title = {hit.title.lower(): hit for hit in hits}
    for item in base["applicable_requirements"]:
        match = by_title.get((item.get("document") or "").lower())
        if match is None:
            match = next(
                (h for h in hits if item.get("document") and item["document"].lower() in h.title.lower()),
                None,
            )
        if match is not None:
            item["document_id"] = match.document_id
            try:
                page = int(item.get("page") or 0)
            except (TypeError, ValueError):
                page = 0
            if page not in {h.page_no for h in hits if h.document_id == match.document_id}:
                item["page"] = match.page_no
    base["citations"] = [
        {
            "ref": f"S{i}",
            "document": hit.title,
            "collection": hit.collection,
            "document_id": hit.document_id,
            "page": hit.page_no,
        }
        for i, hit in enumerate(hits, start=1)
    ]
    if conn is not None:
        _verify_problem_citations(conn, base, hits, run)
    return base


def _execute(run: Run) -> None:
    conn = connect(Path(settings.data_dir) / "aerovault.db")
    try:
        if run.mode in ("problem", "improvement"):
            query = " ".join(
                [run.problem_brief, run.filename]
                + [c.get("heading", "") for c in run.clauses[:8]]
            ).strip()
            doc_ids = [s["id"] for s in run.standards if s["id"] != run.document_id]
            hits = _retrieve(
                conn,
                query[:3000],
                doc_ids or None,
                Path(settings.data_dir) / "lancedb",
                k=12,
                authorities=[] if run.standards else run.authorities,
                exclude_doc_id=run.document_id,
            )
            narrative = _analyse_problem(run, hits, conn)
            with _LOCK:
                run.narrative = narrative
                run.progress = 1
            if run.cancel.is_set():
                run.status = "cancelled"
                _save_meta(run)
                return
            run.status = "done"
            _save_meta(run)
            return
        for i, clause in enumerate(run.clauses, start=1):
            if run.cancel.is_set():
                run.status = "cancelled"
                _save_meta(run)
                return
            query = f"{clause.get('heading', '')}\n{clause.get('text', '')[:1200]}".strip()
            hits = _retrieve(conn, query, [s["id"] for s in run.standards], Path(settings.data_dir) / "lancedb")
            result = _compare(run, clause, hits)
            with _LOCK:
                run.results.append(result)
                run.progress = i
    except Exception as exc:  # noqa: BLE001
        run.error = f"{type(exc).__name__}: {exc}"[:400]
        run.status = "error"
        _save_meta(run)
        return
    finally:
        conn.close()
    if not run.cancel.is_set():
        run.status = "done"
        _save_meta(run)


@router.post("/{run_id}/run")
def start_run(run_id: str, body: RunBody, conn=Depends(_get_conn), _user=Depends(_user)) -> dict:
    run = _run_or_404(run_id)
    if run.status == "running":
        raise HTTPException(status_code=409, detail="This run is already in progress")
    model = body.model if body.model in ALLOWED_MODELS else DEFAULT_MODEL
    mode = body.mode.strip().lower()
    if mode not in ("gap", "problem", "improvement"):
        raise HTTPException(status_code=400, detail="mode must be gap, problem or improvement")
    if mode == "gap" and not body.standard_ids:
        raise HTTPException(status_code=400, detail="Select at least one standard for a gap review")
    standards = _standards(conn, body.standard_ids) if body.standard_ids else []
    extras = [x.strip()[:40] for x in body.extra_columns if x.strip()]
    if len(extras) > MAX_EXTRA_COLUMNS:
        raise HTTPException(status_code=400, detail="At most 3 extra columns are allowed")
    source_clauses = body.clauses or [
        ClauseBody(id=c["id"], heading=c.get("heading", ""), text=c.get("text", ""))
        for c in run.clauses
    ]
    clauses = []
    for i, c in enumerate(source_clauses[:MAX_CLAUSES], start=1):
        if not c.text.strip() and not c.heading.strip():
            continue
        clauses.append({"id": str(i), "heading": c.heading.strip(), "text": c.text.strip()[:8000]})
    if not clauses:
        raise HTTPException(status_code=400, detail="At least one clause with text is required")
    brief = body.problem_brief.strip()
    if mode in ("problem", "improvement") and not brief:
        brief = f"Analyse the supplied document for problems, gaps and improvement opportunities: {run.filename}"
    authorities = []
    for authority in body.authorities:
        clean = authority.strip()[:60]
        if clean and clean.lower() not in {x.lower() for x in authorities}:
            authorities.append(clean)
    run.clauses = clauses
    run.standards = standards
    run.model = model
    run.extra_columns = extras
    run.instructions = body.instructions.strip()
    run.mode = mode
    run.problem_brief = brief[:6000]
    run.authorities = authorities
    run.narrative = {}
    run.status = "running"
    run.progress = 0
    run.results = []
    run.error = ""
    run.cancel.clear()
    _save_meta(run)
    threading.Thread(target=_execute, args=(run,), daemon=True).start()
    return _public(run)


@router.get("/history")
def history(limit: int = 50, conn=Depends(_get_conn), _user=Depends(_user)) -> dict:
    _cleanup()
    limit = max(1, min(limit, 100))
    rows = conn.execute(
        "SELECT run_id, filename, document_id, mode, created_at, expires_at, model, "
        "standards_json, authorities_json, status, progress, total, error "
        "FROM compliance_runs WHERE expires_at >= ? ORDER BY created_at DESC LIMIT ?",
        (datetime.now(timezone.utc).isoformat(), limit),
    ).fetchall()
    return {"runs": [_meta_row(r) for r in rows], "retention_days": 90}


@router.delete("/history/{run_id}")
def delete_history(run_id: str, conn=Depends(_get_conn), _user=Depends(_user)) -> dict:
    conn.execute("DELETE FROM compliance_runs WHERE run_id = ?", (run_id,))
    conn.commit()
    with _LOCK:
        _RUNS.pop(run_id, None)
    return {"ok": True}


@router.get("/{run_id}")
def get_run(run_id: str, _user=Depends(_user)) -> dict:
    return _public(_run_or_404(run_id))


@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, _user=Depends(_user)) -> dict:
    run = _run_or_404(run_id)
    run.cancel.set()
    run.status = "cancelled"
    _save_meta(run)
    return _public(run)


@router.delete("/{run_id}")
def delete_run(run_id: str, _user=Depends(_user)) -> dict:
    with _LOCK:
        _RUNS.pop(run_id, None)
    try:
        conn = connect(Path(settings.data_dir) / "aerovault.db")
        try:
            conn.execute("DELETE FROM compliance_runs WHERE run_id = ?", (run_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


def _safe_name(name: str) -> str:
    stem = Path(name).stem[:60]
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", stem) or "procedure"


def _problem_xlsx(run: Run) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    n = run.narrative
    wb = Workbook()
    ws = wb.active
    ws.title = "Problem analysis"
    ws.append(["AeroVault problem-driven analysis"])
    ws["A1"].font = Font(bold=True, size=14, color="0F4C81")
    ws.append(["Document", run.filename])
    ws.append(["Mode", run.mode])
    ws.append(["Model", run.model])
    ws.append(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    ws.append(["Problem understanding", n.get("problem_understanding", "")])
    risk = n.get("risk_assessment") or {}
    ws.append(["Risk", f"{risk.get('risk_level', 'Unclear')} (likelihood {risk.get('likelihood', 'Unclear')}, severity {risk.get('severity', 'Unclear')})"])
    ws.append(["Risk rationale", risk.get("rationale", "")])
    ws.append(["Verification", n.get("verification", "")])
    ws.append(["Limitations", n.get("limitations", "")])
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 100
    for row in ws.iter_rows(min_row=2):
        row[0].font = Font(bold=True)
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    def sheet(name: str, headers: list[str], rows: list[list], widths: list[int]) -> None:
        sh = wb.create_sheet(name)
        sh.append(headers)
        for cell in sh[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="0F4C81")
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for row in rows:
            sh.append(row)
        for i, width in enumerate(widths, start=1):
            sh.column_dimensions[get_column_letter(i)].width = width
        for row in sh.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        sh.freeze_panes = "A2"

    sheet(
        "Requirements",
        ["#", "Requirement", "Authority", "Document", "Clause", "Page", "Evidence", "Relevance"],
        [
            [i, r.get("requirement", ""), r.get("authority", ""), r.get("document", ""),
             r.get("clause", ""), r.get("page", 0), r.get("evidence", ""), r.get("relevance", "")]
            for i, r in enumerate(n.get("applicable_requirements", []), start=1)
        ],
        [5, 45, 14, 35, 14, 7, 50, 40],
    )
    sheet(
        "Findings",
        ["#", "Issue / gap", "Why it matters", "Severity", "Evidence"],
        [
            [i, r.get("issue", ""), r.get("why_it_matters", ""), r.get("severity", ""), r.get("evidence", "")]
            for i, r in enumerate(n.get("gaps_or_conflicts", []), start=1)
        ],
        [5, 45, 55, 10, 55],
    )
    sheet(
        "Actions",
        ["#", "Action", "Owner", "Priority", "Verification"],
        [
            [i, r.get("action", ""), r.get("owner", ""), r.get("priority", ""), r.get("verification", "")]
            for i, r in enumerate(n.get("corrective_actions", []), start=1)
        ],
        [5, 60, 22, 10, 50],
    )
    sheet(
        "Citations",
        ["Ref", "Document", "Collection", "Page"],
        [[c.get("ref", ""), c.get("document", ""), c.get("collection", ""), c.get("page", 0)] for c in n.get("citations", [])],
        [8, 60, 18, 8],
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _problem_docx(run: Run) -> bytes:
    from docx import Document

    n = run.narrative
    doc = Document()
    doc.add_heading("Problem-driven analysis", level=0)
    doc.add_paragraph(f"Document: {run.filename}")
    doc.add_paragraph(f"Mode: {run.mode}  |  Model: {run.model}  |  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_heading("Problem understanding", level=1)
    doc.add_paragraph(n.get("problem_understanding", ""))

    def bullets(title: str, key: str, field: str) -> None:
        items = n.get(key) or []
        if not items:
            return
        doc.add_heading(title, level=1)
        for item in items:
            doc.add_paragraph(str(item.get(field, "")), style="List Bullet")
            extras = [f"{k.replace('_', ' ').title()}: {v}" for k, v in item.items() if k != field and v]
            if extras:
                doc.add_paragraph("; ".join(extras), style="List Bullet 2")

    doc.add_heading("Applicable requirements", level=1)
    requirements = n.get("applicable_requirements") or []
    if requirements:
        table = doc.add_table(rows=1, cols=5)
        table.style = "Light Grid Accent 1"
        for i, h in enumerate(["Requirement", "Authority / document", "Clause", "Page", "Evidence"]):
            table.rows[0].cells[i].text = h
        for item in requirements:
            cells = table.add_row().cells
            values = [
                item.get("requirement", ""),
                f"{item.get('authority', '')} / {item.get('document', '')}",
                item.get("clause", ""),
                str(item.get("page", 0)),
                item.get("evidence", ""),
            ]
            for i, value in enumerate(values):
                cells[i].text = str(value)[:900]
    bullets("Gaps or conflicts", "gaps_or_conflicts", "issue")
    bullets("Contributing factors", "contributing_factors", "factor")
    bullets("Corrective actions", "corrective_actions", "action")
    doc.add_heading("Risk assessment", level=1)
    risk = n.get("risk_assessment") or {}
    doc.add_paragraph(
        f"Risk level: {risk.get('risk_level', 'Unclear')}; likelihood: {risk.get('likelihood', 'Unclear')}; "
        f"severity: {risk.get('severity', 'Unclear')}. {risk.get('rationale', '')}"
    )
    doc.add_heading("Verification and limitations", level=1)
    doc.add_paragraph(n.get("verification", ""))
    doc.add_paragraph(n.get("limitations", ""))
    citations = n.get("citations") or []
    if citations:
        doc.add_heading("Page citations", level=1)
        for citation in citations:
            doc.add_paragraph(
                f"[{citation.get('ref', '')}] {citation.get('document', '')} — page {citation.get('page', 0)}",
                style="List Bullet",
            )
    doc.add_paragraph(
        "Decision-support output. Verify every finding against the cited source page before acting."
    )
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _xlsx(run: Run) -> bytes:
    if run.narrative and run.mode in ("problem", "improvement"):
        return _problem_xlsx(run)
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance matrix"
    headers = [
        "#", "Procedure clause", "Procedure heading", "Procedure excerpt", "Status",
        "Requirement", "Standard", "Standard clause", "Page", "Evidence", "Rationale",
        "Recommended action", "Confidence",
    ] + run.extra_columns
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0F4C81")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    fills = {
        "Compliant": "D9EAD3", "Partial": "FFF2CC", "Gap": "F4CCCC",
        "Not applicable": "E8EAED", "Unclear": "DDEBF7",
    }
    for idx, r in enumerate(run.results, start=1):
        row = [
            idx, r["clause_id"], r["clause_heading"], r["clause_excerpt"], r["status"],
            r["requirement"], r["standard"], r["standard_clause"], r["page"], r["evidence"],
            r["rationale"], r["action"], r["confidence"],
        ] + [r.get("extras", {}).get(c, "") for c in run.extra_columns]
        ws.append(row)
        fill = fills.get(r["status"])
        if fill:
            ws.cell(row=ws.max_row, column=5).fill = PatternFill("solid", fgColor=fill)
    widths = [5, 10, 30, 50, 14, 40, 32, 14, 7, 45, 50, 40, 11] + [18] * len(run.extra_columns)
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.append([])
    ws.append(["Decision-support output — verify every clause against the cited standard before use."])
    ws.cell(row=ws.max_row, column=1).font = Font(italic=True, color="666666")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _docx(run: Run) -> bytes:
    if run.narrative and run.mode in ("problem", "improvement"):
        return _problem_docx(run)
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.add_heading("Compliance gap analysis", level=0)
    doc.add_paragraph(f"Procedure: {run.filename}")
    doc.add_paragraph("Standards: " + "; ".join(s["title"] for s in run.standards))
    doc.add_paragraph(f"Model: {run.model}  |  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    counts: dict[str, int] = {}
    for r in run.results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    doc.add_heading("Executive summary", level=1)
    doc.add_paragraph(
        "Clauses analysed: "
        + str(len(run.results))
        + ". "
        + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    )
    doc.add_heading("Compliance matrix", level=1)
    headers = ["#", "Clause", "Status", "Requirement", "Standard / page", "Evidence", "Action"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for r in run.results:
        cells = table.add_row().cells
        values = [
            r["clause_id"], r["clause_heading"] or r["clause_excerpt"][:80], r["status"],
            r["requirement"], f"{r['standard']} p.{r['page']}", r["evidence"], r["action"],
        ]
        for i, value in enumerate(values):
            cells[i].text = str(value)[:900]
    doc.add_heading("Method and limitations", level=1)
    doc.add_paragraph(
        "Each clause was compared only with the selected standards' retrieved passages. "
        "This is a decision-support output, not a certification or legal opinion. "
        "Verify every finding against the cited standard page before acting."
    )
    for p in doc.paragraphs:
        for run_obj in p.runs:
            run_obj.font.size = Pt(9) if p.style.name == "Normal" else run_obj.font.size
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@router.get("/{run_id}/export.xlsx")
def export_xlsx(run_id: str, _user=Depends(_user)):
    run = _run_or_404(run_id)
    if not run.results and not run.narrative:
        raise HTTPException(status_code=400, detail="Run has no results yet")
    data = _xlsx(run)
    suffix = "analysis" if run.narrative and run.mode in ("problem", "improvement") else "compliance"
    name = f"{_safe_name(run.filename)}_{suffix}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/{run_id}/export.docx")
def export_docx(run_id: str, _user=Depends(_user)):
    run = _run_or_404(run_id)
    if not run.results and not run.narrative:
        raise HTTPException(status_code=400, detail="Run has no results yet")
    data = _docx(run)
    suffix = "analysis" if run.narrative and run.mode in ("problem", "improvement") else "compliance"
    name = f"{_safe_name(run.filename)}_{suffix}.docx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
