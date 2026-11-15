# 7. Architecture Decisions (ADR)

**Project:** AeroVault — local aviation library and LLM decision-support tool
**Version:** 0.1 (draft for Gate 1 owner review)
**Date:** 2026-11-13
**Status:** Approved at Gate 1 (2026-11-13); Phase 2 implemented

## 1. Context

AeroVault is a purpose-built, password-protected web application that indexes the owner's local aviation library (639 PDFs, ~210,502 pages across Aircraft Theory, Aviation HF and Quality ISO SAE) and lets an LLM answer questions with page-level citations. It runs on a single Windows PC, is reachable only on `localhost`, and uses an OpenAI API key (other providers optional).

The decisions below define the Phase 1 foundation. They will be revisited if the owner's Gate 1 review changes requirements.

## 2. Decisions

| ID | Decision | Rationale | Alternatives considered | Status |
|----|----------|-----------|--------------------------|--------|
| D-023 | **Monorepo layout:** `backend/`, `frontend/`, `Project_Documents/`, `data/` (runtime, git-ignored), `docker-compose.yml` at root | Single owner, single machine; one-command startup; plan documents versioned with the code | Separate repos per service (overhead); monorepo with workspaces (unneeded complexity) | Proposed |
| D-024 | **Backend:** Python 3.11 + FastAPI + Uvicorn | Matches host Python 3.11.10; mature PDF tooling (pypdf); OpenAPI docs for free; async-ready for streaming chat | Flask (weaker typing/streaming); Node backend (weaker PDF tooling) | Proposed |
| D-025 | **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS 3 | Fast dev server, typed UI, utility-first styling for the dashboard/charts in the wireframes | Next.js (SSR not needed); plain HTML/JS (poor fit for chat UI) | Proposed |
| D-026 | **Storage:** SQLite for metadata (documents, pages, chunks, sessions, audit log) + LanceDB for vectors under `data/`; PDFs indexed in place from the library root, never copied | Zero external services; portable; files stay where the owner keeps them | PostgreSQL + pgvector (needs a server; heavier); Chroma/Qdrant (extra service) | Proposed |
| D-027 | **LLM gateway:** LiteLLM with provider profiles (OpenAI default; Azure/Ollama optional). Default chat model `gpt-4o-mini`, default embeddings `text-embedding-3-small` (1536-d), all configurable via `.env` | Provider-agnostic; per-query model switch; low cost for daily use | Direct OpenAI SDK (locks in one provider); LangChain (heavy abstraction) | Proposed |
| D-028 | **Security:** Argon2id password hash; server-side sessions in HttpOnly, SameSite=Strict cookies; every port bound to `127.0.0.1`; secrets only in `.env` (git-ignored); no telemetry | Password-protected access on a shared office PC; localhost-only exposure | Basic auth (weak); JWT in localStorage (XSS-exposed) | Proposed |
| D-029 | **Compose baseline:** services `backend` (`127.0.0.1:8000`) and `frontend` (`127.0.0.1:5173`) with a Vite dev proxy `/api` → `backend`; volume `./data:/data` | Localhost-only by construction; no CORS in dev; one compose file | Host networking (Windows pain); separate nginx (needed only for release) | Proposed |
| D-030 | **Version control:** local git repo at project root; GitHub push only after Gate 1 owner review; `.work/`, `_QUARANTINE/`, `data/` and `.env` excluded | Keeps 1 GB of quarantined duplicates and runtime data out of history | Git LFS for everything (heavy); no VCS (no rollback) | Proposed |

## 3. Stack summary

| Layer | Choice | Notes |
|-------|--------|-------|
| UI | React 18 + Vite + TS + Tailwind | Login, library, reader, chat with citations |
| API | FastAPI (Python 3.11) | Streaming answers, page citations |
| Metadata | SQLite (SQLAlchemy 2.x) | Single file under `data/` |
| Vectors | LanceDB | Embedded, no server |
| LLM | LiteLLM → OpenAI (default) | Configurable provider/model |
| Auth | Argon2id + server sessions | HttpOnly cookies |
| Runtime | Docker Compose | localhost-only ports |

