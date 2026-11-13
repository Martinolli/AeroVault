# AeroVault

Local, password-protected web app that indexes the aviation library (Aircraft Theory, Aviation HF, Quality ISO SAE) and lets an LLM answer questions with page-level citations. Runs on a single Windows PC and is reachable only on `localhost`.

## Status

**Phase 1 — foundation (in progress).** Repository skeleton and Docker Compose baseline. Login, library and chat arrive in Phase 2.

## Layout

```
AeroVault/
├─ backend/            FastAPI service (Python 3.11)
│  ├─ app/             config.py, main.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/           React + Vite + TypeScript + Tailwind
│  ├─ src/
│  ├─ Dockerfile
│  └─ package.json
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
# edit .env and set AEROVAULT_OPENAI_API_KEY
docker compose up --build
```

- UI: http://127.0.0.1:5173
- API health: http://127.0.0.1:8000/api/health

Both ports are bound to `127.0.0.1` only; nothing is exposed to the network.

## Project documents

| File | Purpose |
|------|---------|
| `Project_Documents/1_Project_Plan.md` | Plan, gates and milestones |
| `Project_Documents/2_Step_Log.md` | Step-by-step history and decisions |
| `Project_Documents/3_Inspection_Report.md` | Gate 0 library inspection (PASSED 2026-11-13) |
| `Project_Documents/4_Naming_Convention.md` | Library naming rules |
| `Project_Documents/5_Wireframes.md` | UI wireframes |
| `Project_Documents/6_Retrieval_Benchmark.md` | 25-question retrieval benchmark |
| `Project_Documents/7_Architecture_Decisions.md` | Architecture decision record (Gate 1) |
