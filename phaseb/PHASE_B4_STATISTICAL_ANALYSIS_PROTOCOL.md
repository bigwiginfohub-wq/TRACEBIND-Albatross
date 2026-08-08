\# PHASE B4: Statistical Analysis Protocol



\*\*Version:\*\* 1.0  

\*\*Status:\*\* DRAFT (Pending Freeze)  

\*\*Predecessor:\*\* Phase B3 (Descriptor Extraction)  

\*\*Successor:\*\* Phase B5 (Manuscript Preparation / Reporting)



\---



\## 1. Objective

To perform a strictly preregistered statistical comparison using the frozen B3 descriptors and prespecified case labels of the $C\_\\phi$ descriptor between the 150 Tropical Cyclone (TC) cases and the 150 non-cyclonic Control cases. This phase tests the primary TRACEBIND hypothesis regarding the discriminative power of the tangential velocity alignment metric.



\---



\## 2. Input Artifacts \& Contract

The sole scientific inputs for this phase are the frozen B3 artifacts:

\* \*\*Filename:\*\* `b3\_descriptors.csv`

\* \*\*SHA256:\*\* `eb16205e233c3eb3d35de2e1e17c934bfd4ecb767dae6148d1b0f3f70e708ded`

\* \*\*Required Columns:\*\* `case\_id`, `case\_type`, `case\_timestamp`, `C\_phi`, `shell\_grid\_count`, `QC\_Status`

\* \*\*Filter:\*\* Analysis is strictly restricted to rows where `QC\_Status == "PASSED"`.



\---



\## 3. Sampling Design \& Independence

The 150 TC cases and 150 Control cases were selected as independent cohorts. There is no one-to-one matching or pairing between individual TCs and Controls. Therefore, all primary inferential tests are explicitly designed for \*\*independent samples\*\*.



\---



\## 4. Hypotheses

\* \*\*Primary Null Hypothesis ($H\_0$):\*\* The distribution of $C\_\\phi$ for TC cases is identical to the distribution of $C\_\\phi$ for Control cases.

\* \*\*Primary Alternative Hypothesis ($H\_1$):\*\* The distributions of $C\_\\phi$ for TC and Control cases differ.

\* \*\*Directional Scientific Expectation:\*\* The TRACEBIND hypothesis predicts higher tangential alignment in TC cases. Therefore, a positive effect size and an AUC > 0.5 would be directionally consistent with the hypothesis, though the primary statistical test remains two-sided.



\---



\## 5. Preregistered Statistical Tests

The following tests shall be executed in this exact order. All tests are two-sided with a significance level of $\\alpha = 0.05$.



1\. \*\*Descriptive Statistics:\*\* Report mean, standard deviation, median, and interquartile range (IQR) of $C\_\\phi$ for both TC and Control groups separately.

2\. \*\*Primary Inferential Test:\*\* Two-sided Mann–Whitney U test. (Note: Shapiro-Wilk may be computed as an optional diagnostic, but it shall \*\*not\*\* be used to select or alter the primary test).

3\. \*\*Primary Effect Size:\*\* Cliff's delta ($\\delta$), representing the probability that a randomly selected TC $C\_\\phi$ is greater than a Control $C\_\\phi$, minus the reverse probability.

4\. \*\*Sensitivity Analysis:\*\* Welch's two-sample t-test (to assess robustness to distributional assumptions).

5\. \*\*Sensitivity Effect Size:\*\* Hedges' $g$ (with small-sample bias correction).

6\. \*\*Discriminative Power:\*\* Receiver Operating Characteristic (ROC) curve analysis.

&#x20;  \* \*\*Class Definition:\*\* TC is the positive class.

&#x20;  \* \*\*Direction:\*\* Higher $C\_\\phi$ is the predicted TC direction.

&#x20;  \* \*\*Bootstrap Procedure:\*\* 2,000 bootstrap replicates. Resampling is performed \*within each class independently\*. The AUC is calculated for each replicate. The 95% confidence interval is reported using the percentile method.

&#x20;  \* \*\*Reproducibility:\*\* A fixed random seed of 43 shall be used for all bootstrap resampling. The seed value shall be recorded in `b4\_audit.json`.



\*Kolmogorov–Smirnov tests and unplanned subgroup analyses (e.g., by basin or month) are explicitly excluded from this protocol to prevent multiple-comparison penalties.\*



### 5.1 Mann–Whitney U Implementation
The primary Mann–Whitney U test shall use the asymptotic two-sided p-value with the implementation specified by the frozen analysis engine (SciPy `scipy.stats.mannwhitneyu` with `alternative="two-sided"` and `method="asymptotic"`). The implementation settings and software versions shall be recorded in the audit manifest. No alternative exact, permutation, or continuity-corrected Mann–Whitney result shall replace the preregistered primary result.



\---



\## 6. Strict Analysis Constraints

\*\*CRITICAL:\*\* The B4 engine shall execute the entire preregistered analysis automatically from the frozen B3 artifact and shall write all prespecified results to machine-readable output files. No analyst-controlled branching, data dredging, p-hacking, or post-hoc subgroup analysis based on observed results is permitted. The script shall not require or allow manual intervention during execution.



\---



\## 7. Output Schema

The script shall generate the following artifacts:

1\. \*\*`b4\_statistical\_results.json`\*\*: A machine-readable file containing:

&#x20;  \* Descriptive statistics (mean, SD, median, IQR) for both groups.

&#x20;  \* Mann-Whitney U test statistic, p-value, and Cliff's delta.

&#x20;  \* Welch t-test statistic, p-value, and Hedges' $g$.

&#x20;  \* ROC AUC and its bootstrap 95% percentile CI.

2\. \*\*`b4\_audit.json`\*\*: Cryptographic manifest containing:

&#x20;  \* SHA256 of `b3\_descriptors.csv`.

&#x20;  \* SHA256 of the B4 analysis script.

&#x20;  \* Git commit hash.

&#x20;  \* Execution timestamp.

&#x20;  \* Bootstrap random seed (exactly 43).

3\. \*\*`b4\_visualizations/`\*\*: A directory containing publication-ready figures:

&#x20;  \* \*\*Distribution Plot:\*\* Empirical Cumulative Distribution Function (ECDF) or violin/boxplot with jittered observations (avoiding primary reliance on KDE to prevent bandwidth artifacts).

&#x20;  \* \*\*ROC Curve:\*\* Plot showing the curve, AUC value, and 95% CI bounds.



\---



\## 8. Freeze Criteria

This protocol is considered frozen when:

1\. This document is committed to Git with a `v1.0-phase-b4-protocol` tag.

2\. The analysis script is written to strictly adhere to these rules without deviation.

3\. The script is executed, and the audit manifest confirms successful generation of all output artifacts.