## 4. Phase 1 deliverables

1. Repository skeleton (`backend/`, `frontend/`, compose, env template, README).
2. Local git repository with an initial commit.
3. This ADR and updated step log.
4. Gate 1 review: owner approves architecture and UX before Phase 2 coding.

## 5. Open questions for Gate 1 review

1. **UI style** — light "aviation chart" theme, dark "cockpit" theme, or system-adaptive? The wireframes draft assumes light.
2. **Ports** — is the pair 5173 (UI) / 8000 (API) acceptable during development, or do you prefer a single port (e.g., 8080) from day one?
3. **Default chat model** — `gpt-4o-mini` (cheap, fast) as default with a per-query switch to a stronger reasoning model, or a stronger default from the start?
4. **Query history** — should the app keep a searchable history of questions/answers by default (useful for audit and reuse), or keep sessions ephemeral?
5. **Embeddings** — `text-embedding-3-small` as default (cheaper, ~5x less than large), or `-large` for better retrieval quality?

## 6. Gate 1 approval (2026-11-13)

The owner approved the architecture and all recommendations. Resolutions: light "aviation chart" UI with dark mode later (D-032); host ports 5273/18000 in development because 5173/8000 are occupied by other local containers, container ports unchanged, single 8080 at release (D-033); `gpt-4o-mini` default with per-query switch (D-034); searchable history with delete (D-035); `text-embedding-3-small` first (D-036); private GitHub repo created (D-037). Phase 3 UX: first-run password setup, 8-hour sessions with remember-me, streaming answers, PDF.js in-app viewer (D-043–D-046).

## 7. Phase 2 implementation decisions

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D-038 | BM25 via SQLite FTS5 over a `chunks` table, kept in sync with triggers | No extra service; works offline; hybrid partner for vectors | Implemented |
| D-039 | Page-aware chunking: 3,000 characters (~750 tokens) with 400-character overlap, never crossing pages | Page-level citations require page-safe chunks | Implemented |
| D-040 | Reciprocal Rank Fusion (k=60) to merge BM25 and vector result lists | Simple, robust, no training needed | Implemented |
| D-041 | Benchmark runner parses `6_Retrieval_Benchmark.md`, writes top-5 CSV; scoring once `benchmark_expected.csv` (qnum, doc_contains, page) is filled | Gate 2 evidence with minimal manual work | Implemented |
| D-042 | Private GitHub repo `github.com/Martinolli/AeroVault`, pushed from the owner's `gh` login | Version control after Gate 1 approval (D-037) | Done |
| D-047 | Ingestion runs natively on Windows (`scripts/ingest.ps1`), not inside Docker: the bind mount to the OneDrive library is ~40x slower (full scan 31 s native vs 20+ min with no progress). The app stays in Docker; both share `data/` | Keeps daily re-indexing practical | Implemented |
| D-048 | Status model `pending → text_only → indexed`; `vectors-only` backfills embeddings for text-indexed documents; `vectors` column tracks completion | Allows text/BM25 index without API credits, vectors added later | Implemented |
| D-049 | OpenAI account returned 429 "no credits remaining"; embeddings deferred until billing is resolved (alternatives: add credits, Azure OpenAI, local model) | Blocker discovered during first ingest | Open — owner action |
| D-050 | Per-document PDF passwords in git-ignored `data/pdf_passwords.json` (DO-160F: `mk3ja5`); extractor tries empty password, then the mapped one | Keeps secrets out of code while indexing encrypted standards | Implemented |

**Extraction order:** PyMuPDF primary, pypdf fallback (offline mode); Tesseract OCR opt-in via `--ocr` for the 53 scanned documents (D-018), run as a background re-ingest after the first index.

**Vectors:** written to LanceDB table `chunks` (vector, document_id, page_no, chunk_id); document vectors are deleted and re-added on re-ingest.

