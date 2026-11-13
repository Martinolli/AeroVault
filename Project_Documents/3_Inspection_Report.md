# 3 — Inspection Report (Gate 0, Final)

**Version:** 1.0
**Date:** 2026-11-13
**Status:** **Gate 0 PASSED** — owner sign-off 2026-11-13
**Project:** AeroVault — Aviation Safety & Risk Library Assistant

---

## 1. Scope

Three initial collections under `C:\Users\Aspire5 15 i7 4G2050\OneDrive\Documentos\J_B_Martinolli\DOCUMENTOS REVISION`:

- `BOOKS\Aircraft Theory(1)`
- `BOOKS\Aviation Human Factors and Risk Management(1)`
- `QUALITY ISO SAE`

Access to the parent folder was granted by the owner on 2026-11-13. The project folder lives at `...\DOCUMENTOS REVISION\AeroVault` (working location; the preferred profile-root location `C:\Users\Aspire5 15 i7 4G2050\AeroVault` remains pending a workspace grant).

## 2. Executive summary

| Metric | Result |
|--------|--------|
| Files inventoried | 755 (639 PDFs + 116 other formats) |
| Total size | 10,292.1 MB (~10.3 GB) |
| PDFs parsed successfully | 630 of 639 (98.6%) |
| Total pages detected | **210,502 pages** |
| PDFs with full text layer | 570 |
| PDFs with partial text layer | 7 (2,363 pp) |
| PDFs with no text layer (OCR needed) | 53 (20,221 pp) |
| PDFs with remaining exceptions | 9 (see §6) |
| Exact duplicates quarantined | 117 files, 1,019.5 MB |
| Different-content `(n)` pairs | 0 |

**Gate 0 conclusion:** the library is well suited to text-based RAG. 89% of documents (by count) carry a usable text layer. The main processing load is OCR for 53 scanned documents — concentrated in Aircraft Theory (45 documents, 18,299 pages of classic engineering textbooks). Parsing quality is sufficient to proceed to Phase 1, with OCR planned as a background job in Phase 2.

## 3. Inventory summary

| Collection | Files | PDFs | Other formats | Total size | PDF pages | Subfolders |
|------------|------:|-----:|---------------|-----------:|----------:|------------|
| Aircraft Theory | 304 | 304 | — | 7,924.6 MB | 122,317 | None (all in root) |
| Aviation HF and Risk Mgmt | 242 | 242 | — | 2,172.6 MB | 80,382 | None (all in root) |
| Quality ISO SAE | 209 | 93 | DOCX 79, DOC 14, XLSX 13, XLS 1, PPTX 1, CSV 2, JPG 2, PNG 2, ZIP 2 | 194.9 MB | 7,803 | `AS9100_Template_Kit_v1.1` (43), `DOCUMENTS` (39), `CURSO GERENCIAL` (11), root (116) |
| **Total** | **755** | **639** | **116** | **10,292.1 MB** | **210,502** | |

Full file-level inventory: `AeroVault\.work\inspection\library_inventory.csv` (755 rows).
Full probe results: `AeroVault\.work\inspection\pdf_probe_local_results_v2.csv` (639 rows).

## 4. Hydration and storage state

The owner pinned all three folders ("Always keep on this device") on 2026-11-13. Hydration completed during the session:

- 638 of 639 PDFs are fully local and readable.
- 1 PDF remains a cloud placeholder: `Aircraft Theory(1)\Introduction to Aerospace Engineering.pdf` (31.1 MB). It was re-pinned; it will hydrate on its own or on first access by the application. Not a blocker.

The first probe pass ran while hydration was still in progress, which produced spurious `OSError 22` results for 366 files. After hydration, a re-probe of those files succeeded for all but the 9 exceptions in §6.

## 5. Parsing assessment

Detection method: pypdf 7.1.0, sampling 5 pages per document (first, second, third, middle, near-end); a document is classified **YES** when the sample averages ≥ 80 extracted characters per page, **PARTIAL** at 10–79, and **NO** below 10.

