# 11 — Compliance Workspace Design (W3)

**Date:** 2026-11-14  |  **Status:** draft for owner approval  |  **Decision:** D-066

## 1. Purpose

Let the owner upload an internal procedure and compare it, clause by clause, against one or more indexed standards (for example AS9100D, ISO 9001 or an ISO/SAE guidance document). The output is an evidence-based compliance matrix with a clear status, the supporting standard clause and page, and a recommended action. It is a decision-support aid, not a certification.

## 2. Confirmed scope (owner, 2026-11-14)

| Item | Decision |
|------|----------|
| Input formats | PDF and DOCX |
| Output formats | DOCX report and XLSX matrix |
| Matching granularity | Clause level |
| Upload persistence | **None** — the uploaded procedure is processed in a temporary folder and deleted after the run; it is not added to SQLite, FTS or LanceDB |
| Standards | Selected from the existing indexed library |
| Language | English |

## 3. User flow

1. Open **Compliance** in the sidebar.
2. Upload a procedure (PDF/DOCX); the backend extracts text and shows the detected clauses in an editable list (clause number, heading, first lines).
3. Select one or more standards from the library (searchable list, default collection: Quality ISO SAE).
4. Choose the model (`gpt-4o-mini` default, `gpt-4o` for deeper analysis) and run.
5. Watch progress per clause (SSE or polling); cancel at any time.
6. Review the matrix in the app: procedure clause, requirement, evidence, status, rationale, action, standard page.
7. Export the DOCX report and/or XLSX matrix.

## 4. Processing design

### 4.1 Extraction and segmentation

- PDF: PyMuPDF text extraction; if a page has almost no text, optionally OCR that page with Tesseract (owner choice; slower).
- DOCX: `python-docx`, preserving heading levels and paragraph numbering.
- Clause detection: numbered headings (`4.1`, `4.1.2`, `5.3.1`, `Section 7`, `A.3`), then bold/short headings, then paragraph blocks. The owner can merge/split/edit clauses before running.
- Limits: maximum 60 clauses and 200 pages per run (configurable); longer documents are truncated with a warning.

### 4.2 Retrieval per clause

For each procedure clause, retrieve the top 3 passages from the selected standards only (hybrid BM25 + vector, filtered by `document_id`), using the clause heading plus its first 1,000 characters as the query. Reuse the existing retrieval stack and page-level metadata.

### 4.3 LLM comparison

One call per clause with a strict JSON contract:

```json
{
  "status": "Compliant | Partial | Gap | Not applicable | Unclear",
  "requirement": "short paraphrase of the applicable requirement",
  "standard_clause": "clause number if visible in the passage",
  "evidence": "short quote from the standard passage (max 40 words)",
  "page": 12,
  "rationale": "why the procedure does or does not satisfy it",
  "action": "specific recommended action, or empty"
}
```

Rules: use only the retrieved standard passages; never invent clause numbers; mark `Unclear` when the procedure text is insufficient; include the passage tag so the page can be verified in the PDF viewer. Default model `gpt-4o-mini`; `gpt-4o` available per run.

### 4.4 Outputs

**XLSX matrix columns:** `#`, `Procedure clause`, `Procedure heading`, `Procedure excerpt`, `Status`, `Requirement`, `Standard`, `Standard clause`, `Page`, `Evidence`, `Rationale`, `Recommended action`, `Confidence`.

**DOCX report:** title page (procedure name, standards, date, model), executive summary (counts by status), matrix table, gaps and actions section, methodology and limitations, short quotes only.

Both exports include a footer: "Decision-support output — verify every clause against the cited standard before use."

### 4.5 API sketch

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/compliance/upload` | multipart PDF/DOCX; returns `run_id`, detected clauses, warnings |
| GET | `/api/compliance/{run_id}/clauses` | editable clause list |
| POST | `/api/compliance/{run_id}/run` | selected standards, model, clause list |
| GET | `/api/compliance/{run_id}/events` | SSE progress (`clause`, `status`, `delta` summary, `done`) |
| POST | `/api/compliance/{run_id}/cancel` | cancel |
| GET | `/api/compliance/{run_id}/result` | matrix JSON |
| GET | `/api/compliance/{run_id}/export.docx` | DOCX report |
| GET | `/api/compliance/{run_id}/export.xlsx` | XLSX matrix |

Runs live in memory plus a temporary folder under `data/compliance_tmp/<run_id>/`; the folder is deleted on completion, cancel or expiry (2 hours). No database rows are written.

## 5. Cost and time (estimate)

| Model | 30 clauses | Notes |
|-------|-----------|-------|
| gpt-4o-mini | ≈ $0.05–0.20 per run, 1–3 min | Default |
| gpt-4o | ≈ $1–2 per run, 2–5 min | Deeper analysis |

Scanned procedures add OCR time (~2–5 s/page). Retrieval uses the existing index, so no re-embedding is needed.

## 6. Implementation slices

1. **Backend core:** upload, PDF/DOCX extraction, clause segmentation, temp-folder lifecycle.
2. **Comparison engine:** per-clause retrieval, JSON contract, validation, progress events, cancel.
3. **Exports:** XLSX (`openpyxl`) and DOCX (`python-docx`) with the agreed columns and disclaimer.
4. **Frontend:** Compliance view (upload → clause editor → standards picker → progress → matrix → export).
5. **Verification:** one AS9100-style procedure sample, one ISO 9001 sample, a scanned PDF, a DOCX, a cancellation test, and an export check; then Gate 4 UAT.

## 7. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Clause segmentation splits or merges sections incorrectly | Editable clause list before the run; show warnings |
| LLM claims a requirement that is not in the passage | Strict JSON contract, quote + page required, `Unclear` fallback, human review banner |
| Standard clause numbering is not visible in the extracted text | Return the page and quote; leave `standard_clause` empty rather than invent it |
| Large procedure costs or time | 60-clause / 200-page caps, per-run cost estimate, cancel button |
| Scanned procedure is slow | OCR opt-in per run; text PDFs recommended |
| Uploaded content is sensitive | Temp folder deleted after run; no indexing; no chat history entry |

## 8. Questions for owner approval

1. Which standards should be offered first — AS9100D and ISO 9001, or also the ISO 31000 / safety-management documents?
2. Is the proposed matrix (status, requirement, evidence, page, rationale, action) sufficient, or do you need extra columns (e.g., risk rating, due date, owner)?
3. Should scanned procedures be OCR'd automatically, or only when you explicitly enable it?
4. Do you want a run history (procedure name, date, standards, result summary) kept locally, or is the exported DOCX/XLSX the only record?
5. Is the 60-clause / 200-page cap acceptable for your typical procedures?