**Ingestion runner:** `scripts/ingest.ps1` wraps `app.ingest.pipeline` with the native Python (`.work/native_libs`) and explicit `data/aerovault.db` / `data/lancedb` paths. The pipeline also scans only the three collection folders — never the whole library root (which contains 8,400+ other PDFs).
| D-051 | LanceDB `latest_version_hint.json` may fail to persist under the OneDrive mount/AV lock (warning only). Upserts delete a document's rows before re-adding, so reruns are idempotent; if a row-count mismatch appears, delete the hint file to force a version scan | Integrity verified: 184,317 LanceDB rows = 184,317 chunks of indexed documents | Implemented |
| D-052 | Production retrieval = hybrid BM25 + vector RRF with equal weights (k=60), BM25-only remains available (`--no-vectors`); a title-aware boost was added after the expected pages were verified (D-061) | Hybrid fixes semantic questions that BM25 alone misses; equal weights beat vector-heavy variants in the final grid | Implemented |
| D-053 | OCR runs through the `ocr` command with explicit Tesseract path and page preprocessing (grayscale, 6% margin crop, autocontrast, psm 6); documents that still yield no text are marked `error` instead of being silently indexed empty | Full-page OCR returned 0 characters on framed scans; the crop variant returned 3,400+ characters per page | Implemented |
| D-054 | LLM query expansion + rerank of 40 hybrid candidates was built and tested, then **rejected**: the reranker still omitted Q3's expected MRM p.16 passage even with the Swiss-cheese sentence in the snippet, and cost ~15.6 s/query | Verified expected pages show document-level misses, but the LLM reranker was not reliable enough and too slow for chat | Rejected — replaced by D-061 |
| D-061 | Title-aware RRF: after fusion, add `0.012 × (query-term/title-term overlap)` to each hit's score | +9 points top-5 on the verified benchmark (54.5% → 63.6%) at zero latency cost; best of the tested fusion variants (pools 50/100/200, vector weights 1–3, max/normalised fusion) | Implemented |
| D-062 | Do **not** migrate the corpus to `text-embedding-3-large`: pilot on 7,814 chunks from the 17 expected documents ranked the expected page in the top-5 for 16/22 questions vs 18/22 with `-small` | A full re-embed (~184k chunks) costs money and hours with no measured page-level gain; `-small` stays (D-036) | Rejected — keep `-small` |
| D-063 | OCR backfill resumed after the owner approved running it in parallel with retrieval work; it processes Aviation HF → Quality → Aircraft Theory and commits per document | `text_only` dropped from 47 to 22 while running; remaining books are mostly Aircraft Theory | Running — resumable |

