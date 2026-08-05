# TRACEBIND Phase B2.2: ERA5 Acquisition & Data QC Protocol

**Status:** Frozen  
**Date:** 2026-08-04  
**Principal Investigator:** Mohammed Ali, Independent Researcher  

---

## 1. Objective & Firewall
To acquire, verify, and freeze the ERA5 10m wind field data for the 300-case cohort (150 TCs from B2.1 + 150 Controls from B2.1). **Descriptor extraction is explicitly excluded from this phase.**

**FIREWALL CLAUSE:** No scientific descriptors, feature extraction, thresholding, ranking, or retrieval metrics shall be computed during Phase B2.2.

---

## 2. Acquisition Specification

### 2.1 Data Source
* **Dataset:** ECMWF ERA5 Reanalysis (`reanalysis-era5-single-levels`).
* **CDS API Version:** To be recorded in the manifest at execution time.
* **Variables:** 
  * `10m_u_component_of_wind` ($u_{10}$)
  * `10m_v_component_of_wind` ($v_{10}$)
* **Temporal Resolution:** Single instantaneous snapshot per case (matching the 6-hourly timestamp selected in B2.1).

### 2.2 Deterministic Bounding Box
For each case, extract a regional domain centered on the case coordinate (TC circulation center or Control coordinate).
* **Algorithm:** A fixed bounding box of exactly **10° latitude × 10° longitude** centered on the target coordinate. (This yields a deterministic grid size of 41×41 points at 0.25° resolution, approximately 1100 km × 1100 km at the equator).
* **Format:** NetCDF-4.
* **Naming Convention:** `{CASE_TYPE}_{CASE_INDEX}_{BASIN}_{TIMESTAMP}.nc` (e.g., `TC_0001_NI_20200512T060000.nc`).

### 2.3 Retry Policy
* Maximum 3 automated retries per file via CDS API.
* If a file fails 3 retries, it is logged in `failed_downloads.csv` and flagged for manual review.

---

## 3. Data Integrity & QC Gates

Every downloaded NetCDF file must pass the following automated gates before being accepted.

### Gate 1: Structural Integrity
* File is readable via `xarray`/`netCDF4`.
* Expected variables ($u_{10}$, $v_{10}$) are present.
* Spatial dimensions are exactly 41×41 grid points.

### Gate 2: Physical & Coordinate Integrity
* **Finite Values:** No `NaN` or `Inf` values in the wind fields.
* **Coordinate Monotonicity:** Latitude and longitude arrays must be strictly monotonic.
* **Wind Speed Sanity:** Maximum wind speed in the domain must be $> 0$ and $< 150$ m/s.

### Gate 3: Metadata Integrity
* Verify CRS, units (m/s), timestamp, and variable names match expected ERA5 metadata.

### Gate 4: Cryptographic Verification
* Compute and record the SHA-256 hash of every accepted NetCDF file.

---

## 4. Deliverables & Freeze Manifest

Upon successful completion of QC, the following immutable artifacts will be generated:

* **`B2_DATASET_MANIFEST.json`**: The master provenance document containing:
  * Protocol hash and acquisition script hash.
  * CDS dataset identifier, retrieval date, and API version.
  * A dictionary mapping every accepted filename to its metadata: SHA-256 hash, file size, NetCDF dimensions, timestamp, basin, and case ID.
  * Acquisition timestamps and retry logs.
  * Final accepted file count (Target: 300).
* **`failed_downloads.csv`**: Log of any files that failed acquisition or QC.

---
*This protocol constitutes the pre-registered specification for Phase B2.2. Any deviation requires a formal protocol amendment.*