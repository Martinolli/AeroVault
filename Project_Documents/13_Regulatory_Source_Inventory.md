# 13 — Regulatory Source Inventory and Ingestion Options

**Date:** 2026-11-15  |  **Status:** inventory complete — Option A approved; fetcher implemented, core pack pending  |  **Related:** 12_Flexible_Compliance_and_Regulatory_Expansion.md

## 1. Summary

The source folders contain a useful seed collection, but they are not a complete FAA/EASA/ICAO regulatory library. The counts below cover the five folders named by the owner.

| Source | Files | PDF | DOC/DOCX | Other | Size | Main content |
|--------|------:|----:|---------:|------:|-----:|--------------|
| FAA | 528 | 467 | 37 | 24 | 3.13 GB | Part 23, AC 23, Part 36, maintenance handbooks, human-factors guides, selected SMS ACs |
| EASA | 155 | 131 | 21 | 3 | 0.39 GB | Basic Regulation, Part 21, CS-23, Part-145, CAMO, Easy Access Rules, AMC/GM |
| ICAO | 305 | 295 | 5 | 5 | 0.24 GB | 12th Air Navigation Conference papers, SMS folder, Annex 19 Rev 1, Doc 9760, SMM 1st–3rd editions |
| AQAP | 79 | 79 | 0 | 0 | 0.70 GB | AQAP quality publications, AGARD/STANAG material |
| NASA | 291 | 291 | 0 | 0 | 1.73 GB | NACA/NASA technical reports, not a regulatory standards collection |
| **Total** | **1,358** | **1,263** | **63** | **32** | **6.19 GB** | |

There are 11 duplicate-name groups in FAA and 2 in EASA. Some are version pairs, for example AC 120-92B and AC 120-92D, AQAP 2110 Ed 3 and Ed D, and several Part 23 amendment comparisons. These need version metadata, not blind deduplication.

## 2. What each folder actually contains

### FAA

The FAA folder is strongest on **Part 23 certification**, associated AC 23 guidance, maintenance handbooks, and aviation maintenance human factors. It includes useful SMS material: AC 120-92B and AC 120-92D, AC 21-58 (SMS for Part 21 production certificate holders), and AC 119-270. It does not appear to contain a complete set of 14 CFR Parts 21, 25, 43, 91, 121, 135, and 145. Those should be added from the official FAA/eCFR source if they matter to the first use cases.

### EASA

The EASA folder is stronger than the raw count suggests. It includes the Basic Regulation 2018/1139, Part 21 consolidated material, Easy Access Rules Part 21, CS-23 and CS-22 material, Part-145 AMC/GM, Part-CAMO, continuing-airworthiness guidance, and a set of conference presentations. It does not appear to contain a complete Part-ORO, Part-CAT, Part-NCO, or full AMC/GM set. Those should be added from EASA's official Easy Access Rules if the first use case needs them.

### ICAO

Most of the ICAO folder is **12th Air Navigation Conference papers**, which are useful context but not the core regulatory material. The `ICAO SMS` subfolder is the valuable part: Annex 19 Rev 1, Doc 9760 Airworthiness Manual, the 1st–3rd editions of Doc 9859, SMS handouts, and a commentary document. The 4th edition of Doc 9859 is not visible in the folder; the owner may have it in the ICAO eLibrary.

### AQAP

AQAP is a defence quality-assurance collection. It includes AQAP 2000, 2009, 2105, 2110, 2120, 2130, 2131, 2210, and 2310, plus AGARD and STANAG material. It is relevant as a secondary quality/defence framework, not as an FAA/EASA substitute.

### NASA

The NASA folder is a technical report collection: NACA/NASA reports on aerodynamics, aeroelasticity, flight dynamics, flutter, autorotation, and related subjects. It is not a regulatory source. It should be indexed as a technical reference collection if the owner wants it, but it should not appear in a "regulatory requirement" filter.

### Other relevant folders

The root also contains CAA UK (55 files), CAA Australia (47), CAA Canada (14), CAA New Zealand (11), MAA (181), MIL DoD (467), SMICG (33), and SCMH (44). These can become secondary authority collections later. They should not be mixed into the first FAA/EASA pack without a clear use case.

## 3. Recommended library structure

Keep the owner's original folders where they are. Do not move or rename them for this phase. Index them **in place** with a collection mapping, and create a separate managed folder for missing official downloads and new versions.

Recommended collections:

- `Regulatory/FAA`
- `Regulatory/EASA`
- `Regulatory/ICAO`
- `Regulatory/AQAP`
- `Regulatory/NASA-Technical`
- `Regulatory/Other-Authorities` (CAA, MAA, MIL DoD, SMICG, SCMH, later)

