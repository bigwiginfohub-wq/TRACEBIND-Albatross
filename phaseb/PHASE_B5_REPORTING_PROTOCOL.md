\# PHASE B5: Reporting \& Interpretation Protocol



\*\*Version:\*\* 1.0  

\*\*Status:\*\* DRAFT (Pending Freeze)  

\*\*Predecessor:\*\* Phase B4 (Statistical Analysis)  

\*\*Successor:\*\* Manuscript Submission / Public Release



\---



\## 1. Objective

To translate the frozen, machine-readable outputs of Phase B4 into a human-readable scientific report or manuscript. This phase strictly governs the interpretation of the results, ensuring that claims are bounded by the actual statistical evidence and do not overstate the physical implications. Completion of B5 will establish a frozen, auditable reporting state for the B1–B4 computational pipeline.



\---



\## 2. Input Artifacts

The sole inputs for this phase are the frozen B4 outputs:

\* `b4\_statistical\_results.json`

\* `b4\_audit.json`

\* `b4\_visualizations/` (ECDF, Boxplot+Jitter, ROC Curve)



\*No new data analysis, subgroup stratification, or alternative statistical testing is permitted in this phase.\*



\---



\## 3. Permitted Claims (Claim Hierarchy)

The reporting may explicitly state the following, strictly adhering to this hierarchy of inference:



\* \*\*Level 1 — Directly Observed:\*\* "TC cases had higher observed mean $C\_\\phi$ values than Controls." (Reported means must exactly match the frozen JSON).

\* \*\*Level 2 — Statistical Inference:\*\* "The preregistered analysis detected a statistically significant distributional difference between the cohorts under the Mann-Whitney U test."

\* \*\*Level 3 — Classification Performance:\*\* "The $C\_\\phi$ descriptor showed limited-to-moderate discriminative ability, with an ROC AUC of 0.6871 (95% CI: 0.6250–0.7444)."

\* \*\*Level 4 — Physical Interpretation (Cautious):\*\* "The result is consistent with the expectation that TC cases exhibit greater tangential wind-direction alignment than non-cyclonic controls."



\---



\## 4. Forbidden Claims

To prevent overinterpretation, the reporting \*\*shall not\*\*:

1\. \*\*Claim Causality or Proof:\*\* State that these results "prove" the underlying physical hypothesis. Statistical separation does not equate to physical proof.

2\. \*\*Overstate Discrimination:\*\* Describe the AUC using categorical absolutes (e.g., "high," "excellent," or "near-perfect") detached from the actual numerical value and confidence interval.

3\. \*\*Conflate Significance with Magnitude:\*\* Use the highly significant p-value to imply that the \*effect size\* is massive. The p-value reflects sample size and consistency, not the absolute magnitude of the physical difference.

4\. \*\*Introduce Post-Hoc Narratives:\*\* Present any unplanned subgroup analyses as primary findings. If exploratory analyses are mentioned, they must be explicitly labeled as \*hypothesis-generating\* and subject to multiple-comparison caveats.

5\. \*\*Misrepresent the Descriptor:\*\* Describe $C\_\\phi$ as a measure of "tangential wind speed" or "intensity."



\---



\## 5. Required Discussion Elements



\### 5.1 Descriptor Interpretation

$C\_\\phi$ is a dimensionless directional-alignment statistic bounded between 0 and 1. It measures the absolute projection of the local horizontal wind direction onto the local tangential direction.

\* $C\_\\phi = 1$ corresponds to purely tangential alignment.

\* $C\_\\phi = 0$ corresponds to purely radial alignment.

\* Because the absolute value is applied, the descriptor does not distinguish the sign of tangential rotation; oppositely directed tangential flows contribute equally.



\### 5.2 Methodological Limitations

The report must explicitly address:

\* \*\*Substantial Overlap:\*\* The moderate AUC indicates substantial overlap between the TC and Control $C\_\\phi$ distributions, as visible in the ECDF/Boxplot.

\* \*\*Center Selection:\*\* For B3, the analysis center was fixed to the frozen requested coordinate rather than dynamically estimated from the pressure field. This choice was made a priori to maintain the same geometric rule across TC and Control cases and preserve blind descriptor extraction.



\### 5.3 Mechanistic Non-Inference

A statistically significant association between cohort membership and $C\_\\phi$ shall not be interpreted as evidence that the hypothesized physical mechanism generated the observed difference. Alternative explanations, including known meteorological structure, sampling design, spatial geometry, reanalysis characteristics, and residual confounding, must remain open unless independently tested.



\---



\## 6. Reproducibility Statement

The reported primary results shall be reproduced directly from the frozen B4 machine-readable outputs. Numerical values shall not be manually transcribed from intermediate console output.



Any reported numerical result must be traceable to:

1\. The frozen `b4\_statistical\_results.json`.

2\. The corresponding `b4\_audit.json`.

3\. The frozen B4 Git commit/tag.



If a discrepancy is discovered between the manuscript and the frozen machine-readable outputs, the manuscript shall be corrected rather than modifying the frozen statistical outputs.



\---



\## 7. Cryptographic Provenance

The reported B4 results are cryptographically linked through the frozen B2.2, B3, and B4 artifacts and their recorded hashes, commits, and audit manifests. This establishes artifact identity and computational lineage, not physical truth.



\---



\## 8. Freeze Criteria

This protocol is considered frozen when:

1\. This document is committed to Git with a `v1.0-phase-b5-protocol` tag.

2\. The final manuscript or report draft is reviewed against this protocol to ensure zero forbidden claims are present and all required discussion elements are included.

