# TRACEBIND Phase B2.1: Control Selection Protocol

**Status:** Frozen  
**Date:** 2026-08-04  
**Principal Investigator:** Mohammed Ali, Independent Researcher  

---

## 1. Objective & Firewall
To deterministically select exactly 150 non-cyclonic atmospheric control cases that match the geographic and temporal distribution of the frozen Phase B1 Tropical Cyclone (TC) cohort.

**FIREWALL CLAUSE:** No scientific descriptors, feature extraction, thresholding, ranking, or retrieval metrics shall be computed during Phase B2.1. This phase is strictly limited to cohort selection.

---

## 2. Selection Constraints

### 2.1 Geographic & Temporal Matching
* **Basin Balance:** Exactly 50 controls per basin (NI, SI, WP).
* **Calendar Month Matching:** The distribution of control months must exactly match the calendar month distribution of the 150 TCs selected in Phase B1.

### 2.2 Exclusion Zone (The "No-TC" Rule)
Every candidate control timestamp and coordinate must satisfy:
* **Spatial Separation:** Minimum 1000 km great-circle distance (computed via the Haversine formula) from *any* IBTrACS observation point belonging to any storm in the target analysis period (1980–present). Interpolation between track points is not used; only actual reported observation points are considered.
* **Temporal Separation:** Minimum ±7 days from *any* IBTrACS observation point in the target basins.

### 2.3 Candidate Pool Definition
* **Timestamp Resolution:** Candidates are restricted to ERA5 6-hourly analysis times (00:00, 06:00, 12:00, 18:00 UTC).
* **Location:** Must be located over open ocean within the ERA5 0.25° grid coverage for the target basins.

---

## 3. Algorithmic Selection & Randomization

1. **Candidate Generation:** Query the ERA5 temporal index for all valid 6-hourly timestamps within the target basins and required months.
2. **Filtering:** Apply the Exclusion Zone to remove all candidate points overlapping with known cyclone activity.
3. **Stratification:** Group remaining valid candidates by Basin and Calendar Month.
4. **Random Sampling:** 
   * Use `numpy.random.default_rng(seed=43)`.
   * Randomly sample the exact required number of controls per Basin/Month stratum.
5. **Deterministic Replacement:** If a selected control later fails B2.2 QC, it will be replaced by the next unused candidate from the pre-generated randomized list for that specific stratum.

---

## 4. Deliverables & Audit
* **`selected_control_ids.csv`**: Frozen list of 150 control coordinates and timestamps.
* **`control_randomized_order.csv`**: Full ranked list of candidates for deterministic replacement.
* **`control_candidate_filter_log.csv`**: Log of rejected candidates containing candidate ID, rejection reason, distance to nearest storm, nearest storm SID, and time difference.
* **`control_audit.json`**: Cryptographic manifest containing seed, software versions, input hashes, and stratum counts.

---
*This protocol constitutes the pre-registered specification for Phase B2.1. Any deviation requires a formal protocol amendment.*