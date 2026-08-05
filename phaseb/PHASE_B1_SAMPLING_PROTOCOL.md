\# TRACEBIND Phase B1: Dataset Sampling Protocol



\*\*Status:\*\* Frozen Protocol  

\*\*Date:\*\* 2026-08-03  

\*\*Principal Investigator:\*\* Mohammed Ali, Independent Researcher  



\---



\## Version Lock

\* \*\*IBTrACS Version:\*\* v04r01

\* \*\*ERA5 Version:\*\* 1940–present (Single-level reanalysis)

\* \*\*TRACEBIND Version:\*\* v1.0 (Frozen in Phase A)

\* \*\*Protocol Version:\*\* 1.0



\## Scientific Philosophy

\*\*The objective of the sampling protocol is not to maximize sample size but to maximize inferential validity while preserving reproducibility.\*\* Phase B is designed to evaluate the scientific utility and generalizability of the frozen TRACEBIND framework under substantially broader observational conditions. Any modifications to the descriptor definitions or extraction methodology will constitute a separately versioned framework.



\---



\## 1. Source Population \& Temporal Cutoff

\* \*\*Source Catalog:\*\* IBTrACS v04r01 (`ibtracs\_ALL.csv`).

\* \*\*Target Basins:\*\* North Indian (NI), South Indian (SI), Western North Pacific (WP).

\* \*\*Total Raw Population:\*\* 8,967 storms.



\### 1.1 The Operational Temporal Cutoff

1980 is adopted as a protocol-defined operational cutoff chosen to improve observational consistency, metadata completeness, and comparability across storms. It should not be interpreted as implying that pre-1980 storms are scientifically invalid.

\* \*\*Temporal Gate:\*\* Only storms with a `SEASON` $\\ge$ 1980 will be eligible.



\---



\## 2. The CONSORT-Style Filtering Pipeline

Before any sampling occurs, the raw population will be passed through a strict sequence of exclusion gates.



\* \*\*Gate 1: Source Population\*\* (N = 8,967)

\* \*\*Gate 2: Temporal Cutoff\*\* (SEASON $\\ge$ 1980) $\\rightarrow$ \*Yields Eligible Population A.\*

\* \*\*Gate 3: Core Metadata Completeness\*\*

&#x20; \* Must have valid WMO Maximum Wind (`WMO\_WIND` is numeric and $> 0$).

&#x20; \* \*Rationale:\* TRACEBIND descriptors rely exclusively on ERA5 wind fields. Wind metadata is required for intensity stratification; pressure metadata is treated as optional and handled via Dataset Tiers. $\\rightarrow$ \*Yields Eligible Population B.\*



\---



\## 3. Dataset Tiers

To maximize the usable population without compromising rigor, the cohort is divided into two analysis-specific tiers.



\### Tier 1: Core Cohort (Primary Endpoints)

\* \*\*Requirements:\*\* Valid ERA5 10m wind field + Valid WMO Maximum Wind + Valid Basin.

\* \*\*Usage:\*\* Basin retrieval, Intensity Class retrieval, PCA comparison, Dimensionality analysis.

\* \*\*Target Size:\*\* 150 TCs + 150 Controls.



\### Tier 2: Extended Cohort (Secondary Endpoints)

\* \*\*Requirements:\*\* All Tier 1 requirements + Valid WMO Minimum Pressure (`WMO\_PRES` is numeric and $< 1050$).

\* \*\*Usage:\*\* Pressure retrieval, ACE correlation, RMW analysis.

\* \*\*Target Size:\*\* Subset of Tier 1 where pressure data is available.



\---



\## 4. Stratification and Sampling Strategy



\### 4.1 Tropical Cyclone Cases (Tier 1 Target N = 150)

From the \*\*Tier 1 Eligible Pool\*\*, we will perform stratified random sampling across a 3x3 matrix:

\* \*\*Strata 1 (Basin):\*\* NI, SI, WP.

\* \*\*Strata 2 (Intensity):\*\* Weak (<64kt), Moderate (64-95kt), Intense ($\\ge$96kt).



\*\*Sampling Rule:\*\*

\* Aim for equal representation across the 9 strata (approx. 16-17 storms per stratum). 

\* \*Exception:\* If a specific stratum contains fewer than 20 eligible storms, sample all available cases and proportionally redistribute the deficit to other strata within the same basin.



\### 4.2 Control Cases (Tier 1 Target N = 150)

Controls must be strictly defined to ensure deterministic selection.



\*\*Accepted Controls:\*\*

\* Monsoon lows

\* Weak vortices / Offshore troughs

\* Monsoon depressions below TC criteria

\* Large-scale shear zones



\*\*Rejected Controls:\*\*

\* Tropical cyclones (any intensity)

\* Extratropical cyclones / Frontal systems

\* Cases with missing or disrupted circulation centers

\* Strong land-induced vortices (e.g., intense thermal lows over deserts)



\*\*Temporal Matching:\*\*

Controls must be matched to the TC cohort by \*\*Calendar Month\*\* (e.g., a July cyclone is matched with a July control) to control for background environmental seasonality. The exact ERA5 timestamp must not overlap with any IBTrACS storm track within a 1000 km radius.



\---



\## 5. Randomization, Version Lock, and Replacement Policy



\### 5.1 Computational Reproducibility

All random sampling will be performed using a fixed environment to guarantee bitwise reproducibility:

\* \*\*Python:\*\* 3.12+

\* \*\*NumPy:\*\* `numpy.random.default\_rng(seed=42)`

\* \*\*Pandas:\*\* Latest stable release as of protocol freeze.



\### 5.2 Replacement Policy

If a selected case fails post-selection QC (e.g., ERA5 download corrupted, NaN values in wind field):

1\. The case is immediately rejected.

2\. It is replaced by the \*\*next available case in the exact same stratum\*\*, following the pre-generated random ordering.

3\. No manual selection or "cherry-picking" of replacement cases is permitted.



\---



\## 6. Deliverables of Phase B1

1\. `b075\_consort\_flow.csv`: The exact counts at every gate of the CONSORT pipeline.

2\. `selected\_cohort\_ids.csv`: The frozen list of SIDs (TCs) and coordinates/timestamps (Controls) to be downloaded.

3\. `metadata\_comprehensive.csv`: The complete, verified metadata for the final cohort, including Tier 1/Tier 2 flags.



\---

\*By committing this document, the investigator agrees to execute the sampling exactly as defined. Any deviation will be explicitly documented as a protocol amendment.\*

