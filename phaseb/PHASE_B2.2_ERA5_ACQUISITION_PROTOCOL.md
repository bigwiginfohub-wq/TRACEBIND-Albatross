# PHASE B2.2: ERA5 Acquisition & Quality Control Protocol

**Version:** 1.0  
**Status:** READY FOR FREEZE  
**Predecessor:** Phase B1 (TC Cohort Selection) & Phase B2.1 (Control Selection)  
**Successor:** Phase B3 (Descriptor Extraction)

---

## 1. Objective
To programmatically acquire, verify, and structure high-resolution ERA5 reanalysis data for the exact spatiotemporal coordinates of the 150 Phase B1 Tropical Cyclones (TCs) and the 150 Phase B2.1 non-cyclonic Controls. 

**Crucial Distinction:** This phase acquires the **spatial velocity fields** surrounding each of the 300 target centers, providing the necessary spatial coverage to permit the reproducible calculation of the pre-registered Phase B3 $C_\phi$ descriptor. It does not merely acquire point observations.

---

## 2. Target Coordinates
The acquisition script shall target exactly **300 spatiotemporal centers**:
1. **150 TC Centers**: Sourced from `phaseb/selected_cohort_ids.csv` (Phase B1).
2. **150 Control Centers**: Sourced from `phaseb/selected_control_ids.csv` (Phase B2.1, `Status == "Selected"`).

For each center, the script shall extract data at the exact `Timestamp`, `Latitude`, and `Longitude` recorded in the respective CSV files, plus the surrounding spatial domain required for Phase B3.

---

## 3. Data Source & Variables
- **Source**: ECMWF Climate Data Store (CDS) via `cdsapi`.
- **Dataset**: `reanalysis-era5-single-levels` (ERA5 hourly data on single levels from 1940 to present).
- **Dataset DOI**: `10.24381/cds.adbb2d47`
- **Spatial Resolution**: 0.25° × 0.25° (Native ERA5 grid).
- **Required Variables**:
  1. `10m_u_component_of_wind` (m/s)
  2. `10m_v_component_of_wind` (m/s)
  *(Note: No additional variables (e.g., temperature, MSLP) shall be acquired unless explicitly mandated by the frozen Phase B3 descriptor specification.)*

---

## 4. Acquisition Strategy (Batched & Efficient)
To ensure operational efficiency without compromising scientific precision, the acquisition shall **not** make 300 individual point requests. Instead:
1. **Group Targets**: Group the 300 target centers by date/time to identify overlapping or proximate requests.
2. **Define Acquisition Domain**: For each group, calculate a rectangular bounding box that encompasses all target centers plus a sufficient margin beyond 150 km to ensure that the complete 30–150 km analysis shell is represented on the native 0.25° ERA5 grid.
3. **Batch Request**: Submit a single CDS API request per bounding box/timestep combination.
4. **Local Extraction**: Programmatically extract the precise target windows from the downloaded regional fields.

*This batching is strictly an implementation detail and must not alter the scientific target or the final extracted data.*

---

## 5. Strict Quality Control (QC) Rules
Every acquired target center must pass the following deterministic, automated checks. Failures must be logged, not silently ignored or substituted.

1. **Identity**: Every field must remain unambiguously linked to exactly one `SID` (for TCs) or `ControlID` (for controls).
2. **Temporal Exactness**: The acquired ERA5 timestamp must **exactly match** the frozen requested hourly timestamp. If the requested timestamp is not available in the ERA5 response, the case shall fail QC; the acquisition engine shall not silently substitute another hour.
3. **Spatial Determinism**: The requested center coordinate shall be mapped deterministically to the nearest native ERA5 grid coordinate solely for center-reference metadata. The surrounding u10/v10 field shall retain the native ERA5 grid without interpolation, rotation, reprojection, smoothing, or any other spatial transformation during B2.2 acquisition.
4. **Completeness**: All required grid cells inside the Phase B3 **analysis domain** (the deterministic 30–150 km great-circle shell around the frozen center) must be present. No `NaN` or `null` values are permitted within this shell.
5. **Dimensions & Orientation**: Verify expected latitude/longitude dimensions are present and correctly ordered (e.g., descending latitude, ascending longitude).
6. **Units**: Verify variables are in `m s⁻¹`.
7. **Range (Anomaly Screen)**: Wind components must fall within physically plausible limits (e.g., `-100 m/s < u, v < 100 m/s`). Values outside this threshold trigger an investigation, not automatic rejection, but must be explicitly flagged.

---

## 6. Output Artifacts
Upon successful completion, the script shall generate:

1. **`b2.2_era5_fields.nc`** (Primary Scientific Artifact):  
   A structured NetCDF file containing the acquired spatial fields for all 300 targets, preserving the native spatial grid, coordinates, and metadata.  
   - **Dimensions**: `(case, time, latitude, longitude)`  
   - **Variables**: `u10(case, time, latitude, longitude)`, `v10(case, time, latitude, longitude)`  
   - **Case Metadata**: Must include `case_id`, `case_type`, `requested_timestamp`, `requested_latitude`, `requested_longitude`, `center_grid_latitude`, `center_grid_longitude`.

2. **`b2.2_target_index.csv`** (Derived Manifest/Index):  
   A tabular audit file containing one row per target, with columns:  
   `ID`, `Type` (TC/Control), `RequestedTimestamp`, `RequestedLat`, `RequestedLon`, `ERATimestamp`, `CenterLat`, `CenterLon`, `GridDistanceKm`, `QC_Status`.

3. **`b2.2_qc_audit.json`** (Cryptographic Manifest):  
   - Dataset identifier and DOI.
   - Request parameters (variables, grid resolution, geographic extents).
   - SHA256 hashes of input CSVs (`selected_cohort_ids.csv`, `selected_control_ids.csv`).
   - SHA256 hash of the acquisition script.
   - Git commit hash at the time of execution.
   - Summary statistics: Total requested (300), Total successful, Total failed.

4. **`b2.2_qc_failure_log.csv`**:  
   A detailed log of any points that failed QC, including the specific reason (e.g., "NaN in u10", "CDS API Timeout after 3 retries").

---

## 7. Failure Handling & Amendment Trigger
- **Retries**: If a CDS API request fails (e.g., network timeout), the script shall implement an exponential backoff retry mechanism (max 3 retries).
- **Logging**: If a point fails QC after retries, it shall be recorded in `b2.2_qc_failure_log.csv`.
- **Completion Rule**: **Acquisition may complete with failures, but Phase B2.2 cannot be declared scientifically complete until every required case (300/300) has a valid dataset OR a formally approved protocol amendment is drafted.** A generic "<5% failure rate" is explicitly rejected as an automatic pass criterion, as it would leave the Phase B3 cohort incomplete.

---

## 8. Freeze Criteria
This protocol is considered frozen when:
1. This document is committed to Git with a `v1.0-phase-b2.2-protocol` tag.
2. The acquisition script is written to strictly adhere to these rules.
3. The script is executed, and the `b2.2_qc_audit.json` confirms 100% success rate (or formally amended exceptions) with all QC checks passed.