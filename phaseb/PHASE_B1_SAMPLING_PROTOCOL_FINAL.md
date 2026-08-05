# TRACEBIND Phase B1: Pre-Registered Sampling Specification & Algorithmic Quotas

**Status:** Frozen  
**Date:** 2026-08-03  
**Derived From:** Phase B0.75 Population Characterization  

---

## 1. Scientific Philosophy & Immutability Principle
**Stratified sampling is intentionally not representative of the natural cyclone population.** The objective is to maximize statistical power for descriptor evaluation across all intensity classes rather than to estimate climatological frequencies. 

**Immutability Principle:** Outputs from one stage become immutable inputs to the next stage. The eligible pool (`b075_eligible_tier1.csv`) generated in B0.75 is declared immutable once Phase B1 begins. No storms will be added, removed, or regenerated from the source data unless a formal protocol amendment is executed.

---

## 2. Algorithmic Sampling Rules (Tropical Cyclones)

### Rule A: Maximum Sampling Fraction
No single stratum shall contribute more than 40% of its total eligible population to the final cohort, unless the stratum contains fewer than 10 eligible storms.
* **Formula:** `Max_Sample = floor(Available_Pool * 0.40)`
* **Justification:** The maximum sampling fraction was selected to reduce variance inflation caused by sampling a large proportion of small strata while still preserving adequate statistical power.

### Rule B: Target Quota & Proportional Redistribution
The target quota per stratum is 17 (to reach N=150 across 9 strata). The final sample size is computed deterministically:

1. **Compute Provisional Sample:** For each stratum $i$, compute `sample_i = min(17, Max_Sample_i)`.
2. **Compute Basin Deficit:** For each basin, calculate `BasinDeficit = 50 − Σ(sample_i)`.
3. **Proportional Redistribution:** If `BasinDeficit > 0`, redistribute the deficit among the uncapped strata within that basin. The redistribution is strictly proportional to each uncapped stratum's **remaining available capacity** (`Available_Pool - sample_i`).
4. **Shortfall Handling:** If every stratum reaches the cap before `BasinDeficit = 0`, document the shortfall in `sampling_audit.json`.

### Rule C: Deterministic Replacement (No Manual Substitution)
If a selected storm later fails ERA5 QC (e.g., corrupted download, NaN values), it cannot be manually replaced. The replacement shall be the **next unused SID** from the fully randomized list within the exact same stratum.

---

## 3. Control Case Sampling Strategy (Target N = 150)

1. **Geographic Balance:** Exactly 50 controls per basin (NI, SI, WP).
2. **Temporal Matching:** Controls must be sampled from the same **Calendar Month** distribution as the selected TCs.
3. **Spatial Exclusion:** Control snapshots must not overlap with any IBTrACS storm track within a 1000 km radius and ±7 days.

---

## 4. Software & Reproducibility Lock

To guarantee bitwise reproducibility, the following exact computational environment is frozen:
* **Python:** 3.14.4
* **NumPy:** 2.4.6
* **Pandas:** 3.0.5* **Random Generator:** `numpy.random.default_rng(seed=42)`

---

## 5. Deliverables & Cryptographic Audit Trail

The execution of this protocol will generate four mandatory files:

1. **`randomized_order.csv`**: The complete, deterministic ranking of every eligible storm in the Tier 1 pool, grouped by stratum. This ensures replacements are strictly deterministic without re-running the RNG.
2. **`selected_cohort_ids.csv`**: The frozen list of the first 150 TC SIDs and 150 Control identifiers drawn from the randomized order.
3. **`excluded_strata_report.csv`**: A report listing `Available`, `Cap`, `Selected`, and `Reason for exclusion` for every stratum.
4. **`sampling_audit.json`**: A comprehensive audit trail containing:
   * Protocol Version & SHA-256 hash.
   * Git commit hash.
   * Random seed used.
   * Execution timestamp.
   * **Source Data Hash:** SHA-256 of the original `ibtracs_ALL.csv`.
   * **Input Data Hash:** SHA-256 of `b075_eligible_tier1.csv`.
   * **Output Data Hash:** SHA-256 of `selected_cohort_ids.csv`.
   * Eligible population counts and actual sampling fractions per stratum.
   * Exact software versions (Python, NumPy, Pandas).

---

## 6. Versioned Study Governance

This project adheres to a formal versioned study governance model. Each stage concludes with a freeze tag and a SHA-256 manifest.

* **B0:** Infrastructure
* **B0.5:** Population Census
* **B0.75:** Population Characterization
* **B1:** Cohort Selection (Current)
* **B2:** ERA5 Acquisition
* **B3:** Quality Control
* **B4:** Descriptor Extraction
* **B5:** Retrieval Evaluation
* **B6:** Statistical Analysis
* **B7:** Manuscript

---

## 7. Protocol Amendments

This protocol constitutes the pre-registered sampling specification for Phase B1. Amendments are strictly categorized:

### Major Amendment
Changes to descriptors, statistical tests, sampling rules, or primary hypotheses. Requires a new preregistration document and a new version number.

### Minor Amendment
Typographical corrections, logging adjustments, or documentation clarifications that do not affect the scientific outcome. Documented in the project log.

---
*By committing this document, the investigator agrees to execute the sampling exactly as defined.*