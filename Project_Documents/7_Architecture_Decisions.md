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

The owner approved the architecture and all recommendations. Resolutions: light "aviation chart" UI with dark mode later (D-032); ports 5173/8000 in development, single 8080 at release (D-033); `gpt-4o-mini` default with per-query switch (D-034); searchable history with delete (D-035); `text-embedding-3-small` first (D-036); private GitHub repo created (D-037).

## 7. Phase 2 implementation decisions

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| D-038 | BM25 via SQLite FTS5 over a `chunks` table, kept in sync with triggers | No extra service; works offline; hybrid partner for vectors | Implemented |
| D-039 | Page-aware chunking: 3,000 characters (~750 tokens) with 400-character overlap, never crossing pages | Page-level citations require page-safe chunks | Implemented |
| D-040 | Reciprocal Rank Fusion (k=60) to merge BM25 and vector result lists | Simple, robust, no training needed | Implemented |
| D-041 | Benchmark runner parses `6_Retrieval_Benchmark.md`, writes top-5 CSV; scoring once `benchmark_expected.csv` (qnum, doc_contains, page) is filled | Gate 2 evidence with minimal manual work | Implemented |
| D-042 | Private GitHub repo `github.com/Martinolli/AeroVault`, pushed from the owner's `gh` login | Version control after Gate 1 approval (D-037) | Done |

**Extraction order:** PyMuPDF primary, pypdf fallback (offline mode); Tesseract OCR opt-in via `--ocr` for the 53 scanned documents (D-018), run as a background re-ingest after the first index.

**Vectors:** written to LanceDB table `chunks` (vector, document_id, page_no, chunk_id); document vectors are deleted and re-added on re-ingest.