## 9. Phase 4 decisions (2026-11-14)

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D-064 | Gate 3 is marked **passed** on the owner's review (clean UI, persistent history, comprehensive answers on both models, tables render well) | Owner explicitly accepted the MVP on 2026-11-14 | Passed |
| D-065 | Chat answers render LaTeX with `remark-math` + `rehype-katex`; the system prompt asks for `$...$` inline and `$$...$$` display math | Aeronautics and dynamics books are formula-heavy; KaTeX is client-side and safe (no raw HTML) | Implemented |
| D-066 | Compliance workspace (W3): PDF + DOCX input; DOCX + XLSX output; clause-level matching against standards named per request; up to 3 optional columns; OCR opt-in; 60-clause cap; uploads transient and never stored or embedded | Owner wants a practical gap-check tool without polluting the library index; clause-level gives actionable results | Implemented — MVP tested |
| D-067 | Formula rendering normalises both `\(...\)`/`\[...\]` and `$...$`/`$$...$$` before KaTeX; the owner's formula test DOCX showed the model emitted parenthesis delimiters | KaTeX only understands dollar delimiters; supporting both avoids broken formulas regardless of model style | Implemented |
| D-068 | Compliance run history is metadata only (file name, date, mode, standards/authorities, model, status counts, error), 90-day retention, deletable; never store procedure text, briefs, clauses or full results; optional "keep full result" remains deferred | Gives traceability without turning the app into a document store; matches the transient-upload decision | Implemented |
| D-069 | Compliance modes are `problem` (default), `improvement` and `gap`. Problem/improvement use a flexible narrative prompt; gap keeps the clause-level JSON comparison. A `mode` field and problem brief are persisted only in the in-memory run, not in history | Owner asked for problem-driven analysis first and no fixed output template; the matrix remains available when explicitly requested | Implemented |
| D-070 | A compliance run can start from an uploaded PDF/DOCX or an indexed library document (`POST /api/compliance/library/{doc_id}`). Indexed pages are copied into the transient run; the source document is excluded from standards retrieval | Avoids duplicate uploads and self-citation while keeping the library unchanged | Implemented |
| D-071 | Problem/improvement retrieval can use selected documents or an authority filter (`FAA`, `EASA`, `ICAO`, `AQAP`, `NASA`, `BOOKS`); no selected documents means all indexed sources. FAA/EASA are primary, the rest secondary | Matches the owner's source hierarchy and supports both focused and exploratory requests | Implemented |
| D-072 | Regulatory ingestion is manifest-driven (`data/regulatory_sources.json`) with official HTTPS URLs, authority/type/version/effective date, SHA-256 and local path. eCFR XML is downloaded from the official API and a text companion is written; EASA/ICAO copyright is respected | Controlled, auditable downloads are safer than an uncontrolled crawler and preserve revision/checksum evidence | Implemented — foundation; core pack pending |
| D-073 | Project knowledge is packaged as the `aerovault-project` skill (SKILL.md + references for project map, operations, compliance and regulatory ingestion + healthcheck script) | Gives future Manus sessions the non-obvious paths, guardrails and operating commands without relying on conversation history | Implemented |
| D-074 | The approved FAA core pack is downloaded from official endpoints and indexed: eCFR Parts 5, 91, 121, 135, AC 120-92D and AC 21-58; six documents / 1,027 chunks, all vectorised. Runtime checksums/status stay in `data/regulatory_sources.json`; the tracked template contains only planned metadata | Focused, auditable source set for operations/SMS and manufacturing-quality use cases; avoids indexing the whole 1,358-file regulatory tree before validation | Implemented |
| D-075 | Problem-mode citations are evidence-validated: after the LLM response, the backend searches the cited document's pages for the quoted evidence, corrects the page when a supported match is found, sets unsupported pages to 0, appends a limitation and exposes `citation_verified`. The UI does not open a page-0 citation | A live FAA test showed a correct quote can be attached to a plausible but unsupported page; page-level decision support requires validating the quote against the source text | Implemented — regression test passes |
| D-076 | The EASA Easy Access Rules for Air Operations Rev 24 is downloaded from the official EASA PDF endpoint and indexed (2,566 pages / 3,038 chunks / vectors); the official XML ZIP is retained for future machine-readable processing. The core pack is now seven documents / 4,065 chunks. EASA material stays local and is not redistributed | Completes the approved operations/SMS core pack and gives EASA equal retrieval status with FAA; PDF page numbers are usable immediately, while the XML archive preserves the option of section-level processing later | Implemented |
| D-077 | `GET /api/documents/{id}/file` resolves cited files safely from both `AEROVAULT_LIBRARY_ROOT` and `$AEROVAULT_DATA_DIR/regulatory_library`, strips whitespace from stored `rel_path`, and returns the correct media type. The citation viewer renders PDFs with PDF.js and text-only sources through their indexed page text | FAA/EASA downloads live outside the main library root; eCFR sources are `.txt`, so treating every citation as a PDF caused `Missing PDF` on every regulatory citation | Implemented — regression test passes; Gate 4 UAT passed |

