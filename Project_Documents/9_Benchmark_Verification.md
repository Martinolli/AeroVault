# 9 - Benchmark Expected Pages (Draft for owner spot-check)

**Date:** 2026-11-14  |  **Status:** draft awaiting owner confirmation

Proposed expected document and page for each answerable benchmark question. `hint match` = the document named in the benchmark appeared in the hybrid top-5; `hint doc (page auto)` = the hinted document was used but the page was located by keyword search; `verify` = the hint was vague, so the top-ranked passage is proposed. Please correct any row, then save as `benchmark_expected.csv` and tell me to run the scored Gate 2 benchmark.

| # | Question | Proposed document | Page | Status | Snippet |
|---|----------|-------------------|------|--------|---------|
| 1 | What are the four levels of HFACS? | Book HFACS A Human Error Approach to Aviation Accident  | 68 | hint doc (page auto) | The Human Factors Analysis and Classification System 51 outcome. Not surprising, given the fact that humans by their very nature m |
| 2 | Difference between an error and a violation in Reason's model? | Book Human Error by James Reason | 249 | hint match | An important lesson to be learned from both the Chernobyl and Zeebrugge disasters is that the term ‘error’ does not capture all th |
| 3 | Explain the Swiss cheese model of accident causation. | Book Human Error by James Reason | 223 | hint doc (page auto) | 7 Latent errors and systems disasters In considering the human contribution to systems disasters, it is important to distinguish t |
| 4 | What is a bow-tie analysis and its main elements? | Book Bow Ties in Risk Management | 40 | hint match | 6 BOW TIES IN RISK MANAGEMENT Assumptions are frequently made, based on the visual structure of the representation, that bow ties  |
| 5 | Define hazard, risk and safety in aviation risk management. | Book Aviation Risk and Safety Management Methods and Ap | 102 | hint doc (page auto) | organizational decisions, whereby the strategy from the group differs from the one management has imposed.12 10.2 The Notion of Ri |
| 6 | How does a 5x5 risk matrix score severity and likelihood? | Book Safety Management System in Aviation | 155 | verify | Safety Management Systems in Aviation 130 Deﬁnitions Let’s begin our journey with deﬁnitions—always a good place to start. You wil |
| 7 | What does ALARP mean and how is it applied? | Book Quality-I Is Safety-ll The Integration of Two Mana | 89 | verify | 72 Quality-I Is Safety-II This is extremely safe but very impractical. Absolute safety means no haz- ards or at least all hazards  |
| 8 | Describe the SHEL model of human factors. | Book HFACS A Human Error Approach to Aviation Accident  | 44 | verify | Human Error Perspectives 27 working conditions that we as humans (liveware – symbolized by the letter L) are faced with. Edwards,  |
| 9 | What is situational awareness and how does it degrade? | Book Controlled Flight Into Terrain | 126 | verify | Summary In this chapter we have seen how lost situational aware- ness can result in CFIT or CFTT. Two concepts seem to be precurso |
| 10 | What are the key components of a safety management system? | Book Aviation Risk and Safety Management Methods and Ap | 162 | hint match | 14.2 Phase: Risk Collection and Assessment In Phase II the focus is to correct potential deﬁciencies within the system and to work |
| 11 | What is a just culture? | Book Just culture restoring trust and accountability in | 14 | verify | xiii Preface who disclose their mistakes. Unreflectively or arbitrarily punitive regimes destroy the opportunity to report safety  |
| 12 | Explain the difference between active and latent failures. | Book Human Error by James Reason | 223 | hint doc (page auto) | 7 Latent errors and systems disasters In considering the human contribution to systems disasters, it is important to distinguish t |
| 13 | What are the main organisational factors in accident theories? | Accident Theories and Organisational Factors | 23 | hint match | making leading to potential catastrophic incident. In this framework, explanation of serious accidents focuses on structural facto |
| 14 | What is a system safety assessment? | Book An Overview of System Safety Assessment | 1 | hint doc (page auto) | Chapter 2 An Overview of System Safety Assessment Abstract This chapter provides an introduction to the steps involved in creating |
| 15 | Describe the V-model and its role in ARP4754A. | Book Aviation Development Ecosystem DO-178C, ARP4754A,  | 74 | hint match | to evolve over time. Thus they are developed by different persons via different disciplines often separated by space and time; the |
| 16 | What is DO-178C and what does it cover? | Book Aviation Development Ecosystem DO-178C, ARP4754A,  | 190 | hint match | Differences between DO-278A and DO-178C. The first major difference with DO-278A is its emphasis upon, and allowance for, COTS sys |
| 17 | Explain FMEA and FMECA. | Book Hazard Analysis Techniques for System Safety | 246 | hint match | Chapter13 Failure Mode and Effects Analysis 13.1 INTRODUCTION Failure mode and effects analysis (FMEA) is a tool for evaluating th |
| 18 | What is HAZOP and when is it used? | Book Guidelines for Hazard Evaluation Procedures (2) | 90 | hint doc (page auto) | Non=Scenario-Based Hazard Evaluation Procedures The purpose of the next two chapters is to discuss eleven commonly used hazard eva |
| 19 | What is the purpose of AS9100? | 9100_auditor_guidance_material | 2 | hint doc (page auto) | Dated: 26 September 2011 Page 2/22 9100 Auditor Guidance Material Introduction This document provides general guidance and potenti |
| 20 | What are the main audit requirements of AS9100? | 9100_auditor_guidance_material | 3 | hint doc (page auto) | 9101 Auditor Guidance Material – Dated: 26 September 2011 Page 3/22 Process Auditing Approach When auditing each process identifie |
| 21 | What is RobustQMS and what does it cover? | 0_RobustQMS_Guidance_top_20150414_eng | 1 | hint doc (page auto) | 1 About the Guidance Documents for Construction of Robust Quality Management Systems (QMS) for the Aviation, Space and Defense Org |
| 22 | Difference between safety and quality management? | Book Quality-I Is Safety-ll The Integration of Two Mana | 130 | hint match | 113 The Natural Connection between Quality and Safety As mentioned previously, the main difference between QMS and SMS was in risk |

