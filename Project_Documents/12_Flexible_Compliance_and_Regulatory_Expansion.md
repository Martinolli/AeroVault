# 12 — Flexible Compliance Workflows and Regulatory Expansion Strategy

**Date:** 2026-11-15  |  **Status:** proposed — owner decisions needed  |  **Related:** D-066, D-068, W3, P-600-007 example

## 1. What you asked for

The current Compliance tab is a clause-by-clause checker: upload a procedure, choose one or more indexed standards, and compare each clause with a numbered requirement. That works for a quality procedure against AS9100D or ISO 9001, but it is too rigid for the two jobs you described.

The first job is a **document review against a framework**. Your P-600-007 draft is an Emergency Response Plan, not an SMS manual. You may want to compare it with the SMS framework, see which points are covered, and receive improvement actions for the uncovered or weak points. The tool should not declare the whole SMS framework "failed" simply because an ERP does not contain hazard identification or safety performance monitoring.

The second job is a **problem-driven review**. You have a procedure in use and a problem in the assembly line or operational area. You want to describe the problem, point to the applicable standard, and receive an analysis that connects the procedure, the problem, the requirement, and possible corrective actions.

You also want to expand the library with FAA and EASA material. That is a good next step, but it should be planned as a **regulatory library with versions and authority metadata**, not as another folder of PDFs dropped into the existing index.

## 2. Why the current MVP is too narrow

The current flow assumes four things that are not always true:

1. The input is a procedure with numbered clauses.
2. The reference is a standard with numbered clauses.
3. The useful output is a row per clause with a compliance status.
4. The document is expected to cover the whole reference.

An ERP breaks assumptions 1 and 4. A problem investigation breaks assumptions 2 and 3. A framework such as the ICAO SMS framework is organised as four components and twelve elements, not as a single numbered clause list. FAA advisory circulars and EASA AMC/GM mix regulation paragraphs, guidance, and acceptable means of compliance in the same document.

The fix is not to add many special cases. The fix is to separate **what is being reviewed**, **what it is being reviewed against**, and **what question the reviewer is asking**.

## 3. One engine, three review modes

I recommend keeping a single review engine and exposing three modes in the UI. The modes share upload, extraction, retrieval, citations, exports, and run handling. They differ in the input fields, the assessment schema, and the way the answer is synthesised.

### Mode A — Gap and coverage review

Use this when the question is: "What does this document cover, what is missing, and what should we improve?"

Inputs:

- A procedure, plan, manual, checklist, or work instruction (PDF or DOCX).
- One or more frameworks or standards, selected per request.
- Optional scope note, for example "this ERP covers flight operations, production, and maintenance at Al Ain."
- Optional document type: procedure, ERP, SMS manual, work instruction, audit checklist, or other.

Output:

- A row per framework element or requirement.
- Coverage status: addressed, partially addressed, not addressed, not applicable, or unclear.
- Evidence from the uploaded document: section, page, and a short quotation.
- Framework reference: element or clause, source document, page.
- Improvement action: specific, actionable wording, not a generic recommendation.
- Priority: high, medium, or low, with a short reason.
- Confidence: high, medium, or low.
- An "applicability" field that distinguishes a genuine gap from a requirement that is outside the document's purpose.

This last field is essential for P-600-007. An ERP should be assessed strongly against the emergency-response element, and only lightly against the other SMS elements. If you want an "SMS integration review," the tool should flag interfaces to the other elements rather than pretending the ERP is an SMS manual.

### Mode B — Problem and root-cause analysis

Use this when the question is: "We have this problem; does our procedure and the applicable standard support the right response, and what should we correct?"

Inputs:

- A procedure or work instruction (uploaded, or selected from the library if we allow that later).
- A problem brief: what happened, where, when, who was involved, what the immediate response was, and what is going wrong.
- One or more applicable standards or frameworks.
- Optional investigation lens: five whys, fishbone, HFACS, bow-tie, FMEA, HAZOP, or a simple causal map.

Output:

- A clear problem statement and observed condition.
- Contributing factors, separated into direct, contributing, and systemic factors where the evidence supports that distinction.
- Root-cause hypotheses, each with supporting evidence and a confidence level.
- Applicable requirements, with citations to the standard or framework.
- Procedure-to-requirement conflicts, omissions, or ambiguities.
- Risk description and severity/likelihood where the source material supports it.
- Corrective and preventive actions, with suggested owner and verification evidence.
- A short "what to check next" list when the evidence is insufficient.

This mode must be explicit that it is an analysis aid, not an accident investigation or a regulatory finding. The output should say when the uploaded procedure or the problem brief does not contain enough evidence.

