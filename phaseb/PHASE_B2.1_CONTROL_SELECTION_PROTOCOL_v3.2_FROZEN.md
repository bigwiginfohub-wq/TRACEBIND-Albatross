\# TRACEBIND Phase B2.1: Control Selection Protocol



\*\*Status:\*\* DRAFT v3.2 FROZEN 

\*\*Date:\*\* 2026-08-04  

\*\*Version:\*\* 3.2



\---



\## 1. Scientific Definition of "Control"



A control is defined as an atmospheric snapshot that satisfies ALL of the following criteria:



1\. \*\*Temporal Matching:\*\* Occurs in the same calendar month as at least one Phase B1 Tropical Cyclone (TC) in the same basin.

2\. \*\*Latitude Matching:\*\* Occurs within the same Latitude Matching Class (LMC) as at least one Phase B1 TC in the same basin and month.

3\. \*\*Spatial Exclusion:\*\* No IBTrACS observation point exists within 1000 km great-circle distance (measured using Haversine metric).

4\. \*\*Temporal Exclusion:\*\* No IBTrACS observation point exists within the inclusive interval \[-7 days, +7 days] of the candidate timestamp.

5\. \*\*Ocean Requirement:\*\* Located over open ocean, verified using ERA5 land-sea mask (lsm < 0.5, with exactly 0.5 treated as land).

6\. \*\*ERA5 Availability:\*\* Corresponds to an existing ERA5 record retrievable through CDS at 6-hourly intervals (00:00, 06:00, 12:00, 18:00 UTC) on the native 0.25° × 0.25° grid.



\*\*Rationale:\*\* This definition controls for seasonal climatology, Coriolis parameter, SST gradients, and Hadley circulation patterns while ensuring every candidate corresponds to actual ERA5 data.



\---



\## 2. Data Sources \& Preprocessing



\### 2.1 IBTrACS Data

\- \*\*Source:\*\* `ibtracs\_ALL.csv` (v04r01)

\- \*\*Temporal Filter:\*\* Only storms with `SEASON >= 1980` (modern observational era)

\- \*\*Robust Parsing:\*\* 

&#x20; ```python

&#x20; ibtracs\["SEASON\_INT"] = pd.to\_numeric(ibtracs\["SEASON"], errors="coerce")

&#x20; bad\_rows = ibtracs\["SEASON\_INT"].isna()

&#x20; ibtracs\_rejected = ibtracs\[bad\_rows].copy()

&#x20; ibtracs\_valid = ibtracs\[\~bad\_rows].copy()

&#x20; ```

\- \*\*Audit:\*\* Save `ibtracs\_rejected\_rows.csv` containing all malformed rows with rejection reason.



\### 2.2 Ocean Mask

\- \*\*Source:\*\* ERA5 land-sea mask (`lsm` variable from `reanalysis-era5-land`)

\- \*\*Resolution:\*\* 0.25° × 0.25° (native ERA5 grid)

\- \*\*Threshold:\*\* Grid cell is "ocean" if `lsm < 0.5` (exactly 0.5 is treated as land)

\- \*\*Rationale:\*\* Using the same grid and data ecosystem as the atmospheric fields eliminates projection and interpolation artifacts.



\### 2.3 Basin Boundaries

\- \*\*Source:\*\* IBTrACS basin classification (BASIN column)

\- \*\*Definition:\*\* Use the basin assignment provided by IBTrACS for each storm track point

\- \*\*Rationale:\*\* IBTrACS is the authoritative source for tropical cyclone basin classification



\### 2.4 ERA5 Temporal Coverage

\- \*\*Period:\*\* 1980-01-01 to 2025-12-31

\- \*\*Frequency:\*\* 6-hourly (00:00, 06:00, 12:00, 18:00 UTC)

\- \*\*Grid:\*\* 0.25° × 0.25° (native resolution)

\- \*\*Verification:\*\* Candidate timestamps must correspond to records retrievable through CDS API



\---



\## 3. Candidate Generation Algorithm



\### 3.1 Step 1: Extract Required Strata from Phase B1

For each TC in the Phase B1 cohort, extract:

\- `Basin` (from IBTrACS BASIN column)

\- `Month` (1-12)

