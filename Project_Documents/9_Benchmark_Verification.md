# 9 - Benchmark Expected Pages (Verified)

**Date:** 2026-11-14  |  **Status:** verified against indexed text; Gate 2 run complete

Each expected passage was checked against the indexed chunk text. Three expectations were corrected from the original benchmark hints: Q3 (the Swiss cheese model is explained in *Maintenance Resource Management* p.16, not in Reason's *Human Error*), Q16 (DO-178C overview at p.106 rather than the DO-278A comparison at p.190), and Q18 (HAZOP in the scenario-based chapter at p.118).

| # | Question | Expected document | Page |
|---|----------|-------------------|------|
| 1 | Four levels of HFACS | Book HFACS A Human Error Approach... | 67 |
| 2 | Error vs violation (Reason) | Book Human Error by James Reason | 249 |
| 3 | Swiss cheese model | Book Maintenance Resource Management... | 16 |
| 4 | Bow-tie analysis | Book Bow Ties in Risk Management | 40 |
| 5 | Hazard, risk, safety definitions | Book Aviation Risk and Safety Management | 24 |
| 6 | 5x5 risk matrix | Book Safety Management Systems in Aviation | 155 |
| 7 | ALARP | Book Quality-I Is Safety-II | 89 |
| 8 | SHEL model | Book HFACS A Human Error Approach... | 44 |
| 9 | Situational awareness | Book Controlled Flight Into Terrain | 126 |
| 10 | SMS components | Book Aviation Risk and Safety Management | 62 |
| 11 | Just culture | Book Just Culture | 14 |
| 12 | Active vs latent failures | Book Human Error by James Reason | 223 |
| 13 | Organisational factors | Accident Theories and Organisational Factors | 23 |
| 14 | System safety assessment | Book An Overview of System Safety Assessment | 1 |
| 15 | V-model / ARP4754A | Book Aviation Development Ecosystem | 74 |
| 16 | DO-178C | Book Aviation Development Ecosystem | 106 |
| 17 | FMEA / FMECA | Book Hazard Analysis Techniques for System Safety | 246 |
| 18 | HAZOP | Book Guidelines for Hazard Evaluation Procedures | 118 |
| 19 | Purpose of AS9100 | SAE AS9100D | 5 |
| 20 | AS9100 audit requirements | 9100_auditor_guidance_material | 3 |
| 21 | RobustQMS | 0_RobustQMS_Guidance_top_20150414_eng | 1 |
| 22 | Safety vs quality management | Book Quality-I Is Safety-II | 130 |

## Gate 2 result (2026-11-14)

- 25 questions, 22 answerable, 3 unanswerable.
- **Top-1 accuracy 45.5%, top-5 recall 54.5% (12/22), MRR 0.49**, median latency 1.86 s.
- Gate 2 target is top-5 >= 80%, so **Gate 2 is not passed**.
- Misses are mostly document-level: named sources such as Reason, HFACS, RobustQMS, 9100 auditor guidance and the system-safety overview are not surfaced in the top-5 for their questions. Page-level misses are secondary.
- Planned fix: LLM-based query expansion and reranking of the top 20 candidates before answering (ADR D-054); this is a retrieval-quality task, not an indexing gap (all expected documents are indexed).

The final expected file is `data/benchmark_expected.csv`; the scored run is `data/benchmark_results_gate2.csv`.