### Mode C — Improvement review

Use this when there is no single applicable standard, or when the question is: "How can this document be made clearer, more complete, and more usable?"

Inputs:

- A document.
- Optional framework or best-practice reference.
- Optional focus areas: clarity, roles, interfaces, records, training, document control, or emergency response.

Output:

- Prioritised improvement list.
- The current text or section that creates the problem.
- Why it matters.
- Suggested replacement text or a concrete edit.
- Dependencies or related sections.

This mode is useful for draft documents such as P-600-007, where many issues are document-quality issues rather than compliance gaps.

### Shared custom instructions

Every mode should accept a short free-text instruction, for example "focus on interface with the SMS occurrence-reporting process" or "use a formal audit tone." The instruction should guide synthesis, not override the evidence rules. The tool should never invent a requirement or a citation to satisfy the instruction.

## 4. What the user sees

The UI should remain one workspace, not three separate applications.

1. **Intake.** Choose the mode. Upload a document or select a library document. Add the problem brief when using Mode B. Choose the document type and scope.
2. **Structure.** Show the extracted sections, clauses, headings, and tables. Let the user edit, merge, or delete items before running. OCR is opt-in, as agreed.
3. **References.** Search the library and select frameworks or standards. Show authority, version, effective date, and source page before selection. Allow more than one reference when the question genuinely needs a comparison.
4. **Options.** Choose the model, output depth, optional columns (up to three), and export format. The 60-item cap remains enough for the first version.
5. **Review.** Show progress per item, not just a spinner. Allow cancel. Show the matrix or narrative as soon as partial results are available.
6. **Results.** Provide a matrix view for Mode A and a narrative report for Mode B, with the same underlying evidence records. Every row or finding links back to the uploaded document and the reference.
7. **Export and history.** Export XLSX and DOCX. If approved, keep metadata-only run history for 90 days.

## 5. Data and backend changes

The existing `compliance.py` module can be extended rather than replaced. The main additions are:

- A `mode` field: `gap`, `problem`, or `improvement`.
- A `document_profile`: document type, scope, owner, revision, and any user-supplied context.
- A `problem_brief` object for Mode B.
- A `reference_set`: one or more framework packs or standards, each with authority, version, and effective date.
- A richer result schema: coverage status, applicability, evidence, requirement reference, gap, recommendation, priority, confidence, and optional extra columns.
- A framework-pack loader that reads curated element definitions instead of treating a whole PDF as an undifferentiated list of clauses.

Framework packs are the most important design decision. A pack should be a small, reviewable data file, not an automatic extraction of every paragraph in a regulation. Each entry should have:

- Framework ID, title, authority, version, and effective date.
- Element or clause ID, parent ID, and title.
- Requirement text or a faithful summary.
- Applicability note, for example "service providers required to maintain an ERP."
- Source document, page, and URL.
- Optional evidence prompts, for example "look for activation authority, notification chain, and recovery actions."

This makes the review reproducible. When a framework changes, we update the pack and keep the old version for history. It also lets us support ICAO's four-component/twelve-element SMS framework and a numbered quality standard with the same engine.

The retrieval step should combine the uploaded document and the library. The uploaded document is the primary evidence for Mode A and Mode B; the library supplies the reference text, definitions, and related guidance. Results must quote the uploaded document, not just paraphrase it.

## 6. Regulatory library expansion

### 6.1 Principles

Use official sources. Keep the authority, document number, revision, and effective date with every file. Preserve old versions instead of overwriting them. Do not mix regulatory documents with books in the same collection without metadata. Do not redistribute copyrighted material outside the owner's local installation.

The existing ingestion pipeline can handle PDFs and DOCX, but regulatory documents need a **source register** alongside the index. The register is a small CSV or SQLite table with one row per source document:

- Authority: GCAA, ICAO, FAA, EASA, SAE, ISO.
- Document type: regulation, annex, advisory circular, AMC/GM, manual, guidance, standard.
- Document ID and title.
- Revision, issue, amendment, and effective date.
- Applicability and scope.
- Official URL and local file path.
- SHA-256 and ingestion status.
- Access or licence note.
- Last checked date.

### 6.2 Priority order

I recommend expanding in tiers, not downloading everything at once.

**Tier 0 — FAA/EASA first (owner decision, 2026-11-15).** The owner wants FAA and EASA as the main sources because they are widely accepted international benchmarks. The first regulatory pack should therefore prioritise FAA regulations/advisory material and EASA regulations/AMC/GM. GCAA and ICAO remain secondary references: GCAA for the UAE operating context, ICAO for the international SMS framework and Annex 19.

