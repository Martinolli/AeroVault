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
from datetime import datetime, timezone
from pathlib import Path

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
        "status": run.status,
        "progress": run.progress,
        "total": len(run.clauses),
        "model": run.model,
        "standards": run.standards,
        "extra_columns": run.extra_columns,
        "instructions": run.instructions,
        "clauses": run.clauses,
        "results": run.results,
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
    standard_ids: list[int] = Field(min_length=1, max_length=MAX_STANDARDS)
    model: str | None = None
    clauses: list[ClauseBody] = Field(min_length=1, max_length=MAX_CLAUSES)
    extra_columns: list[str] = Field(default_factory=list, max_length=MAX_EXTRA_COLUMNS)
    instructions: str = Field(default="", max_length=1000)


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
    if ocr_pages:
        warnings.append(f"OCR was used on {ocr_pages} page(s).")
    return {"run_id": run.id, "filename": filename, "clauses": clauses, "warnings": warnings}


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


def _retrieve(conn, query: str, doc_ids: list[int], lance_dir: Path, k: int = 3) -> list[Hit]:
    fts = fts_search(conn, query, 40)
    fts = [h for h in fts if h.document_id in doc_ids]
    try:
        import lancedb

        qvec = embed_texts([query], settings.embedding_model, settings.openai_api_key)[0]
        table = lancedb.connect(str(lance_dir)).open_table("chunks")
        where = "document_id IN (" + ",".join(str(int(x)) for x in doc_ids) + ")"
        raw = table.search(qvec).where(where).limit(40).to_list()
        by_id = _enrich(conn, [r["chunk_id"] for r in raw])
        vec = []
        for r in raw:
            hit = by_id.get(r["chunk_id"])
            if hit is not None:
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


def _execute(run: Run) -> None:
    conn = connect(Path(settings.data_dir) / "aerovault.db")
    try:
        for i, clause in enumerate(run.clauses, start=1):
            if run.cancel.is_set():
                run.status = "cancelled"
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
        return
    finally:
        conn.close()
    if not run.cancel.is_set():
        run.status = "done"


@router.post("/{run_id}/run")
def start_run(run_id: str, body: RunBody, conn=Depends(_get_conn), _user=Depends(_user)) -> dict:
    run = _run_or_404(run_id)
    if run.status == "running":
        raise HTTPException(status_code=409, detail="This run is already in progress")
    model = body.model if body.model in ALLOWED_MODELS else DEFAULT_MODEL
    standards = _standards(conn, body.standard_ids)
    extras = [x.strip()[:40] for x in body.extra_columns if x.strip()]
    if len(extras) > MAX_EXTRA_COLUMNS:
        raise HTTPException(status_code=400, detail="At most 3 extra columns are allowed")
    clauses = []
    for i, c in enumerate(body.clauses[:MAX_CLAUSES], start=1):
        if not c.text.strip() and not c.heading.strip():
            continue
        clauses.append({"id": str(i), "heading": c.heading.strip(), "text": c.text.strip()[:8000]})
    if not clauses:
        raise HTTPException(status_code=400, detail="At least one clause with text is required")
    run.clauses = clauses
    run.standards = standards
    run.model = model
    run.extra_columns = extras
    run.instructions = body.instructions.strip()
    run.status = "running"
    run.progress = 0
    run.results = []
    run.error = ""
    run.cancel.clear()
    threading.Thread(target=_execute, args=(run,), daemon=True).start()
    return _public(run)


@router.get("/{run_id}")
def get_run(run_id: str, _user=Depends(_user)) -> dict:
    return _public(_run_or_404(run_id))


@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, _user=Depends(_user)) -> dict:
    run = _run_or_404(run_id)
    run.cancel.set()
    run.status = "cancelled"
    return _public(run)


@router.delete("/{run_id}")
def delete_run(run_id: str, _user=Depends(_user)) -> dict:
    with _LOCK:
        _RUNS.pop(run_id, None)
    return {"ok": True}


def _safe_name(name: str) -> str:
    stem = Path(name).stem[:60]
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", stem) or "procedure"


def _xlsx(run: Run) -> bytes:
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
    if not run.results:
        raise HTTPException(status_code=400, detail="Run has no results yet")
    data = _xlsx(run)
    name = f"{_safe_name(run.filename)}_compliance.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/{run_id}/export.docx")
def export_docx(run_id: str, _user=Depends(_user)):
    run = _run_or_404(run_id)
    if not run.results:
        raise HTTPException(status_code=400, detail="Run has no results yet")
    data = _docx(run)
    name = f"{_safe_name(run.filename)}_compliance.docx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
