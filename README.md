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

- UI: http://127.0.0.1:5273
- API health: http://127.0.0.1:18000/api/health

Both host ports are bound to `127.0.0.1` only; nothing is exposed to the network. Host ports 18000/5273 were chosen because 8000/5173 are used by other local containers. The library is mounted read-only at `/library`.

## Ingestion (Phase 2)

**Use the native runner (recommended).** The Docker bind mount to a OneDrive folder is
about 40x slower for file reads (a full scan took 31 s natively vs 20+ min in Docker,
with no progress). Native ingestion writes to the same `data/` folder the app uses.

```powershell
# one-time: install native libs
py -3 -m pip install --target .work\native_libs pydantic-settings pypdf pymupdf lancedb litellm pillow pytesseract

.\scripts\ingest.ps1 scan            # discover + hash (seconds)
.\scripts\ingest.ps1 ingest -NoVectors   # full text index, no API calls
.\scripts\ingest.ps1 vectors-only    # embeddings + LanceDB (needs API credits)
.\scripts\ingest.ps1 status
```

Notes:

- Without API credits the pipeline indexes text only (`text_only` status); `vectors-only` backfills vectors later.
- The Docker route still works: `docker compose exec backend python -m app.ingest.pipeline ...` but is much slower on OneDrive.
- OCR for the 53 scanned documents (D-018), after the first index:
  `.\scripts\ingest.ps1 ingest -Ocr -Force -Collection "Aircraft Theory"` (and the other collections).
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
