# 2 — Step Log: AeroVault

Chronological record of actions, decisions, results and next steps. Updated at every milestone and gate.

## Log

| ID | Date | Phase | Action | Result | Next step |
|----|------|-------|--------|--------|-----------|
| S-001 | 2026-11-13 | Initiation | Owner requested options for consulting a local aviation library with an LLM as a daily work tool. | Four routes presented: desktop RAG app, self-hosted platform, purpose-built app, cloud notebooks. | Owner decision |
| S-002 | 2026-11-13 | Initiation | Checked authorized execution devices. | Device Martinolli-1 online; only two workspaces authorized (`flight-test-interactive-analysis-suite`, `Notebook_Google`). | Owner to grant library folder |
| S-003 | 2026-11-13 | Initiation | Owner provided three library paths and confirmed read access, edits/renames, cloud downloads, no confidentiality constraints, prototype first. | Direction confirmed: purpose-built app (Route 3), password-protected, prototype-first. | Draft plan and step log |
| S-004 | 2026-11-13 | P0 — Discovery | Drafted `1_Project_Plan.md` v0.1 and step log (sandbox working copy). | Plan with goals, success criteria, architecture, roadmap, gates, risks and open decisions. | Owner review |
| S-005 | 2026-11-13 | P0 — Discovery | Owner confirmed: name **AeroVault**, project folder accepted, OpenAI API key available, Docker installed, localhost-only, English, GitHub allowed. | Plan updated to v0.2; decisions register updated. | Folder access |
| S-006 | 2026-11-13 | P0 — Discovery | Owner granted access to `...\DOCUMENTOS REVISION`; Manus switched to Martinolli-1. | Library root readable; project folder created at `DOCUMENTOS REVISION\AeroVault` (the separate Projects path is outside the grant and was denied). | Inventory |
| S-007 | 2026-11-13 | P0 — Discovery | Ran PowerShell inventory over the three collections. | 755 files, 639 PDFs, 10,292.1 MB. Aircraft Theory 304 PDFs/7.9 GB; Aviation HF 242 PDFs/2.17 GB; Quality ISO SAE 209 files/195 MB. | Duplicate and structure analysis |
| S-008 | 2026-11-13 | P0 — Discovery | Analyzed duplicates, subfolders and filename patterns. | 127 duplicate-style `(n)` files, 117 with matching originals, ~1.08 GB; Quality ISO SAE has 3 subfolders; naming inconsistent. | Parsing probe |
| S-009 | 2026-11-13 | P0 — Discovery | Attempted PDF probe with pypdf. | All sampled PDFs are OneDrive cloud-only placeholders; the restricted session cannot hydrate them (`OSError 22`). Probe invalid. | Owner to hydrate folders |
| S-010 | 2026-11-13 | P0 — Discovery | Wrote `3_Inspection_Report.md` v0.1 (preliminary). | Inventory and duplicate findings recorded; Gate 0 blocked pending hydration. | Hydration; rerun probe |
| S-011 | 2026-11-13 | P0 — Discovery | Owner confirmed: keep necessary files on device, approve duplicate sanitization, prefer project folder in user profile root, proceed with parallel preparation, GitHub after Phase 1 with review. | Disk free 245.9 GB; root folder write denied by the restricted session; dedupe script and naming convention draft prepared. | Owner to pin folders and grant project workspace |
| S-012 | 2026-11-13 | P0 — Discovery | Received handoff documents (plan v0.3, wireframes, benchmark) into `Project_Documents`. | Six planning documents now local. | Probe results analysis |
| S-013 | 2026-11-13 | P0 — Discovery | Verified hydration: 638/639 PDFs local; 1 placeholder (`Introduction to Aerospace Engineering.pdf`, re-pinned). | Hydration effectively complete. | Re-probe failed files |
| S-014 | 2026-11-13 | P0 — Discovery | Re-probed the 366 files that failed during hydration; decrypted `DO-160F (senha mk3ja5).pdf` with its embedded password (460 pp). | 630/639 PDFs parsed; 210,502 pages detected; 570 full text layer, 7 partial, 53 OCR-needed (20,221 pp); 9 exceptions left (6 AES, 2 password-locked bowties, 1 placeholder). | Duplicate sanitization |
| S-015 | 2026-11-13 | P0 — Discovery | Ran dedupe dry run (SHA-256) after fixing a base-name substitution bug. | 117 pairs checked; 117 exact duplicates; 0 different content; 10 unmatched `(n)` files. | Owner-approved quarantine |
| S-016 | 2026-11-13 | P0 — Discovery | Applied quarantine (`dedupe.py --apply`). | 117 duplicate files (1,019.5 MB) moved to `AeroVault\_QUARANTINE\DUPLICATES`; nothing deleted. | Gate 0 report |
| S-017 | 2026-11-13 | P0 — Discovery | Published `3_Inspection_Report.md` v1.0 with final Gate 0 findings and six owner questions (OCR scope, bowties password, quarantine retention, DO-160F rename, project location). | Gate 0 recommended PASS, pending owner sign-off. | Owner Gate 0 review |
| S-018 | 2026-11-13 | Gate 0 → P1 | Owner accepted Gate 0 and all recommendations (Q1–Q5 yes; keep project folder as is). DO-160F renamed to `DO-160F.pdf`. | **Gate 0 PASSED.** Phase 1 authorized. | Phase 1 foundation |
| S-019 | 2026-11-13 | P1 — Foundation | Created repository skeleton: FastAPI backend (health endpoint, settings), React/Vite/TS/Tailwind frontend, Docker Compose baseline with localhost-only ports, README, `.env.example`, `.gitignore`; wrote `7_Architecture_Decisions.md` (D-023–D-030). | `py_compile` OK. Local git repo initialized; initial commit `ff92d82` (26 files) with Manus co-author trailer; `safe.directory` exception added (folder owner SID differs from session account). | Gate 1 owner review |
| S-020 | 2026-11-13 | Gate 1 → P2 | Owner approved the architecture (D-023–D-030) and all recommended answers. Device access was revoked mid-review and re-authorized by the owner. | **Gate 1 PASSED.** Decisions D-031–D-037 recorded. Phase 2 (ingestion MVP) authorized. | Build ingestion pipeline |
| S-021 | 2026-11-13 | P2 — Ingestion MVP | Built ingestion pipeline: scanner (SHA-256 incremental), PyMuPDF/pypdf extraction, Tesseract OCR hook, page-aware chunker, SQLite pages/chunks + FTS5 triggers, LiteLLM/HTTP embeddings, LanceDB vectors, CLI (`scan`/`ingest`/`status`). | Scan of the real library: 522 PDFs (639 − 117 quarantined), 0 unreadable. Local smoke test: 3 Quality docs extracted and chunked (9 chunks), FTS query returns ranked snippets. Commit `ffaeb1b`. | Retrieval + benchmark |
| S-022 | 2026-11-13 | P2 — Ingestion MVP | Created private GitHub repo `github.com/Martinolli/AeroVault` and pushed `main` (Gate 1 approval, D-037). | Repo live; origin tracking `main`. | Retrieval layer |
| S-023 | 2026-11-13 | P2 — Ingestion MVP | Built hybrid retrieval (FTS5 BM25 + LanceDB vectors, RRF merge) and benchmark runner (parses the 25-question benchmark, writes top-5 CSV, scores against `benchmark_expected.csv`). | Local BM25 smoke test OK. Commit pending push. | Owner runs Docker ingestion + benchmark |

