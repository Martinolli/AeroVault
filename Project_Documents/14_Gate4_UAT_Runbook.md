# 14 — Gate 4 UAT Runbook (Five Scenarios)

**Date:** 2026-11-15  
**Owner:** J. B. Martinolli  
**App:** http://127.0.0.1:5273  
**Purpose:** Execute the Gate 4 owner acceptance test for the compliance workspace and record pass/fail evidence.

---

## 1. Before starting

1. Confirm the backend health endpoint returns `status: ok`:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:18000/api/health
   ```

2. Open **http://127.0.0.1:5273** and sign in.
3. Click **Compliance** in the left navigation.
4. Use **`gpt-4o-mini`** for all five scenarios to control cost and latency.
5. Use the supplied non-sensitive test files, or substitute a real procedure if you prefer:
   - `outputs/UAT_5_Test_Procedure.docx` — 11 detected clauses; use for Scenarios 1 and 4.
   - `outputs/UAT_5_Test_Procedure.pdf` — 2 pages, text PDF; use for Scenario 3.
6. Do not delete a run from **History** until you have recorded its result; history is metadata-only and deletion is permanent.

The test procedure deliberately contains gaps: no calibration due date, no training record, no verification owner, no closure evidence, no revision control and no records backup/retrieval control.

---

## 2. Scenario map

| # | Scenario | Input | Mode | Authority | Standard selection |
|---|---|---|---|---|---|
| 1 | Uploaded procedure problem analysis | `UAT_5_Test_Procedure.docx` | Analyse a problem | FAA | None (authority search) |
| 2 | Indexed-document problem analysis | Indexed `AC_120-92D` | Analyse a problem | FAA | None (authority search) |
| 3 | Improvement review with PDF input | `UAT_5_Test_Procedure.pdf` | Improvement review | FAA | None |
| 4 | Clause-level gap review | `UAT_5_Test_Procedure.docx` | Gap / coverage review | Not used | `SAE AS9100D` |
| 5 | Negative / no-evidence guardrail | Indexed `AC_120-92D` | Analyse a problem | FAA | None |

---

## 3. Scenario 1 — Uploaded procedure, problem analysis

### Steps

1. In **Compliance**, leave **Upload PDF / DOCX** selected.
2. Under **Procedure or document**, choose `UAT_5_Test_Procedure.docx`.
3. Leave **OCR scanned pages** unchecked.
4. Click **Use this document**.
5. Select **Analyse a problem**.
6. Paste this brief into **Problem or improvement brief**:

   > During an assembly-line audit, three torque records were missing for a completed batch. The procedure says to re-torque and create a new record, but does not define who verifies closure or how the batch is released. Analyse the problem against FAA SMS expectations; identify contributing factors, risk and corrective actions.

7. In **Source scope**, select **FAA**. Leave the document list unselected.
8. Leave **Additional instructions** empty.
9. Click **Problem-driven analysis**.

### Expected result

- The result header says `UAT_5_Test_Procedure.docx · Problem-driven analysis`.
- **Problem understanding**, **Applicable requirements**, **Gaps, conflicts and contributing factors**, **Corrective actions and verification**, and **Page citations** are populated.
- Requirements cite FAA documents such as `AC_120-92D`, `AC_21-58` or `14_CFR_Part_5`; the uploaded procedure is **not** cited as the applicable standard.
- The gaps include missing closure ownership/evidence and weak training/change-control records.
- At least two corrective actions have an owner, priority and verification method.
- Clicking **Open p.N** opens the cited document at the correct page.
- No citation is presented as valid when the UI says **Page not verified**.
- **Export DOCX** and **Export XLSX** both download and open.
- XLSX contains the sheets **Problem analysis**, **Requirements**, **Findings**, **Actions** and **Citations**.

### Pass criteria

- [ ] Narrative is complete and readable.
- [ ] At least two FAA requirements are cited.
- [ ] Uploaded procedure is not used as a standards source.
- [ ] Citation page opens correctly.
- [ ] Both exports open.
- [ ] No invented clause or page number.

---

## 4. Scenario 2 — Indexed library document, problem analysis

### Steps

1. Click **New analysis** (or **Start over**) to return to the input screen.
2. Select **Indexed library document**.
3. In **Search the indexed library**, type `AC_120-92D`.
4. Select the result `AC_120-92D` (`FAA · 148 pp · indexed`).
5. Select **Analyse a problem**.
6. Paste this brief:

   > An operator's SMS procedure requires corrective actions after a hazard report, but does not clearly define who verifies effectiveness or what evidence closes the action. Assess the applicable FAA SMS requirements and recommend specific, proportionate corrective actions.

7. In **Source scope**, select **FAA**. Leave the document list unselected so the authority filter searches the FAA collection.
8. Click **Problem-driven analysis**.

### Expected result

- The result header identifies `AC_120-92D · Problem-driven analysis`.
- Citations come from other FAA sources, such as `AC_21-58`, `14_CFR_Part_5`, `14_CFR_Part_121` or `14_CFR_Part_135`; the source document itself is excluded.
- The narrative identifies corrective-action ownership, effectiveness verification and closure evidence.
- The **Page citations** panel shows real page numbers from the FAA documents.
- No self-citation to `AC_120-92D` appears as an applicable standard.

### Pass criteria

- [ ] Indexed document opens without re-upload.
- [ ] Source document is excluded from standards retrieval.
- [ ] At least two FAA citations have valid pages.
- [ ] At least one gap and one corrective action are evidence-backed.
- [ ] **Export DOCX** or **Export XLSX** works from the indexed-document path.

---

## 5. Scenario 3 — Improvement review with PDF input

### Steps

1. Click **New analysis**.
2. Select **Upload PDF / DOCX**.
3. Choose `UAT_5_Test_Procedure.pdf`.
4. Leave **OCR scanned pages** unchecked (the PDF has a text layer).
5. Click **Use this document**.
6. Select **Improvement review**.
7. Paste this brief:

   > Review this draft torque-record procedure for weaknesses and practical improvements. Focus on record completeness, correction of missing records, training evidence, change control and closure verification. Do not force a compliance matrix.

8. In **Source scope**, select **FAA**. Leave documents unselected.
9. Click **Improvement review**.

### Expected result

- The result is a narrative, **not** a clause-by-clause compliance matrix.
- Findings cover at least: calibration evidence, missing-record correction, training records, change control and closure verification.
- Actions are practical and proportionate; each has an owner, priority and verification.
- Citations are FAA sources with valid pages.
- **Export DOCX** and **Export XLSX** work; XLSX uses the problem/improvement sheet structure.

### Pass criteria

- [ ] PDF text is extracted without OCR.
- [ ] No forced matrix appears.
- [ ] At least three improvement findings are specific to the supplied procedure.
- [ ] At least two citations open correctly.
- [ ] Both exports open.

---

## 6. Scenario 4 — Clause-level gap review

### Steps

1. Click **New analysis**.
2. Select **Upload PDF / DOCX** and choose `UAT_5_Test_Procedure.docx`.
3. Leave OCR off; click **Use this document**.
4. Select **Gap / coverage review**.
5. In **Standard(s) for this request**, search `SAE AS9100D` and select `SAE AS9100D` (`Quality ISO SAE · 54 pp · indexed`).
6. Leave the detected clauses as they are. The test document should show about 11 clauses.
7. Optional: enter `Risk rating` in the first **Extra columns** field.
8. Click **Gap / coverage review**.

### Expected result

- A **Compliance matrix** appears with one row per clause and statuses such as `Compliant`, `Partial`, `Gap`, `Not applicable` or `Unclear`.
- The matrix should identify at least these weak areas:
  - `4.3` torque record content versus AS9100D documented-information requirements.
  - `4.5` missing/illegible record handling versus nonconforming-output control.
  - `6` training without records versus competence/training evidence.
  - `7` vague closure versus corrective-action effectiveness.
  - `8` shift-handover change communication versus documented-information control.
- **Standard / page** contains a clickable **Open p.N** link for populated rows.
- The run does not exceed 60 clauses.
- **Export DOCX** and **Export XLSX** open; XLSX contains the **Compliance matrix** sheet.

### Pass criteria

- [ ] Matrix is produced.
- [ ] At least one `Partial` or `Gap` is correctly tied to the test procedure.
- [ ] Standard page link opens.
- [ ] Optional extra column appears if entered.
- [ ] Both exports open.

---

## 7. Scenario 5 — Negative / no-evidence guardrail

### Steps

1. Click **New analysis**.
2. Select **Indexed library document** and search `AC_120-92D`.
3. Select `AC_120-92D`.
4. Select **Analyse a problem**.
5. Paste this brief:

   > Using only the indexed library, what is the approved calibration interval and acceptance limit for the fictional ZX-99 torque analyzer? Give the exact FAA or EASA clause and page. If the library does not contain this information, say so explicitly.

6. In **Source scope**, select **FAA**. Leave documents unselected.
7. Click **Problem-driven analysis**.

### Expected result

- The answer states that the library does not contain the requested ZX-99 calibration interval or acceptance limit.
- **Limitations** explicitly says the evidence is insufficient.
- The model does **not** invent a ZX-99 interval, acceptance limit, clause or page.
- Citations are empty or limited to genuinely relevant general passages; no citation is presented as the ZX-99 requirement.
- If the model invents a specific answer, the scenario fails even if the rest of the narrative looks plausible.

### Pass criteria

- [ ] The missing evidence is stated explicitly.
- [ ] No invented ZX-99 specification.
- [ ] No invented FAA/EASA clause or page.
- [ ] The result remains useful without pretending to know.

---

## 8. History and retention check

1. Click **History (N)** at the top of the Compliance workspace.
2. Confirm the five runs appear with file name, date, mode, model, status and source count.
3. Confirm the history does **not** show the problem brief, procedure text, clauses or generated answer.
4. Delete one history item and confirm it disappears.
5. Do not expect an expired run's full text to reopen; in-memory run text expires after two hours, while metadata remains for 90 days.

### Pass criteria

- [ ] History lists the runs.
- [ ] History is metadata-only.
- [ ] Delete works.
- [ ] No procedure text or answer is visible in history.

---

## 9. Recording the result

Use this table for the acceptance record:

| Scenario | Run ID | Pass/Fail | Evidence (screenshot / export) | Notes |
|---|---|---|---|---|
| 1 — Uploaded problem | | | | |
| 2 — Indexed problem | | | | |
| 3 — Improvement review | | | | |
| 4 — Gap review | | | | |
| 5 — No-evidence guardrail | | | | |
| History check | | | | |

**Gate 4 passes only when all five scenarios and the history check pass.** If a scenario fails, record the run ID, the exact question, the bad citation or export name, and a screenshot before deleting anything.

---

## 10. Known expected limitations

- eCFR Parts 5/91/121/135 are continuous text, so their citation page is **page 1**; the section number is the substantive reference until section-level mapping is added.
- The EASA XML archive is stored but not yet used for section-level citations.
- A **Page not verified** label is intentional when the quote cannot be matched to a page. It is not a valid page citation.
- Gate 2 remains open at **63.6% top-5 (14/22)**; it is separate from Gate 4 UAT.

---

## 11. UAT execution record — 2026-11-15

Owner executed the five scenarios and supplied the exports listed below. The content checks passed; one cross-cutting citation-viewer defect was found and fixed after the run.

| Scenario | Evidence | Observed result | Status |
|---|---|---|---|
| 1 — Uploaded DOCX problem | `UAT_5_Test_Procedure_analysis_Scenario_1.docx` | Full problem narrative; FAA requirement and AC 120-92D page citation; one unsupported quote correctly shown at page 0 with a limitation. | PASS |
| 2 — Indexed AC 120-92D problem | `AC_120-92D_analysis_Scenario_2.xlsx` | Five-sheet XLSX; citations from `AC_21-58` and `14_CFR_Part_5`, not from the source document; eCFR citations show page 1 as expected. | PASS |
| 3 — PDF improvement review | `UAT_5_Test_Procedure_analysis_Scenario_3.docx` | Narrative improvement review; weaknesses in closure, training and record control; AC 120-92D page citations; one unmatched requirement at page 0 with a limitation. | PASS |
| 4 — DOCX gap review vs AS9100D | `UAT_5_Test_Procedure_compliance_Scenario_4.docx` | 11 clauses analysed: 4 Compliant, 5 Gap, 2 Partial; AS9100D page citations and matrix. | PASS |
| 5 — ZX-99 no-evidence guardrail | `AC_120-92D_analysis_Scenario_5.docx` | Explicitly states the library does not contain the ZX-99 calibration interval or acceptance limit; no invented ZX-99 specification or clause; limitation stated. | PASS |
| History check | Owner report | Delete works; history behaves as metadata-only. | PASS (owner-reported) |

### Defect found

- **Symptom:** every citation link returned `Missing PDF "http://127.0.0.1:5273/api/documents/529/file"`.
- **Root cause:** `GET /api/documents/{id}/file` resolved paths only under `AEROVAULT_LIBRARY_ROOT`. FAA/EASA sources are stored under `data/regulatory_library`, so those files returned 404. One library record (`SAE AS9100D`) also had a stray newline in `rel_path`.
- **Fix:** resolve safely against both the main library root and `data/regulatory_library`; strip whitespace from stored paths; return the correct media type. The citation viewer now detects text-only sources and renders their indexed page text instead of asking PDF.js to parse a `.txt` file.
- **Verification:** `test_document_file.py` passes; `test_citation_validation.py` and `test_compliance.py` pass; backend rebuilt; health OK; live-mounted route returns 200 for `AC_120-92D` (PDF), `14_CFR_Part_5` (text), and `SAE AS9100D` (PDF).

### Gate 4 status

**PASSED — 2026-11-15.** After the viewer fix and a hard refresh, the owner retested:

- `AC_21-58` PDF citation — opened at the cited page.
- `14_CFR_Part_5` text citation — opened as a text-only source at page 1.
- `SAE AS9100D` PDF citation — opened at the cited page.

The owner also reran the two affected scenarios; all sources opened correctly. Gate 4 is closed.
