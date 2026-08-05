\# TRACEBIND Phase B0: Infrastructure, Governance, and Dataset Census Specification



\*\*Status:\*\* Frozen Protocol  

\*\*Date:\*\* 2026-08-03  

\*\*Principal Investigator:\*\* Mohammed Ali, Independent Researcher  



\---



\## 1. Scientific Philosophy

Phase B is not intended to maximize retrieval accuracy by iteratively modifying descriptors. Instead, it is designed to evaluate the scientific utility and generalizability of the frozen TRACEBIND framework under substantially broader observational conditions. Any modifications to the descriptor definitions or extraction methodology will constitute a separately versioned framework and will not be incorporated into the frozen Phase B analysis.



\---



\## 2. Inclusion and Exclusion Criteria



\### Inclusion Criteria (Must meet ALL)

1\. \*\*TC Cases:\*\* Must have a verified Storm Identifier (SID) in the IBTrACS database.

2\. \*\*Control Cases:\*\* Must be a clearly defined, non-cyclonic synoptic feature identifiable in ERA5 reanalysis.

3\. \*\*Data Completeness:\*\* The ERA5 10m wind field ($u\_{10}$, $v\_{10}$) must be 100% complete (no NaNs or missing grid points) across the entire regional domain for the target snapshot.

4\. \*\*Temporal Alignment:\*\* The ERA5 snapshot timestamp must align with the nearest IBTrACS best-track observation within a predefined tolerance (e.g., $\\pm$ 3 hours).



\### Exclusion Criteria (Reject if ANY)

1\. \*\*Basin Crossing:\*\* Storms that are actively transitioning between basins during the snapshot window.

2\. \*\*Disrupted Circulation:\*\* Storms whose circulation center is so disrupted (e.g., severe post-landfall decay) that a coherent center no longer exists. \*Note: Landfalling storms are explicitly included and tagged, not excluded.\*

3\. \*\*Duplicate Cases:\*\* The exact same storm at the exact same timestamp cannot be included twice. (Simultaneous distinct storms are permitted).



\---



\## 3. Dataset Specification



\### Sample Size

\* \*\*Target Range:\*\* 250–350 independent atmospheric cases. 



\### Geographic Stratification

\* \*\*Principle:\*\* Phase B will include at least three independent tropical cyclone basins to evaluate cross-basin generalization. 

\* \*\*Execution:\*\* The exact basin composition will be determined during the Phase B0.5 Dataset Census according to data availability, metadata completeness, and balancing constraints.



\### Intensity Stratification

\* \*\*Derivation:\*\* Intensity classes will be derived directly from maximum sustained wind speed ($W\_{max}$) to remain insulated from inter-agency category differences (e.g., IMD vs. SSHWS).

\* \*\*Target Balance:\*\* Stratified sampling will aim for approximate balance across Weak, Moderate, and Intense tiers within each basin.



\---



\## 4. Metadata Schema

Every case in the final dataset will have a row in `metadata\_comprehensive.csv` containing exactly these fields.



| Field Name | Data Type | Source | Description |

| :--- | :--- | :--- | :--- |

| `case\_uuid` | String | Internal | HMAC-SHA256 hashed identifier. |

| `ibtracs\_sid` | String | IBTrACS | Official Storm Identifier (Controls = `NA`). |

| `basin` | Categorical | IBTrACS | Basin of origin/operation. |

| `snapshot\_time` | ISO-8601 | ERA5 | Exact timestamp of the 10m wind field. |

| `max\_wind\_kt` | Float | IBTrACS | WMO maximum sustained wind speed. |

| `min\_pressure\_hpa`| Float | IBTrACS | WMO minimum central pressure. |

| `intensity\_class` | Categorical | Derived | Weak, Moderate, Intense (based strictly on wind). |

| `lifecycle\_stage` | Categorical | Pending | Set to `pending`. To be defined in a separate `LIFECYCLE\_SPEC.md`. |

| `storm\_age\_hours` | Float | IBTrACS | Hours since genesis. |

| `translation\_speed` | Float | IBTrACS | Storm motion speed in knots. |

| `rmw\_nm` | Float | IBTrACS | Radius of Maximum Winds (if available, else `NA`). |

| `landfall\_status` | Categorical | Derived | Ocean\_Only, Pre\_Landfall, Landfall, Post\_Landfall. |

| `distance\_to\_land`| Float | Derived | Distance from circulation center to nearest coastline (km). |



\---



\## 5. Quality Control (QC) Rules



\### Pre-Extraction QC

1\. \*\*The "NaN Check":\*\* Any ERA5 file containing `NaN` values in the $u\_{10}$ or $v\_{10}$ arrays is automatically rejected.

2\. \*\*The "SID Check":\*\* Every TC case must successfully map to an IBTrACS SID.

3\. \*\*Coordinate QC:\*\* Verify latitude ordering, longitude ordering, and grid spacing before derivative computations to prevent the descending-grid vulnerability identified in Phase A.



\### Post-Extraction QC

4\. \*\*Descriptor Range QC:\*\* Check every extracted descriptor is finite. Reject cases yielding `NaN`, `Inf`, or numerical overflow.

5\. \*\*Vorticity Sanity Check:\*\* Maximum absolute vorticity must be $> 0$.



\---



\## 6. Data Provenance

To ensure full reproducibility, the following metadata will be recorded in a `provenance.json` file:

\* ERA5 dataset version and download date.

\* IBTrACS dataset version and download date.

\* Processing script SHA-256 hashes.

\* TRACEBIND descriptor version (Frozen v1.0).

\* Software environment commit hash.



\---



\## 7. Phased Execution Roadmap



\### Phase B0 — Infrastructure \& Governance (Current)

\* Freeze dataset specification, metadata schema, and QC rules.

\* \*Deliverable:\* This specification document.



\### Phase B0.5 — Dataset Census

\* Query available ERA5 and IBTrACS data against the B0 inclusion criteria.

\* Characterize the available population: How many storms exist per basin? Which years have complete metadata? Which intensity classes are underrepresented?

\* \*Deliverable:\* A census report detailing the available population, used to finalize the exact sampling strategy for B1. No descriptor extraction yet.



\### Phase B1 — Dataset Construction

\* Execute the sampling strategy defined in B0.5.

\* Acquire and verify the final 250–350 cases.

\* \*Deliverable:\* Curated dataset and frozen `metadata\_comprehensive.csv`.



\### Phase B2 — Descriptor Extraction

\* Run the frozen TRACEBIND pipeline on the full cohort.

\* \*Deliverable:\* Descriptor matrix outputs.



\### Phase B3 — Representation Analysis

\* Repeat Phase A analyses (PCA, VIF, dimensionality, ranking agreement) on the large cohort.



\### Phase B4 — Scientific Retrieval

\* Evaluate retrieval performance across predefined physical targets.



\### Phase B5 — Interpretation

\* Synthesize results according to the pre-registered decision tree.



\---

\*By committing this document to the repository, the investigator agrees to adhere strictly to this protocol. Any deviation will be explicitly documented and justified as exploratory.\*