\- \*\*Analysis Latitude:\*\* Latitude extracted from the frozen Phase B1 analysis snapshot (not genesis latitude)



\*\*Latitude Matching Class (LMC) Assignment:\*\*

Assign each TC to a fixed 5° latitude bin using the formula:

```python

lmc\_lower = floor(latitude / 5) \* 5

lmc\_upper = lmc\_lower + 5

lmc\_label = f"{lmc\_lower}to{lmc\_upper}"

```



This creates global bins:

```

\[-40, -35), \[-35, -30), ..., \[-5, 0), \[0, 5), \[5, 10), ..., \[35, 40)

```



\*\*Example:\*\* If TC analysis occurred at 17.8°N in October in the Bay of Bengal:

\- Basin: NI

\- Month: 10

\- LMC: 15to20



Group into strata: `Basin × Month × LMC`



\### 3.2 Step 2: Generate Candidate Pool

For each stratum:

1\. \*\*Temporal Axis:\*\* Generate all ERA5 6-hourly timestamps for the target month across years 1980-2025 that are retrievable through CDS.

2\. \*\*Spatial Axis:\*\* Generate all ERA5 0.25° grid cells within the target LMC and basin (as defined by IBTrACS).

3\. \*\*Ocean Filter:\*\* Retain only grid cells where `lsm < 0.5`.

4\. \*\*Cartesian Product:\*\* Create all (timestamp, lat, lon) combinations.



\*\*Output:\*\* Raw candidate pool.



\### 3.3 Step 3: Apply Exclusion Filters

For each candidate (timestamp, lat, lon):



\*\*Constants:\*\*

\- Earth radius: `R = 6371.0088 km`

\- Spatial exclusion radius: `radius\_rad = 1000 / R` (in radians)



\*\*Filter 1: Spatial Exclusion (1000 km)\*\*

\- Build `sklearn.neighbors.BallTree` with `metric='haversine'` from all IBTrACS observation points (1980-present).

\- Convert candidate coordinates to radians: `lat\_rad = lat \* π / 180`, `lon\_rad = lon \* π / 180`

\- Query BallTree for all storm observation points within `radius\_rad` of candidate.

\- If any storm observation point exists, reject candidate.

\- \*\*Note:\*\* Distance is measured from candidate to every IBTrACS observation point, not storm center.



\*\*Filter 2: Temporal Exclusion (±7 days)\*\*

\- For remaining candidates, check if any IBTrACS observation point (from Filter 1 results) occurs within the inclusive interval \[-7 days, +7 days] of candidate timestamp.

\- Mathematically: reject if `|candidate\_time - storm\_time| <= 7 days`

\- If yes, reject candidate.



\*\*Output:\*\* Eligible candidate pool.



\### 3.4 Step 4: Deduplicate and Save Eligible Candidate Pool

Remove any duplicate rows (same timestamp, lat, lon) to prevent accidental duplication from affecting the hash.



Save the complete eligible candidate pool to `eligible\_candidate\_pool.csv` with columns:

\- `Basin`, `Month`, `LMC`

\- `Timestamp` (ISO 8601)

\- `Latitude`, `Longitude`



\*\*File Format:\*\* UTF-8 encoding, LF line endings, no BOM.



\*\*Rationale:\*\* This file becomes an immutable artifact that can be independently verified.



\### 3.5 Step 5: Deterministic Sorting

Sort `eligible\_candidate\_pool.csv` using \*\*stable sort\*\* by:

1\. `Basin` (ascending)

2\. `Month` (ascending)

3\. `LMC` (ascending)

4\. `Timestamp` (ascending, ISO 8601 format)

5\. `Latitude` (ascending)

6\. `Longitude` (ascending)



\*\*Critical Rule:\*\* The RNG SHALL NEVER operate on unsorted data. Stable sort ensures consistent ordering when keys are equal.



\*\*Rationale:\*\* Ensures the candidate pool is identical regardless of generation order, enabling reproducible hashing.



\### 3.6 Step 6: Candidate Pool Fingerprint

Compute SHA-256 hash of the sorted `eligible\_candidate\_pool.csv` file:

```python

candidate\_pool\_hash = hashlib.sha256(open('eligible\_candidate\_pool.csv', 'rb').read()).hexdigest()

candidate\_pool\_rows = len(pd.read\_csv('eligible\_candidate\_pool.csv'))

```