**Tier 1 — SMS and emergency-response frameworks.** Add FAA 14 CFR Part 5 with AC 120-92D, EASA Part-ORO with the associated AMC/GM, and then ICAO Annex 19 / the ICAO Safety Management Manual framework. This tier directly supports P-600-007 and the first gap reviews. ICAO's public SMS framework page lists the four components and twelve elements, including the emergency-response element [1]. FAA AC 120-92D is active, dated 2024-05-21, and cancels AC 120-92B [2]. EASA's Easy Access Rules for Air Operations, Revision 24 (March 2026), are available as PDF and machine-readable XML [3].

**Tier 2 — airworthiness and quality.** Add FAA 14 CFR Parts 21, 23, 25, 43, 91, 121, 135, and 145, plus the relevant advisory circulars; add EASA Part-21, Part-M, Part-145, CS-23/25, and the operational parts that matter to Calidus. This is a larger collection and should be scoped by use case, not by authority.

**Tier 3 — guidance and change material.** Add AMC/GM, FAA orders, EASA guidance, and GCAA guidance documents. Keep these separate from binding regulations so the answer can distinguish "required" from "acceptable means of compliance" or "guidance."

### 6.3 Ingestion and retrieval changes

Create separate collections such as `Regulatory/GCAA`, `Regulatory/ICAO`, `Regulatory/FAA`, and `Regulatory/EASA`. Store authority and version metadata on each document and each chunk. Filter retrieval by authority, document type, and effective date when the user asks for a specific regulator.

Add a regulatory citation formatter so answers can say "FAA AC 120-92D, paragraph 3.2, p. 12" or "EASA Part-ORO, ORO.GEN.200(a)(3)" instead of a generic book title and page. For ICAO and EASA frameworks, preserve section and element IDs during chunking; a page number alone is not a useful citation for a framework element.

Add authority-aware query expansion. A query about "emergency response plan" should also retrieve "ERP," "emergency preparedness," "coordination of emergency response planning," and the relevant GCAA/EASA/FAA terms. This is a retrieval aid, not a substitute for the curated framework pack.

### 6.4 Version and change control

Regulations change. ICAO Annex 19 Amendment 2 was adopted in June 2025, became effective in November 2025, and is expected to apply in November 2026 [1]. EASA's Air OPS rules are already at Revision 24 in March 2026 [3]. The app should show the effective date next to every regulatory citation and warn when a selected document has a newer version in the register.

Run a monthly or quarterly source check. For each changed document, download the new version, record the new revision and effective date, keep the old version, re-index the new one, and ask the owner to approve the change before it becomes the default reference. Do not silently replace a standard in the middle of an audit cycle.

### 6.5 Licensing and access

FAA regulations and advisory circulars are U.S. government works and are generally public domain. EASA makes the Easy Access Rules available for free download, but the owner should confirm the applicable reuse terms before redistributing them. ICAO documents are copyrighted; the Safety Management Manual is available through ICAO eLibrary or ICAO-NET, and the owner may need an account or a purchased copy. GCAA publications are publicly downloadable from the GCAA e-publication site. The local app can store documents the owner is entitled to use; it should not become a redistribution service.

## 7. What a P-600-007 review would look like

P-600-007 is a useful test case because it is clearly an ERP, not an SMS manual. The inspected draft has 19 sections and 12 tables. It covers emergency categories, the activation decision matrix, the Emergency Response Centre, the core and support teams, initial response steps, role-specific checklists, post-event actions, training and drills, document control, flow charts, escalation tables, forms, contacts, and specific emergency procedures.

Against the ICAO SMS framework, a fair review would look roughly like this:

- **Strong coverage:** coordination of emergency response planning, roles and responsibilities, emergency activation, drills, contacts, and post-event debriefs.
- **Partial coverage:** SMS documentation, appointment of key safety personnel, training and education, and interfaces with occurrence reporting.
- **Not applicable to this document, but important as an interface:** safety policy and objectives, hazard identification, safety risk assessment and mitigation, safety performance monitoring, management of change, continuous improvement, and safety communication.

That distinction is the difference between a useful review and a misleading one. The report should say "this ERP does not contain the hazard-identification process; confirm that it is defined in the SMS manual and referenced here" rather than "the organisation fails hazard identification."

The improvement review should also catch document-quality issues that a compliance matrix would miss: the revision table still contains placeholder dates, there are typographical errors and inconsistent role names, the activation authority and escalation thresholds need to be unambiguous, the drill programme needs objectives and records, and the document-control section needs a clear owner, approval, review cycle, and distribution list. These are draft observations, not audit findings, and should be labelled as such.

