# 6 — Retrieval Benchmark (Draft)

**Version:** 0.1
**Date:** 2026-11-13
**Status:** Question set drafted; expected documents and pages to be confirmed after indexing

---

## 1. Purpose

Measure whether the retrieval layer finds the right passage for real aviation-safety questions. This benchmark is the evidence for **Gate 2** (success criterion S1: correct passage in the top-5 results for at least 80% of questions).

## 2. Method

- 25 questions: 22 answerable from the three collections, 3 deliberately unanswerable (to test the "not found in library" behaviour).
- For each answerable question, record the expected document and page after the index is built. The page is confirmed manually by opening the cited passage.
- Run each question three times with the production retrieval settings; record the rank of the first correct passage (1–5, or "miss").
- Metrics: top-1 accuracy, top-5 recall, mean reciprocal rank (MRR), false-answer rate on unanswerable questions, median latency.
- Pass criterion: top-5 recall ≥ 80% (≥ 18 of 22 answerable questions), no hallucinated answer on the 3 unanswerable questions.

## 3. Question set

| # | Question | Expected collection | Expected document (confirm) | Expected page (confirm) | Notes |
|---|----------|--------------------|-----------------------------|-------------------------|-------|
| 1 | What are the four levels of HFACS? | Aviation HF and Risk Mgmt | Book HFACS A Human Error Approach... | | Human factors taxonomy |
| 2 | What is the difference between an error and a violation in Reason's model? | Aviation HF and Risk Mgmt | Book Human Error by James Reason | | Error classification |
| 3 | Explain the Swiss cheese model of accident causation. | Aviation HF and Risk Mgmt | Book Human Error by James Reason | | Classic model |
| 4 | What is a bow-tie analysis and what are its main elements? | Aviation HF and Risk Mgmt | Book Bow Ties in Risk Management | | Risk method |
| 5 | Define hazard, risk and safety in an aviation risk-management context. | Aviation HF and Risk Mgmt | Book Aviation Risk and Safety Management | | Core definitions |
| 6 | How does a 5×5 risk matrix score severity and likelihood? | Aviation HF and Risk Mgmt | Aviation risk/safety book | | Risk assessment |
| 7 | What does ALARP mean and how is it applied? | Aviation HF and Risk Mgmt | Risk management book | | Risk acceptance |
| 8 | Describe the SHEL model of human factors. | Aviation HF and Risk Mgmt | Human factors handbook | | Human factors |
| 9 | What is situational awareness and how does it degrade? | Aviation HF and Risk Mgmt | Human factors handbook | | Human performance |
| 10 | What are the key components of a safety management system? | Aviation HF and Risk Mgmt | Aviation risk/safety book | | SMS |
| 11 | What is a just culture? | Aviation HF and Risk Mgmt | Dekker / Reason | | Safety culture |
| 12 | Explain the difference between active and latent failures. | Aviation HF and Risk Mgmt | Book Human Error by James Reason | | Accident theory |
| 13 | What are the main organisational factors in accident theories? | Aviation HF and Risk Mgmt | Accident Theories and Organisational Factors | | Accident theory |
| 14 | What is a system safety assessment? | Aviation HF and Risk Mgmt | Book An Overview of System Safety Assessment | | System safety |
| 15 | Describe the V-model and its role in ARP4754A development. | Aviation HF and Risk Mgmt | Book Aviation Development Ecosystem DO-178C, ARP4754A, DO-254 | | Certification |
| 16 | What is DO-178C and what does it cover? | Aviation HF and Risk Mgmt | Book Aviation Development Ecosystem DO-178C, ARP4754A, DO-254 | | Software assurance |
| 17 | Explain FMEA and FMECA. | Aviation HF and Risk Mgmt | Book Hazard Analysis Techniques for System Safety | | Hazard analysis |
| 18 | What is HAZOP and when is it used? | Aviation HF and Risk Mgmt | Book Guidelines for Hazard Evaluation Procedures | | Hazard analysis |
| 19 | What is the purpose of AS9100? | Quality ISO SAE | 9100 auditor guidance / standard | | Aerospace quality |
| 20 | What are the main audit requirements of AS9100? | Quality ISO SAE | 9100_auditor_guidance_material.pdf | | Quality audit |
| 21 | What is RobustQMS and what does it cover? | Quality ISO SAE | 0_RobustQMS_Guidance... | | Quality guidance |
| 22 | What is the difference between safety and quality management? | Quality ISO SAE / HF | Quality or safety book | | Cross-domain |
| 23 | What is the maximum take-off weight of the Airbus A350-900? | — | Not expected in the three collections | — | Unanswerable test |
| 24 | What are the UAE GCAA requirements for drone registration? | — | Not expected in the three collections | — | Unanswerable test |
| 25 | What is the current price of aviation fuel in Dubai? | — | Not expected in the three collections | — | Unanswerable test |

## 4. Recording template

| Run | Question # | Rank of first correct passage | Cited document | Page | Latency (s) | Notes |
|-----|-----------|-------------------------------|----------------|------|-------------|-------|
| 1 | 1 | | | | | |
| 1 | 2 | | | | | |

Store the full results in `AeroVault\.work\inspection\benchmark_results.csv`.

## 5. Failure analysis

For every miss, record the cause:

- **Parsing failure:** text missing or garbled (scanned page not OCR'd).
- **Chunking failure:** passage split across chunks.
- **Embedding failure:** semantically similar content outranked the target.
- **Query ambiguity:** the question does not uniquely identify the passage.
- **Index gap:** the document is not in the index.

Each cause maps to a specific fix (re-OCR, change chunk size, add reranker, rewrite question, add document).

## 6. Schedule

1. Build the index for the three collections (Phase 2).
2. Fill expected documents and pages (manual verification, ~2 hours).
3. Run the benchmark three times.
4. Review failures and tune retrieval.
5. Re-run; present results at Gate 2.