## 10. Phase 5 security decisions (2026-11-15)

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D-078 | Gate 5 security review uses OWASP ASVS-lite and a short STRIDE model, scoped to a single trusted owner and localhost-only deployment; Critical/High findings are fixed before sign-off, Medium/Low are documented | Matches the owner-approved review defaults and keeps the review proportionate to the deployment | Completed — report `15_Gate5_Security_Review.md` |
| D-079 | Runtime image/PDF parser Pillow is pinned to `>=12.3,<14.0` (installed 13.0.0); the backend image upgrades pip and setuptools before installing requirements | Pillow 11.3.0 carried 76 advisories and handles untrusted uploads; pip/setuptools were build-time-only advisories | Implemented — `pip-audit` clean |
| D-080 | Frontend toolchain is Vite 8.3.8 with `@vitejs/plugin-react` 5.2.0; KaTeX is pinned to 0.19.1 through an npm override | Vite 5.4.21 had a high Windows dev-server advisory; the override removes the nested vulnerable KaTeX copies | Implemented — `npm audit` 0, typecheck and build pass |
| D-081 | Login is throttled to 5 failed attempts per client per 15 minutes (HTTP 429, `Retry-After: 900`), with the counter cleared on success | The plan promised login throttling but the endpoint had none; a single owner still benefits from brute-force resistance | Implemented — regression test passes |
| D-082 | Chat, compliance and problem-analysis prompts explicitly treat library/procedure text as untrusted evidence and forbid following embedded instructions | Uploaded and retrieved documents can contain prompt-injection text; citation validation alone cannot detect a manipulated analysis | Implemented — residual model risk remains |
| D-083 | XLSX exports force every string cell to text (`data_type="s"`) after append | Prevents a formula-like value in a document or model answer from becoming an active Excel formula | Implemented — regression test passes |
| D-084 | `.env`, `data/aerovault.db`, root containers, ACLs and backup/restore remain documented owner decisions for Gate 5 handover; no data or index migration was performed | The trusted-owner model accepts these as Medium/Low, but strict local-only data residency and recovery readiness need owner confirmation | Open — owner decision |

## 8. Phase 3 implementation decisions (2026-11-14)

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D-055 | Chat pipeline: hybrid retrieval (`k=16`) → dedupe by (document, page) → top 8 sources, each capped at 1,600 chars; one system prompt with a strict citation contract; SSE frames `sources`, `delta`, `done`, `error` | Page-level citations and a visible source list require stable source tags; dedupe stops the same page appearing twice; SSE keeps the first token fast | Implemented |
| D-056 | History schema `chats` + `chat_messages` (role, content, `sources_json`); search across title and message text; cascade delete | D-035 requires searchable history with delete; JSON keeps the source cards reproducible when reopening a chat | Implemented |
| D-057 | SQLite connections use `check_same_thread=False` and `PRAGMA busy_timeout=8000`; **WAL mode is not used** while `data/` is a Docker Desktop bind mount on OneDrive | Streaming responses close connections from a worker thread; WAL over the Windows/Linux bind mount produced `disk I/O error` / `database disk image is malformed` in the container even though `integrity_check` passed natively | Implemented |
| D-058 | Docker `.env` changes require `docker compose up -d --force-recreate backend`; `restart` keeps the old environment | A revoked OpenAI key stayed in the container and caused 401 embedding retries long after `.env` was updated | Documented |
| D-059 | OCR backfill is paused while the app is in daily use; resume with `scripts\ingest.ps1 ocr` (Aviation HF → Quality → Aircraft Theory) | OCR commits large page batches and contends with app writes on the single SQLite file; 47 `text_only` books remain, mostly Aircraft Theory (peripheral) | Paused — resumable |
| D-060 | Frontend adds `pdfjs-dist` (worker via `?url`), `react-markdown` + `remark-gfm`, and a PostCSS config for Tailwind; citations are markdown links rewritten to `#cite-S#` and rendered as buttons | Keeps answers readable (tables/lists) and makes every `[S#]` a one-click jump to the cited PDF page | Implemented |
