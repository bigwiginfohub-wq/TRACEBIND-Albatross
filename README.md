# TRACEBIND-Albatross

**Spatial Phase Coherence and Descriptor Framework for Atmospheric Flows**

![Status](https://img.shields.io/badge/Status-Phase_B5_Protocol_Frozen-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Reproducibility](https://img.shields.io/badge/Reproducibility-Cryptographically_Audited-orange)

---

## Overview

TRACEBIND-Albatross is a reproducible computational framework for evaluating spatial organization in atmospheric flow fields using explicitly defined geometric descriptors.

The repository contains the frozen algorithms, preregistered protocols, data-selection procedures, descriptor-extraction engine, statistical analysis pipeline, audit manifests, and reporting constraints used in the TRACEBIND study.

The principal B3 observable, $C_\phi$, is a bounded directional-alignment descriptor defined as the mean absolute projection of local wind velocity onto the tangential basis relative to the specified analysis center. It measures directional alignment, not wind-speed magnitude.

---

## Research Governance & Reproducibility

TRACEBIND follows a versioned study-governance model designed to minimize researcher degrees of freedom and preserve reproducibility.

* **Pre-Registration:** Sampling strategies, exclusion criteria, descriptor definitions, statistical tests, and analysis parameters are specified before the corresponding analysis phase.
* **Cryptographic Auditing:** Phase artifacts are linked through SHA-256 hashes recorded in machine-readable audit manifests.
* **Deterministic Execution:** Randomized procedures use explicitly specified seeds and reproducible algorithms. Analyst-controlled branching is prohibited during preregistered analysis execution.
* **Separation of Measurement and Inference:** Phase B3 extracts $C_\phi$ without using case labels in the descriptor calculation. Phase B4 is the preregistered stage at which TC/Control labels are introduced for statistical inference.
* **Reporting Firewall:** Phase B5 defines permitted interpretations and explicitly prohibits causal, mechanistic, or evidential overreach beyond the statistical findings.

---

## Current Study Status

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase A** | Operator Validation & Geometric Characterization | ✅ **FROZEN** (`v1.0-phase-a`) |
| **Phase B0** | Infrastructure & Governance Specification | ✅ **FROZEN** |
| **Phase B0.5** | IBTrACS Population Census | ✅ **FROZEN** |
| **Phase B0.75** | Population Characterization (CONSORT Pipeline) | ✅ **FROZEN** |
| **Phase B1** | Tropical Cyclone Cohort Selection (N=150) | ✅ **FROZEN** |
| **Phase B2.1** | Control Selection (N=150) | ✅ **FROZEN** (`v5.1-phase-b2.1-frozen`) |
| **Phase B2.2** | ERA5 Data Acquisition & QC (300 fields) | ✅ **FROZEN** (`v1.6-phase-b2.2-frozen`) |
| **Phase B3** | Blind Descriptor Extraction ($C_\phi$) | ✅ **FROZEN** (`v1.0-phase-b3-frozen`) |
| **Phase B4** | Preregistered Statistical Analysis | ✅ **FROZEN** (`v1.0-phase-b4-frozen`) |
| **Phase B5** | Reporting & Interpretation Protocol | ✅ **FROZEN** (`v1.0-phase-b5-protocol`) |

**Important:** Phases B1–B4 constitute the completed computational/statistical analysis pipeline. Phase B5 is the frozen reporting and interpretation protocol governing how those results may be communicated.

---

## Frozen B4 Finding

The preregistered B4 analysis found statistically significant separation between the TC and Control $C_\phi$ distributions under the two-sided Mann–Whitney U test.

The frozen results were:
- **Cliff's delta:** approximately **0.374**
- **Welch sensitivity Hedges' $g$:** approximately **0.857**
- **ROC AUC:** approximately **0.687**
- **Bootstrap 95% CI:** approximately **0.625–0.744**
- **Mann–Whitney U:** $p \approx 2.12 \times 10^{-8}$

The observed AUC indicates **statistically significant discriminative ability of moderate magnitude, with substantial overlap between the two cohorts**. These results do not establish causality, prove a physical mechanism, or demonstrate emergent gravity.

---

## Repository Structure

```text
TRACEBIND-Albatross/
├── README.md
├── LICENSE
├── DATA_SOURCES.md
├── phaseb/
│   ├── protocols/
│   ├── verify_*.py
│   └── ...
├── experiments/
├── src/
├── tests/
├── docs/
└── ...
```

Large raw data artifacts such as `.nc` and `ibtracs_ALL.csv` are intentionally excluded from version control where appropriate. Their integrity is preserved through SHA-256 hashes recorded in the relevant audit manifests.

---

## Key Documentation

* **PHASE_A_FREEZE.md** — Phase A methodology freeze.
* **FROZEN_ALGORITHM.md** — Mathematical definition of the TRACEBIND operator.
* **PREPROCESSING_CONTRACT.md** — Coordinate-aware preprocessing requirements.
* **phaseb/PHASE_B2.1_CONTROL_SELECTION_PROTOCOL_v3.2_FROZEN.md** — Preregistered control cohort selection.
* **phaseb/PHASE_B2.2_ERA5_ACQUISITION_PROTOCOL.md** — ERA5 acquisition and native-grid extraction protocol.
* **phaseb/PHASE_B3_DESCRIPTOR_EXTRACTION_PROTOCOL.md** — Blind $C_\phi$ extraction protocol.
* **phaseb/PHASE_B4_STATISTICAL_ANALYSIS_PROTOCOL.md** — Preregistered statistical analysis protocol.
* **phaseb/PHASE_B5_REPORTING_PROTOCOL.md** — Reporting and interpretation constraints.

---

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/bigwiginfohub-wq/TRACEBIND-Albatross.git
   cd TRACEBIND-Albatross
   ```

2. **Acquire the required data**
   Follow `DATA_SOURCES.md` for the required IBTrACS and ERA5 data sources.

3. **Reconstruct the documented environment**
   Use the software versions recorded in the relevant phase audit manifests.

4. **Verify provenance**
   Run the corresponding `verify_*.py` integrity-verification scripts before relying on phase artifacts.

5. **Do not modify frozen artifacts**
   Any methodological deviation must be documented as a formal protocol amendment rather than silently altering a frozen phase.

---

## Contact & Citation

**Research Lead:** Mohammed Ali, Independent Researcher  
**Repository:** [https://github.com/bigwiginfohub-wq/TRACEBIND-Albatross](https://github.com/bigwiginfohub-wq/TRACEBIND-Albatross)

If you use the TRACEBIND framework or its governance methodology, please cite the associated publications when available.

---

## Reproducibility Statement

TRACEBIND is maintained according to reproducible computational-science principles.

Frozen protocols define the permitted methodology for each phase. Audit manifests provide cryptographic integrity checks linking inputs, protocols, scripts, outputs, and execution metadata.

Any deviation from a frozen protocol must be explicitly documented and must not be presented as the original preregistered analysis.