## 8. Delivery sequence

**Step 1 — approve the product model.** The owner has confirmed FAA/EASA as primary sources, problem-driven analysis first, both uploaded and library documents, no fixed output template, and metadata-only history. The remaining choice is the first domain and the core-pack option.

**Step 2 — extend the compliance engine.** Add mode, document profile, problem brief, framework packs, applicability, and the richer result schema. Keep the current clause-level flow as Mode A rather than replacing it.

**Step 3 — build the first regulatory collection.** Start with the FAA/EASA core pack (Option A in `13_Regulatory_Source_Inventory.md`). Add the source register, authority metadata, regulatory citation formatter, and a small regulatory benchmark. Add ICAO and GCAA as secondary collections after the FAA/EASA pack is usable.

**Step 4 — run three UAT scenarios.** (1) P-600-007 against the SMS framework, (2) a real procedure plus a real problem brief against the applicable standard, and (3) a regulatory question that requires an FAA or EASA citation. Gate 4 is passed only when the owner can complete these without assistance and the citations are usable.

**Step 5 — expand by tier.** Add FAA/EASA operational and airworthiness material only after the first collection proves useful. Keep the source register and version checks in the loop.

## 9. Owner decisions and remaining questions

**Confirmed by the owner on 2026-11-15:**

1. **Primary sources:** FAA and EASA, because they are widely accepted internationally. GCAA and ICAO are secondary references.
2. **First mode:** problem-driven analysis. The ERP is an example of the type of request; the answer may be flexible according to the available library.
3. **Document inputs:** both uploaded documents and indexed library documents.
4. **Output:** no fixed model or formal report template is required; the analysis can follow the evidence and the owner's instruction.
5. **Run history:** metadata-only history approved (file name, date, mode, sources, model, status counts, 90-day retention, deletable, no procedure text).
6. **Source access:** the owner has an ICAO library and local FAA, EASA, AQAP, and NASA folders.

**Remaining decisions:**

1. **First domain:** certification/design (Part 21/23/25, CS-23/25), maintenance (Part 43/145, Part-M/CAMO), operations (Part 91/121/135, Part-ORO/CAT/NCO), or quality/defence (AS9100, AQAP)?
2. **Core pack:** approve Option A (focused FAA/EASA core pack), Option B (index everything), or Option C (owner-curated list) in `13_Regulatory_Source_Inventory.md`.
3. **Secondary sources:** should AQAP and NASA be indexed now, later, or kept out of the regulatory filter?
4. **Other authorities:** should CAA UK/Australia/Canada/New Zealand, MAA, MIL DoD, SMICG, and SCMH be included now or deferred?
5. **Missing official documents:** should I download missing FAA/EASA documents from official sources into a managed `Regulatory_Library` folder, or will you supply them?
6. **ICAO 4th edition:** do you have Doc 9859 4th edition in ICAO eLibrary/ICAO-NET, or should the app use the 3rd edition already in the folder and label it as older?

## References

[1]: https://www.icao.int/safety-management/SMI/SMM/Chapter%209 "ICAO Safety Management Manual, Chapter 9 — SMS framework"
[2]: https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1042733 "FAA AC 120-92D — Safety Management Systems for Aviation Service Providers"
[3]: https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations "EASA Easy Access Rules for Air Operations, Revision 24"
[4]: https://www.icao.int/safety-management "ICAO Safety Management — Annex 19 status"
[5]: https://www.gcaa.gov.ae/en/epublication/EPublications/Civil%20Aviation%20Regulations%20%28CARs%29/SAFETY%20MANAGEMENT%20SYSTEM%20%28SMS%29%20REGULATIONS/CAR-SMS%20-%20SAFETY%20MANAGEMENT%20SYSTEM%20-%20ISSUE%2006%20%28corrected%29.pdf "GCAA CAR-SMS Issue 06"
[6]: https://www.gcaa.gov.ae/en/epublication/EPublications/Civil%20Aviation%20Regulations%20%28CARs%29/CAR%20IV%20-%20FLIGHT%20OPERATIONS%20REGULATIONS/CAR%20AIR%20OPS/CAR-AIR%20OPS%20-%20PART-ORO%20-%20ISSUE%2001.pdf "GCAA CAR-AIR OPS Part-ORO Issue 01"
[7]: https://www.easa.europa.eu/en/document-library/acceptable-means-of-compliance-and-guidance-material-group/part-oro-organisation-requirements-air "EASA Part-ORO AMC and GM"
[8]: https://www.ecfr.gov/current/title-14/chapter-I/subchapter-A/part-5 "14 CFR Part 5 — Safety Management Systems"
