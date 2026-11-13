# AeroVault

Local, password-protected web app that indexes the aviation library (Aircraft Theory, Aviation HF, Quality ISO SAE) and lets an LLM answer questions with page-level citations. Runs on a single Windows PC and is reachable only on `localhost`.

## Status

**Phase 2 — ingestion MVP (code complete, awaiting the owner's first run).** Login, library and chat arrive in Phase 3.

## Layout

```
AeroVault/
├─ backend/            FastAPI service + ingestion/retrieval (Python 3.11)
│  ├─ app/
│  │  ├─ ingest/       scan, extract, chunk, embed, store, pipeline CLI
│  │  └─ retrieve/     hybrid search (BM25 + vectors) and benchmark runner
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/           React + Vite + TypeScript + Tailwind
├─ Project_Documents/  Plan, step log, inspection report, ADR, wireframes, benchmark
├─ data/               Runtime data (SQLite, LanceDB) — git-ignored
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

## Prerequisites

- Docker Desktop (installed on the target PC)
- An OpenAI API key (or another LiteLLM-supported provider)

## Quickstart

```powershell
Copy-Item .env.example .env
# edit .env: set AEROVAULT_OPENAI_API_KEY and AEROVAULT_LIBRARY_ROOT (Windows path with forward slashes)
docker compose up --build -d
```

- UI: http://127.0.0.1:5173
- API health: http://127.0.0.1:8000/api/health

Both ports are bound to `127.0.0.1` only; nothing is exposed to the network. The library is mounted read-only at `/library`.

## Ingestion (Phase 2)

Run inside the backend container:

```powershell
# 1. Discover PDFs and hash them (fast, no API calls)
docker compose exec backend python -m app.ingest.pipeline scan

# 2. Extract, chunk, embed and index in batches (API calls)
docker compose exec backend python -m app.ingest.pipeline ingest --limit 20
# repeat until it reports "Nothing to ingest."

# 3. Status
docker compose exec backend python -m app.ingest.pipeline status
```

Notes:

- Set `AEROVAULT_OPENAI_API_KEY` **before** ingesting; without it the pipeline indexes text only (no vectors).
- OCR for the 53 scanned documents (D-018), after the first index:
  `docker compose exec backend python -m app.ingest.pipeline ingest --ocr --force --collection "Aircraft Theory"` (and the other collections).
- Ingestion is incremental: unchanged files (same SHA-256) are skipped; changed files are re-indexed.

## Retrieval and benchmark (Gate 2)

```powershell
# Ad-hoc query
docker compose exec backend python -m app.retrieve.search "swiss cheese model" --k 5

# Benchmark (writes /data/benchmark_results.csv)
docker compose exec backend python -m app.retrieve.benchmark
```

To score: copy `data/benchmark_results.csv`, fill `data/benchmark_expected.csv` with `qnum,doc_contains,page` from manual page confirmation, then re-run with `--expected /data/benchmark_expected.csv`. Gate 2 passes at top-5 recall ≥ 0.8.

## Project documents

| File | Purpose |
|------|---------|
| `Project_Documents/1_Project_Plan.md` | Plan, gates and milestones |
| `Project_Documents/2_Step_Log.md` | Step-by-step history and decisions |
| `Project_Documents/3_Inspection_Report.md` | Gate 0 library inspection (PASSED 2026-11-13) |
| `Project_Documents/4_Naming_Convention.md` | Library naming rules |
| `Project_Documents/5_Wireframes.md` | UI wireframes |
| `Project_Documents/6_Retrieval_Benchmark.md` | 25-question retrieval benchmark |
| `Project_Documents/7_Architecture_Decisions.md` | Architecture decision record (Gate 1 approved) |
