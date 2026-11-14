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
| D-052 | Production retrieval = hybrid BM25 + vector RRF; BM25-only remains available (`--no-vectors`). Benchmark shows hybrid fixes 7 semantic questions but regresses Q1/Q10, so RRF weights are tuned before Gate 2 | Hybrid median 1.43 s vs BM25 0.85 s; recall gains outweigh latency at prototype scale | Open — tune before Gate 2 |
| D-052 | Production retrieval = hybrid BM25 + vector RRF with equal weights; BM25-only remains available (`--no-vectors`). Stopword/weighted-RRF/title-boost experiments were inconclusive against unverified expected pages, so tuning waits until `benchmark_expected.csv` is confirmed | Draft expected pages gave top-5 59% with equal weights; changing weights moved page hits without a reliable gain | Open — tune after expected pages are verified |
| D-053 | OCR runs through the `ocr` command with explicit Tesseract path and page preprocessing (grayscale, 6% margin crop, autocontrast, psm 6); documents that still yield no text are marked `error` instead of being silently indexed empty | Full-page OCR returned 0 characters on framed scans; the crop variant returned 3,400+ characters per page | Implemented |
| D-054 | Retrieval improvement: LLM-based query expansion + rerank of the top 20 hybrid candidates before answering; benchmark again after the reranker, since Gate 2 scored 54.5% (12/22) | Verified expected pages show document-level misses, not indexing gaps; a reranker can use the question semantics that BM25/RRF miss | Planned — Phase 3 |

## 8. Phase 3 implementation decisions (2026-11-14)

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D-055 | Chat pipeline: hybrid retrieval (`k=16`) → dedupe by (document, page) → top 8 sources, each capped at 1,600 chars; one system prompt with a strict citation contract; SSE frames `sources`, `delta`, `done`, `error` | Page-level citations and a visible source list require stable source tags; dedupe stops the same page appearing twice; SSE keeps the first token fast | Implemented |
| D-056 | History schema `chats` + `chat_messages` (role, content, `sources_json`); search across title and message text; cascade delete | D-035 requires searchable history with delete; JSON keeps the source cards reproducible when reopening a chat | Implemented |
| D-057 | SQLite connections use `check_same_thread=False` and `PRAGMA busy_timeout=8000`; **WAL mode is not used** while `data/` is a Docker Desktop bind mount on OneDrive | Streaming responses close connections from a worker thread; WAL over the Windows/Linux bind mount produced `disk I/O error` / `database disk image is malformed` in the container even though `integrity_check` passed natively | Implemented |
| D-058 | Docker `.env` changes require `docker compose up -d --force-recreate backend`; `restart` keeps the old environment | A revoked OpenAI key stayed in the container and caused 401 embedding retries long after `.env` was updated | Documented |
| D-059 | OCR backfill is paused while the app is in daily use; resume with `scripts\ingest.ps1 ocr` (Aviation HF → Quality → Aircraft Theory) | OCR commits large page batches and contends with app writes on the single SQLite file; 47 `text_only` books remain, mostly Aircraft Theory (peripheral) | Paused — resumable |
| D-060 | Frontend adds `pdfjs-dist` (worker via `?url`), `react-markdown` + `remark-gfm`, and a PostCSS config for Tailwind; citations are markdown links rewritten to `#cite-S#` and rendered as buttons | Keeps answers readable (tables/lists) and makes every `[S#]` a one-click jump to the cited PDF page | Implemented |