Each document gets a source-register row with authority, document type, document number, title, revision/issue, effective date, applicability, official URL, local path, SHA-256, access/licence note, and ingestion status. The app should show the authority and document type on every citation, so a FAA AC is not presented as a regulation and an EASA AMC is not presented as the rule itself.

## 4. Options for the first ingestion

### Option A — Focused FAA/EASA core pack (recommended)

Ingest a curated set of roughly 100–200 documents that directly supports problem-driven analysis:

- FAA: 14 CFR Parts 21, 23, 25, 43, 91, 121, 135, and 145; AC 120-92D; AC 21-58; AC 23.1309-1E; selected AC 20-xxx and maintenance/human-factors guidance.
- EASA: Basic Regulation 2018/1139; Part-21; Part-M; Part-145; Part-ORO; Part-CAT/NCO; CS-23/25; selected AMC/GM and Easy Access Rules.
- ICAO: Annex 19; Doc 9859 (latest available edition); Doc 9760; selected SMS guidance.
- AQAP: AQAP 2110, 2105, 2000, 2130/2131, 2310, only if the owner wants defence quality coverage.
- NASA: not part of the regulatory core; index later as technical reference.

This gives useful answers quickly, keeps retrieval noise low, and leaves room to expand.

### Option B — Index every file now

Index all 1,358 files (6.19 GB) in one pass. This is simpler operationally but produces duplicates, old versions, conference papers, and technical reports in the same retrieval pool. It also makes it harder to explain why a citation is authoritative. Not recommended for the first release.

### Option C — Owner-curated list

The owner provides a list of the documents that matter most. This is the most accurate but slowest option. It can be combined with Option A: start with the core pack, then add owner-selected files.

## 5. Version and authority rules

- Default to the latest effective version for new analyses.
- Keep superseded versions in the register and show them as "superseded" when cited.
- Do not silently replace a document in the middle of an audit or investigation.
- Mark each source as `regulation`, `standard`, `advisory-circular`, `AMC/GM`, `manual`, `guidance`, or `technical-report`.
- Mark jurisdiction and applicability; FAA and EASA material is widely used as a benchmark, but it is not automatically binding in every State.
- Use the official source URL and a local checksum; re-check versions monthly or quarterly.

## 6. Decisions needed

1. **First domain:** is the first problem-driven release for certification/design (Part 21/23/25, CS-23/25), maintenance (Part 43/145, Part-M/CAMO), operations (Part 91/121/135, Part-ORO/CAT/NCO), or quality/defence (AS9100, AQAP)?
2. **Core pack:** approve Option A, Option B, or Option C.
3. **Secondary sources:** should AQAP and NASA be indexed now, later, or kept out of the regulatory filter?
4. **Other authorities:** should CAA UK/Australia/Canada/New Zealand, MAA, MIL DoD, SMICG, and SCMH be included in the first phase or deferred?
5. **Official downloads:** do you want me to download missing FAA/EASA documents from official sources into a managed `Regulatory_Library` folder, or will you supply them?
6. **Version preference:** latest effective version by default, with old versions retained for reference — confirm.
7. **ICAO 4th edition:** do you have Doc 9859 4th edition available through ICAO eLibrary/ICAO-NET, or should the app use the 3rd edition already in the folder and label it as older?

## 7. Recommended next action

Option A was approved on 2026-11-15 with operations/SMS plus manufacturing quality as the first domain. The
problem-analysis mode, indexed-library input, authority scoping and metadata-only history are implemented. The
next action is to populate the core pack from official sources, record versions/checksums in the source register,
ingest deliberately, and run a real problem through the workflow before expanding the collection.

## 8. Implementation status (2026-11-15)

The controlled fetcher is `backend/app/ingest/regulatory.py`. The tracked template is
`regulatory_sources.json`; copy it to `data/regulatory_sources.json` before fetching so runtime status and
checksums stay out of the repository.
The manifest currently contains:

| Source | Form | Status |
|---|---|---|
| 14 CFR Parts 5, 91, 121, 135 | Official eCFR XML API, issue date 2026-11-12 | Part 5 downloaded/checksummed/indexed text-only; Parts 91/121/135 planned |
| AC 120-92D | Official FAA PDF | Planned |
| AC 21-58 | Official FAA PDF | Downloaded, checksummed and indexed text-only (62 pp; 1,114,657 bytes) |
| EASA Easy Access Rules for Air Operations Rev 24 | Official EASA landing page; PDF/XML links | Planned |

The fetcher accepts HTTPS only, records SHA-256, bytes, content type, fetch time and status, refuses to overwrite
unless `--force` is supplied, and writes eCFR `.txt` companions. It does not automatically index downloads. The
EASA landing page is used because direct PDF/XML links are generated on the official page and may change; add the
direct URL after downloading. EASA and ICAO material may be copyrighted and must not be redistributed.