## Gate status

| Gate | Phase | Status | Date passed |
|------|-------|--------|-------------|
| Gate 0 | Discovery and inspection | **PASSED** — owner sign-off (parsing 630/639, 210,502 pp; duplicates quarantined) | 2026-11-13 |
| Gate 1 | Foundation and design | **PASSED** — architecture and UX approved; skeleton committed (`ff92d82`) | 2026-11-13 |
| Gate 2 | Ingestion MVP | Code complete — awaiting owner run (ingestion + benchmark) | — |
| Gate 3 | App MVP | Not started | — |
| Gate 4 | Workflows and export | Not started | — |
| Gate 5 | Hardening and handover | Not started | — |

## Decisions register

| ID | Decision | Status | Date |
|----|----------|--------|------|
| D-001 | Build a purpose-built web app (Route 3), not an off-the-shelf tool | Confirmed by owner | 2026-11-13 |
| D-002 | Password-protected access | Confirmed by owner | 2026-11-13 |
| D-003 | Prototype on three initial collections; expand later | Confirmed by owner | 2026-11-13 |
| D-004 | Project plan with gates, milestones and history | Confirmed by owner | 2026-11-13 |
| D-005 | Application name: AeroVault | Confirmed by owner (delegated choice) | 2026-11-13 |
| D-006 | Project folder: `...\J_B_Martinolli\Projects\AviationLibraryAssistant` | Confirmed by owner, but not writable by the restricted session; provisional working location `DOCUMENTOS REVISION\AeroVault` | 2026-11-13 |
| D-007 | LLM: OpenAI API, dedicated project key | Confirmed by owner | 2026-11-13 |
| D-008 | Deployment: Docker Desktop | Confirmed by owner | 2026-11-13 |
| D-009 | Localhost-only prototype access | Confirmed by owner | 2026-11-13 |
| D-010 | English interface and answers | Confirmed by owner | 2026-11-13 |
| D-011 | GitHub repository for version control | Confirmed by owner | 2026-11-13 |
| D-012 | Hydrate the three collections locally ("Always keep on this device"); 245.9 GB free | Confirmed by owner (direction) | 2026-11-13 |
| D-013 | Duplicate sanitization via SHA-256 verification and quarantine (no deletion) | Approved by owner | 2026-11-13 |
| D-014 | Preferred project location: user profile root `C:\Users\Aspire5 15 i7 4G2050\AeroVault`; pending workspace grant | Owner preference | 2026-11-13 |
| D-015 | Parallel preparation (naming convention, wireframes, benchmark) while files hydrate | Approved by owner | 2026-11-13 |
| D-016 | GitHub repository after Phase 1; owner reviews before push | Confirmed by owner | 2026-11-13 |
| D-017 | Duplicate quarantine applied: 117 exact duplicates (1,019.5 MB) moved to `_QUARANTINE\DUPLICATES` | Executed under D-013 approval | 2026-11-13 |
| D-018 | OCR scope: all 53 scanned documents as background job after first index; Aviation HF + System Safety priority | Approved by owner | 2026-11-13 |
| D-019 | `bowties_online_contents_reduce_size` PDFs remain unindexed until owner provides password | Approved by owner | 2026-11-13 |
| D-020 | Quarantine retained 30 days, then archived to ZIP outside the library | Approved by owner | 2026-11-13 |
| D-021 | Rename `DO-160F (senha mk3ja5).pdf` → `DO-160F.pdf` | Approved and executed | 2026-11-13 |
| D-022 | Project location: keep `DOCUMENTOS REVISION\AeroVault`; revisit before release | Approved by owner | 2026-11-13 |
| D-031 | Architecture D-023–D-030 approved (monorepo, FastAPI, React/Vite/TS/Tailwind, SQLite + LanceDB, LiteLLM, Argon2id sessions, localhost-only compose, local git) | Approved by owner | 2026-11-13 |
| D-032 | UI style: light "aviation chart" default; dark mode later | Approved by owner | 2026-11-13 |
| D-033 | Ports: 5173 (UI) / 8000 (API) in development; single 8080 at release | Approved by owner | 2026-11-13 |
| D-034 | Default chat model `gpt-4o-mini` with per-query switch to a stronger reasoning model | Approved by owner | 2026-11-13 |
| D-035 | Searchable question/answer history kept by default, with per-item delete | Approved by owner | 2026-11-13 |
| D-036 | Embeddings `text-embedding-3-small` first; benchmark decides if `-large` is needed | Approved by owner | 2026-11-13 |
| D-037 | GitHub: create private repo `AeroVault` and push after Gate 1 approval | Approved by owner | 2026-11-13 |