\*\*Audit:\*\* Record both `candidate\_pool\_hash` and `candidate\_pool\_rows` in manifest.



\### 3.7 Step 7: Stratified Random Sampling

For each stratum (Basin × Month × LMC):

1\. Extract candidates belonging to this stratum from the sorted pool.

2\. Shuffle using `numpy.random.default\_rng(seed=43)`.

3\. Select the required number of controls (matching Phase B1 TC count for this stratum).

4\. Record `RandomRank` for each selected candidate.

5\. Build replacement list: all unselected candidates in this stratum, ordered by `RandomRank`.



\*\*Critical Rule:\*\* Replacement SHALL use the next unused RandomRank within the identical (Basin, Month, LMC) stratum. Cross-stratum replacement is prohibited.



\---



\## 4. Deliverables



\### 4.1 Primary Outputs

1\. \*\*`eligible\_candidate\_pool.csv`\*\*: Complete eligible candidate pool (immutable artifact)

&#x20;  - Columns: `Basin`, `Month`, `LMC`, `Timestamp`, `Latitude`, `Longitude`

&#x20;  - Sorted deterministically before hashing

&#x20;  - UTF-8, LF line endings, no BOM



2\. \*\*`selected\_control\_ids.csv`\*\*: Final 150 controls with columns:

&#x20;  - `ControlID` (CTRL\_001 to CTRL\_150)

&#x20;  - `Basin`, `Month`, `LMC`

&#x20;  - `Timestamp` (ISO 8601)

&#x20;  - `Latitude`, `Longitude`

&#x20;  - `RandomRank` (within stratum)

&#x20;  - `StratumID` (e.g., "NI\_10\_15to20")



3\. \*\*`control\_randomized\_order.csv`\*\*: Full ranked list for deterministic replacement:

&#x20;  - All columns from `selected\_control\_ids.csv`

&#x20;  - `Status`: "Selected" or "Standby"

&#x20;  - `StratumID`



4\. \*\*`control\_candidate\_filter\_log.csv`\*\*: Rejection audit:

&#x20;  - Candidate coordinates and timestamp

&#x20;  - Rejection reason ("Spatial Exclusion", "Temporal Exclusion", "Land Mask")

&#x20;  - Nearest storm SID and distance/time difference



5\. \*\*`ibtracs\_rejected\_rows.csv`\*\*: Malformed IBTrACS rows with rejection reason.



\### 4.2 Audit Manifest

\*\*`control\_audit.json`\*\* containing:



\*\*Freeze Fingerprint:\*\*

\- Protocol version: 3.2

\- Protocol SHA-256

\- Script SHA-256

\- Git commit hash

\- Execution timestamp (UTC)

\- Random seed: 43



\*\*Software Versions:\*\*

\- Python version

\- NumPy version

\- Pandas version

\- scikit-learn version (BallTree)



\*\*Data Source Hashes:\*\*

\- IBTrACS file SHA-256

\- ERA5 land-sea mask SHA-256



\*\*Candidate Pool:\*\*

\- `eligible\_candidate\_pool.csv` SHA-256

\- `eligible\_candidate\_pool.csv` row count



\*\*Output File Hashes:\*\*

\- `selected\_control\_ids.csv` SHA-256

\- `control\_randomized\_order.csv` SHA-256



\*\*Summary Statistics:\*\*

\- Total candidates generated

\- Total candidates rejected (by filter type)

\- Total eligible candidates

\- Total selected controls: 150

\- Stratum-level summary (count per Basin × Month × LMC)



\---



\## 5. Invariants \& Validation Checks



Before declaring Phase B2.1 frozen, verify:



1\. \*\*Total Count:\*\* Exactly 150 controls selected.

2\. \*\*Basin Balance:\*\* Exactly 50 controls per basin (NI, SI, WP).

3\. \*\*Stratum Matching:\*\* Each stratum has the same number of controls as Phase B1 TCs in that stratum.

4\. \*\*No Duplicates:\*\* All 150 controls have unique (Timestamp, Latitude, Longitude).

5\. \*\*Exclusion Compliance:\*\* Spot-check 10 random controls to verify no IBTrACS storm observation point within 1000 km / ±7 days.