| Collection | YES | PARTIAL | NO (OCR) | Errors | Pages (all) |
|------------|----:|--------:|---------:|-------:|------------:|
| Aircraft Theory | 250 | 2 | 45 | 7 | 122,317 |
| Aviation HF and Risk Mgmt | 229 | 4 | 7 | 2 | 80,382 |
| Quality ISO SAE | 91 | 1 | 1 | 0 | 7,803 |
| **Total** | **570** | **7** | **53** | **9** | **210,502** |

**OCR workload (scanned documents):**

| Collection | Documents | Pages |
|------------|----------:|------:|
| Aircraft Theory | 45 | 18,299 |
| Aviation HF and Risk Mgmt | 7 | 1,903 |
| Quality ISO SAE | 1 | 19 |
| **Total** | **53** | **20,221** |

The scanned Aircraft Theory set consists mainly of classic structures/aeroelasticity/design textbooks (Bruhn, Bisplinghoff, Fung, Perkins, Roskam, Raymer, etc.). At a planning rate of 2–4 seconds per page on the target PC, full OCR is an estimated 11–22 hours of background processing — feasible overnight and in batches, but it should not block the first index.

**Partial text layer (7 documents, 2,363 pp):** `Book System Safety Engineering and Management, Second Edition` (371 pp), `modern_accident_investigation_analysis` (323 pp) — both also have quarantined copies — and `FAI First Article Inspection.pdf` (28 pp). These benefit from OCR fallback on pages whose extraction is empty.

## 6. Document exceptions (9 files)

| File | Issue | Handling |
|------|-------|----------|
| `Atmosphere of Freedom.pdf` | AES-encrypted, empty user password | Opens with any modern PDF engine (PyMuPDF/qpdf); pypdf probe lacked the `cryptography` package. Not a blocker. |
| `Book Aircraft Management Guidelines.pdf` | AES-encrypted, empty user password | Same as above. |
| `Empirical Method Prediction Airplane Drag Div Mach .pdf` | AES-encrypted, empty user password | Same as above. |
| `Preliminary_Design_Experimental_Spaceship_1.pdf` | AES-encrypted, empty user password | Same as above. |
| `Preliminary_Design_Experimental_Spaceship_2.pdf` | AES-encrypted, empty user password | Same as above. |
| `Preliminary_Design_Experimental_Spaceship_3.pdf` | AES-encrypted, empty user password | Same as above. |
| `Book bowties_online_contents_reduce_size.pdf` | Password-protected (user password required) | **Owner action:** provide the password, or the document stays unindexed. |
| `Book bowties_online_contents_reduce_size(1).pdf` | Password-protected — quarantined duplicate of the above | Follows the original. |
| `Introduction to Aerospace Engineering.pdf` | Still a OneDrive placeholder | Re-pinned; will be ingested when hydrated. |

**Successfully handled:** `DO-160F (senha mk3ja5).pdf` was decrypted using the password embedded in its filename (460 pp, full text layer). Renamed to `DO-160F.pdf` on 2026-11-13 with owner approval (D-021).

## 7. Duplicate sanitization (completed)

Method: SHA-256 verification of every `(n)`-suffixed file against its base-name original, same collection. Dry run followed by apply, as approved (decision D-013).

| Result | Count |
|--------|------:|
| Pairs checked | 117 |
| Exact duplicates (identical SHA-256) | **117** |
| Different content (kept in place) | 0 |
| Errors | 0 |
| Files moved to quarantine | **117** |
| Space reclaimed in working folders | **1,019.5 MB** |

Quarantine location: `AeroVault\_QUARANTINE\DUPLICATES\<collection>\...` — mirrors the collection structure. **Nothing was deleted.** The quarantine remains inside OneDrive and can be restored file-by-file.

**10 unmatched `(n)` files retained** (no base-name original exists, so they are treated as distinct documents):

