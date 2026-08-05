\# TRACEBIND Phase B: Pre-Registration and Study Protocol



\*\*Status:\*\* Draft Protocol (To be frozen before data collection begins)  

\*\*Date:\*\* 2026-08-03  

\*\*Principal Investigator:\*\* Mohammed Ali, Independent Researcher  



\---



\## 1. Primary Objective

Phase A established that the TRACEBIND descriptor extraction and evaluation methodology is trustworthy, reproducible, and mathematically sound. The primary objective of Phase B is to determine whether the frozen TRACEBIND descriptor framework continues to produce statistically robust, physically meaningful retrievals on a balanced large-scale dataset, and to identify retrieval tasks for which physically interpretable descriptors provide advantages or limitations relative to conventional low-dimensional representations.



\## 2. Scientific Philosophy

Phase B is not intended to demonstrate the superiority of TRACEBIND over existing statistical methods. Instead, Phase B seeks to determine:

\* Where physically interpretable descriptors are sufficient.

\* Where compressed latent representations (e.g., PCA) are sufficient.

\* Where each representation succeeds, and where each representation fails.

\* Whether the additional interpretability provided by TRACEBIND offers scientific value beyond equivalent retrieval accuracy.



This study asks a fundamental methodological question: \*\*How should physically interpretable descriptor spaces be evaluated against statistical latent representations?\*\*



\---



\## 3. Frozen Components (Inherited from Phase A)

To ensure continuity and prevent methodological drift, the following components are \*\*strictly frozen\*\* and will not be modified during Phase B. Any modification to these will constitute "TRACEBIND Version 2" and require a separate, distinct study.



1\. \*\*Descriptor Definitions:\*\* The 12 physically motivated descriptors (Global Kinematics, Global Coherence, Local Coherence Statistics) remain exactly as defined in Phase A.

2\. \*\*Extraction Pipeline:\*\* The coordinate-aware derivative computation (fixing the descending grid vulnerability) and sliding window logic are frozen.

3\. \*\*Preprocessing:\*\* Standardization (zero mean, unit variance) is applied only at the representation stage, maintaining strict separation from physical feature extraction.

4\. \*\*Evaluation Protocol:\*\* Monte Carlo random baseline, permutation testing (1,000 iterations), and bootstrap confidence intervals (1,000 iterations, seed=42) remain unchanged.

5\. \*\*Statistical Metrics:\*\* Precision@K (K=1, 3, 5), macro-averaged Precision, and paired bootstrap difference testing.



\---



\## 4. Phased Execution Roadmap



\### Phase B0 — Infrastructure

\* Freeze dataset specification.

\* Freeze metadata schema.

\* Freeze quality-control rules and inclusion/exclusion criteria.

\* \*Deliverable:\* Protocol document (this file). No science yet.



\### Phase B1 — Dataset Construction

\* Acquire ERA5 data and IBTrACS metadata.

\* Verify every storm against predefined criteria.

\* \*Deliverable:\* Curated, balanced dataset of \~300 cases. No descriptor extraction yet.



\### Phase B2 — Descriptor Extraction

\* Run the frozen TRACEBIND pipeline on the full cohort.

\* \*Deliverable:\* Descriptor matrix outputs. Nothing else.



\### Phase B3 — Representation Analysis

\* Repeat every Phase A analysis (PCA, VIF, dimensionality ablation, ranking agreement) on the 300-storm dataset.

\* \*Goal:\* Determine if the low-dimensional structure and redundancy observed in Phase A generalize to a larger cohort.



\### Phase B4 — Scientific Retrieval

\* Evaluate retrieval performance across predefined physical targets: Basin, Intensity Category, Pressure, Lifecycle Stage (formation, RI, mature, decay), and Landfall.

\* \*Goal:\* Identify where physically structured targets reveal differences between representations.



\### Phase B5 — Interpretation

\* Synthesize results. Only after all analyses are frozen should interpretation begin regarding why TRACEBIND succeeds or fails on specific tasks.

\* \*Deliverable:\* Phase B Manuscript.



\---



\## 5. Hypotheses and Endpoints



\### 5.1 Primary Hypothesis (Confirmatory)

\* \*\*H1:\*\* TRACEBIND retrieval performance remains significantly above random chance across predefined physical targets on the balanced dataset.



\### 5.2 Secondary Hypotheses (Confirmatory)

\* \*\*H2:\*\* TRACEBIND and PCA may differ in performance depending on the specific retrieval task. Some tasks may favor one representation over the other.

\* \*\*H3:\*\* If performance differences emerge, they will be most apparent for physically structured targets that extend beyond coarse geographical similarity, such as lifecycle stage or rapid intensification.



\### 5.3 Exploratory Analyses (Hypothesis-Generating)

\* Unsupervised clustering of the descriptor space to identify distinct "storm families" or structural archetypes.

\* Analysis of descriptor drift or variance throughout the temporal lifecycle of individual storms.

\* Uncertainty quantification: Estimating the variance/confidence of descriptor values based on localized grid noise.



\---



\## 6. Pre-Planned Interpretive Pathways (Decision Tree)



To prevent post-hoc rationalization, the interpretation of Phase B results will follow this pre-registered decision tree:



1\. \*\*If TRACEBIND ≈ PCA (Replication of Phase A):\*\*

&#x20;  \* \*Action:\* Focus future work on interpretability, descriptor simplification, and the scientific value of physical transparency. Conclude that the descriptor space is highly redundant but physically meaningful.

2\. \*\*If TRACEBIND > PCA (Emergent Advantage):\*\*

&#x20;  \* \*Action:\* Investigate exactly which descriptors produce the gain. Analyze the specific physical targets (e.g., RI) where the advantage manifests.

3\. \*\*If PCA > TRACEBIND (Latent Advantage):\*\*

&#x20;  \* \*Action:\* Investigate missing physical descriptors. Conclude that the current frozen set lacks specific information captured by latent variance. Design "Version 2" in a future, separate study.

4\. \*\*If Both Fail (Target Failure):\*\*

&#x20;  \* \*Action:\* Revisit the retrieval target. Conclude that the specific physical phenomenon (e.g., eyewall replacement) is not captured by 10m wind fields, rather than modifying the frozen pipeline.



\---



\## 7. Conditions for "TRACEBIND Version 2"

The frozen 12-descriptor set will \*\*not\*\* be modified during Phase B. A "Version 2" framework will only be justified post-Phase B if:

1\. Phase B results demonstrate a consistent, statistically significant failure of the current descriptors to capture a specific, predefined physical phenomenon.

2\. A new, physically motivated descriptor is proposed to address this specific gap.

3\. The new descriptor undergoes its own dedicated, blinded pilot validation (a new "Phase A") before being integrated into the main framework.



\---



\## 8. Deliverables

1\. \*\*D1:\*\* Balanced, curated dataset of \~300 cases with verified metadata.

2\. \*\*D2:\*\* Frozen metadata enrichment script and final `metadata\_comprehensive.csv`.

3\. \*\*D3:\*\* Descriptor extraction outputs for the full cohort.

4\. \*\*D4:\*\* Multi-label retrieval evaluation reports (JSON and CSV).

5\. \*\*D5:\*\* Phase B Manuscript: "Operational Validation and Comparative Evaluation of the TRACEBIND Descriptor Framework on a Balanced Multi-Basin Cyclone Cohort."

6\. \*\*D6:\*\* Public release of the anonymized descriptor matrix and evaluation code.



\---

\*By committing this document to the repository, the investigator agrees to adhere strictly to this protocol. Any deviation will be explicitly documented and justified as exploratory.\*