6\. \*\*Ocean Compliance:\*\* Spot-check 10 random controls to verify `lsm < 0.5`.

7\. \*\*Replacement Integrity:\*\* Verify that `control\_randomized\_order.csv` contains all eligible candidates, with correct `RandomRank` ordering.

8\. \*\*Hash Verification:\*\* Verify that all output file hashes match those recorded in `control\_audit.json`.

9\. \*\*Row Count Verification:\*\* Verify that `eligible\_candidate\_pool.csv` row count matches manifest.



\---



\## 6. Implementation Notes



\### 6.1 Computational Strategy

\- \*\*BallTree with Haversine Metric:\*\* Build `sklearn.neighbors.BallTree` with `metric='haversine'` from all IBTrACS storm observation points (1980-present) for proper spherical distance queries.

\- \*\*Radius Conversion:\*\* Convert 1000 km to radians using `radius\_rad = 1000 / 6371.0088`.

\- \*\*Vectorized Filtering:\*\* Apply exclusion filters using NumPy broadcasting where possible.

\- \*\*Chunked Processing:\*\* Process candidates in chunks (e.g., 100,000 at a time) to manage memory.



\### 6.2 Ocean Mask Acquisition

\- Download from CDS: `reanalysis-era5-land` dataset, variable `land\_sea\_mask`.

\- Resample to 0.25° × 0.25° grid if necessary.

\- Save as `era5\_land\_sea\_mask.nc` for reproducibility.



\### 6.3 File Format Consistency

\- All CSV files: UTF-8 encoding, LF line endings, no BOM

\- Ensures identical hashes across Windows/Linux/macOS



\### 6.4 Reproducibility

\- All random operations use `numpy.random.default\_rng(seed=43)`.

\- Candidate pool is sorted deterministically (stable sort) before hashing.

\- Hash is computed on the CSV file before randomization to prove RNG operated on the intended pool.

\- All output files are hashed and recorded in audit manifest.



\---



\## 7. Protocol Amendments



Any deviation from this protocol requires:

1\. Written justification.

2\. Updated protocol version number.

3\. Re-execution of the entire B2.1 pipeline.

4\. Updated audit manifest with amendment log.



\*\*No manual interventions are permitted.\*\* If a control fails QC in Phase B2.2, replacement must use the pre-generated `RandomRank` ordering within the same stratum.



\---



\## 8. Changes from v3.1



1\. \*\*Global Latitude Bins:\*\* Replaced hemisphere-specific bins with global formula: `floor(latitude / 5) \* 5`

2\. \*\*Basin Boundaries:\*\* Specified IBTrACS BASIN column as authoritative source

3\. \*\*BallTree Radius:\*\* Explicitly specified `radius\_rad = 1000 / 6371.0088` (radians)

4\. \*\*Earth Radius:\*\* Frozen at `R = 6371.0088 km`

5\. \*\*Land-Sea Mask Boundary:\*\* Specified exactly 0.5 is treated as land

6\. \*\*Deduplication:\*\* Added explicit step to drop duplicates before hashing

7\. \*\*Stable Sort:\*\* Specified stable sort for consistent ordering

8\. \*\*File Encoding:\*\* Specified UTF-8, LF line endings, no BOM for cross-platform consistency

9\. \*\*Latitude Source:\*\* Strengthened to "extracted from frozen Phase B1 analysis snapshot"

10\. \*\*ERA5 Availability:\*\* Strengthened to "must correspond to existing ERA5 record retrievable through CDS"

11\. \*\*Row Count:\*\* Added candidate pool row count to audit manifest

12\. \*\*Freeze Fingerprint:\*\* Added consolidated section with all key hashes and versions

13\. \*\*Terminology:\*\* Renamed "LatitudeBin" to "Latitude Matching Class (LMC)" to describe scientific purpose



\---



\## 9. Next Steps



Upon approval, this protocol will be frozen and implementation will proceed as follows:

1\. Acquire ERA5 land-sea mask from CDS.

2\. Implement `b2.1\_select\_controls\_v3.2.py` following this protocol exactly.

3\. Execute script and verify all invariants.

4\. Generate audit manifest and declare Phase B2.1 frozen.

5\. Proceed to Phase B2.2 (ERA5 Acquisition).



\---



\*\*End of Protocol\*\*

```