- Aircraft Theory: `Book Aircraft Design Report (2).pdf`, `Book A_New_Twist_in_Flight_Research(1).pdf`
- Aviation HF: `Book Aircraft Accident Investigation(1).pdf`, `Book Guidelines for Hazard Evaluation Procedures (2).pdf`, `Book Risk Assessment Theory, Methods, and Applications(1).pdf`, `Book Systems Safety Scrapbook(1).pdf`, `evolution_system_safety(1).PDF`, `methods_accident_investigation(1).pdf`
- Quality ISO SAE: `Gidelines for Development of Civil Aircraft Systems ARP 4754 (2).pdf`, `sae_arp_4754a_guidelines_development_aircraft_systems (2)(1).pdf`

Note: the two ARP4754 entries appear to be the same standard under different names; content-level (cross-name) deduplication will be re-checked during ingestion using document fingerprints, without moving files.

## 8. Filename and naming observations

- 353 files start with `Book `; 579 contain spaces; 175 contain underscores; 79 base names are all lowercase; 6 contain non-ASCII characters; 2 base names exceed 120 characters.
- Mixed conventions (`Book X.pdf`, `book_x.pdf`, `BOOK X (z-library).pdf`) complicate display, duplicate detection and citation labels.
- Recommendation unchanged (`4_Naming_Convention.md`): Phase 1 applies safe normalization (trim, collapse spaces, fix case of extensions) only after a dry-run list is approved; metadata enrichment (title/edition/year) is stored in the database, not forced into filenames.

## 9. Tooling observations

| Tool | Status | Implication |
|------|--------|-------------|
| Tesseract OCR | Installed at `C:\Program Files\Tesseract-OCR` | OCR path available; will run inside the app's Docker image or natively |
| Docker | 29.6.2 installed; Docker Desktop running | Deployment target; containers started by the owner (Manus session lacks Docker pipe access) |
| Python (MSYS2) | 3.11.10; pypdf 7.1.0 in `.work\pylibs` | Adequate for inspection; the application will use its own containerized runtime |
| PyMuPDF | Wheel transferred; incompatible with MSYS2 Python | Not required for Gate 0; the Docker image will install it from PyPI |
| PowerShell | 5.1 | Inventory and file operations verified |

## 10. Gate 0 status

| Check | Status |
|-------|--------|
| File inventory | Complete — 755 files |
| Hydration | Complete — 638/639 local; 1 placeholder tracked |
| Text-layer / scanned detection | Complete — 570 YES / 7 PARTIAL / 53 NO |
| Page counts | Complete — 210,502 pages |
| Duplicate sanitization | Complete — 117 exact duplicates quarantined (1,019.5 MB) |
| Document exceptions | 9 identified; 6 auto-resolvable, 2 need owner password, 1 pending hydration |
| OCR assessment | Complete — 20,221 pages across 53 documents |
| Retrieval benchmark | Draft ready (`6_Retrieval_Benchmark.md`, 25 questions) |
| **Gate 0 decision** | **PASSED — owner sign-off 2026-11-13** |

## 11. Owner decisions (resolved 2026-11-13)

| # | Question | Decision |
|---|----------|----------|
| Q1 | Accept Gate 0 and start Phase 1? | **Accepted** — Phase 1 authorized |
| Q2 | OCR scope for the 53 scanned documents (20,221 pp) | **All**, as a background job after the first index; Aviation HF + System Safety prioritized (D-018) |
| Q3 | Password for the two `bowties_online_contents_reduce_size` files | Not provided — **stay unindexed** until available (D-019) |
| Q4 | Quarantine retention | **30 days**, then archive to ZIP outside the library (D-020) |
| Q5 | Rename `DO-160F (senha mk3ja5).pdf` → `DO-160F.pdf` | **Approved and executed** (D-021) |
| Q6 | Project location | **Keep** `DOCUMENTOS REVISION\AeroVault`; revisit before release (D-022) |

## 12. Notes and risks

- The 45 scanned Aircraft Theory textbooks are the dominant OCR cost. They are valuable (structures, aeroelasticity, design) but rarely queried daily; deferring them keeps the first index fast.
- Cross-name duplicates (e.g. ARP4754 under two names) will be detected at ingestion via text fingerprints; no file movement without approval.
- Copyright: private use only; no redistribution of book content; exports contain short quotes with citations.
- OneDrive: the source library remains read-only for the application; renames only through the approved workflow.