## Open items for verification

**Q3.** Hint names Reason's Human Error, but the phrase 'Swiss cheese' is retrieved from HFACS and commercial_aviation_safety. Reason may not contain the exact phrase - verify the expected document.

| Rank | Document | Page |
|---|---|---|
| 1 | commercial_aviation_safety | 64 |
| 2 | Book Safety-Assessment-Techniques-Database_1.2_3-Nov-2020 | 212 |
| 3 | Safety Methods Database 2016 | 205 |

**Q10.** Hint is vague ('Aviation risk/safety book'); the expected page 162 is in Aviation Risk and Safety Management, but the SMS book also covers this. Verify the page.

| Rank | Document | Page |
|---|---|---|
| 1 | Book Aircraft system safety Military and civil aeronautical | 211 |
| 2 | Book Aircraft system safety Military and civil aeronautical | 211 |
| 3 | Book Aircraft system safety Military and civil aeronautical | 215 |

**Q14.** Hint document 'An Overview of System Safety Assessment' was used with an auto page; verify p.1.

| Rank | Document | Page |
|---|---|---|
| 1 | Book Aircraft system safety Military and civil aeronautical | 127 |
| 2 | Book Aircraft system safety Military and civil aeronautical | 127 |
| 3 | Book Aircraft system safety Military and civil aeronautical | 125 |

**Q18.** Hint document 'Guidelines for Hazard Evaluation Procedures' was used with an auto page; verify p.90 (HAZOP chapter).

| Rank | Document | Page |
|---|---|---|
| 1 | Book Risk Assessment Theory, Methods, and Applications(1) | 311 |
| 2 | Book Guidelines for Process Hazards Analysis (PHA, HAZOP) | 10 |
| 3 | Book Guidelines for Process Hazards Analysis (PHA, HAZOP) | 109 |

**Q19.** Hint says '9100 auditor guidance / standard'; the top hits are the SAE AS9100D standard (p.51) and the AS9100 white paper, not 9100_auditor_guidance_material. Verify which document is authoritative.

| Rank | Document | Page |
|---|---|---|
| 1 | AS9100_White_Paper_Process_Approach | 1 |
| 2 | AS9100_White_Paper_Process_Approach | 3 |
| 3 | 2016_aug_progress | 1 |

**Q20.** Hint document 9100_auditor_guidance_material was used with an auto page; verify p.3.

| Rank | Document | Page |
|---|---|---|
| 1 | AS9100_White_Paper_Process_Approach | 1 |
| 2 | AS9100_White_Paper_Process_Approach | 3 |
| 3 | SAE AS9100D | 39 |

**Q21.** Hint document 0_RobustQMS_Guidance was used with an auto page; verify p.1.

| Rank | Document | Page |
|---|---|---|
| 1 | Book System Safety for the 21st Century The Updated and Revi | 219 |
| 2 | Book Quality-I Is Safety-ll The Integration of Two Managemen | 62 |
| 3 | Book Aviation Development Ecosystem DO-178C, ARP4754A, DO-25 | 147 |


## Provisional score (draft expected pages)

Run on 2026-11-14 with hybrid retrieval: top-1 50%, top-5 recall 59% (13/22), MRR 0.52. **Gate 2 target is 80%**, so this draft is not yet a pass; page numbers and a few document choices need confirmation before the result is meaningful.
