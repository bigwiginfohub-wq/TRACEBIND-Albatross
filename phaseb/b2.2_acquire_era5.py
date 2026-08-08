"""
TRACEBIND Phase B2.2: ERA5 Acquisition & Quality Control (v1.6 - Final Corrected)
===================================================================================
Purpose: Acquire native 0.25° ERA5 u10/v10 spatial fields for the 300 
frozen target centers, strictly adhering to the Phase B2.2 Protocol v1.0.

Corrections in this revision:
- Fixed post-write validation meshgrid bug (native coords are already 2D).
- Validates all 300 cases in final artifact, not just a sample.
- Validates exact case ID, type, and timestamp ordering against frozen targets.
- Separates 'total_currently_failed' from 'failure_events_recorded' in audit.
- Validates entire 17x17 field for finite values, not just the shell.
- Uses explicit (case, y, x) dimensions in checkpoints (no artificial 'time' dim).
- Validates coordinate grid integrity (0.25° spacing) in checkpoints.
- Preserves actual ERA5 timestamp in checkpoint attributes.
"""

import cdsapi
import xarray as xr
import pandas as pd
import numpy as np
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone

# ============================================================================
# Configuration & Constants
# ============================================================================
PHASEB_DIR = Path(__file__).parent
TC_CSV = PHASEB_DIR / "selected_cohort_ids.csv"
CTRL_CSV = PHASEB_DIR / "selected_control_ids.csv"
B1_META_CSV = PHASEB_DIR / "b1_analysis_metadata.csv"
PROTOCOL_PATH = PHASEB_DIR / "PHASE_B2.2_ERA5_ACQUISITION_PROTOCOL.md"

CASE_DIR = PHASEB_DIR / "temp_cases"
CASE_DIR.mkdir(exist_ok=True)

OUTPUT_NC = PHASEB_DIR / "b2.2_era5_fields.nc"
OUTPUT_INDEX = PHASEB_DIR / "b2.2_target_index.csv"
OUTPUT_AUDIT = PHASEB_DIR / "b2.2_qc_audit.json"
OUTPUT_FAILURES = PHASEB_DIR / "b2.2_qc_failure_log.csv"

DATASET = "reanalysis-era5-single-levels"
DATASET_DOI = "10.24381/cds.adbb2d47"
VARIABLES = ["10m_u_component_of_wind", "10m_v_component_of_wind"]

LAT_MARGIN = 2.5
LON_MARGIN = 2.5
GRID_RADIUS = 8 # 17x17 window

MAX_RETRIES = 3
EARTH_RADIUS_KM = 6371.0088
PROTOCOL_VERSION = "B2.2-v1.6"

# ============================================================================
# Helper Functions
# ============================================================================
def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_git_hash():
    import subprocess
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, cwd=PHASEB_DIR.parent)
        return result.stdout.strip()
    except Exception:
        return "NOT_GIT_REPOSITORY"

def haversine_km(lat1, lon1, lat2, lon2):
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    return EARTH_RADIUS_KM * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def find_nearest_grid_idx(req_lat, req_lon, ds_lats, ds_lons):
    lons_grid, lats_grid = np.meshgrid(ds_lons, ds_lats)
    dists = haversine_km(req_lat, req_lon, lats_grid, lons_grid)
    min_idx = np.unravel_index(np.argmin(dists), dists.shape)
    return min_idx, float(ds_lats[min_idx[0]]), float(ds_lons[min_idx[1]])

def safe_delete(filepath):
    p = Path(filepath)
    if p.exists():
        try: p.unlink()
        except PermissionError:
            time.sleep(1.0)
            try: p.unlink()
            except Exception: pass

def validate_checkpoint(filepath, expected_id, expected_script_hash):
    """Validate a checkpoint file. Returns True if valid, False otherwise."""
    try:
        with xr.open_dataset(filepath) as ds:
            # Check provenance
            if ds.attrs.get("script_hash") != expected_script_hash: return False
            if ds.attrs.get("protocol_version") != PROTOCOL_VERSION: return False
            if ds.attrs.get("case_id") != expected_id: return False
            if "era5_timestamp" not in ds.attrs: return False
                
            # Check variables, dimensions and shapes
            if "u10" not in ds or "v10" not in ds: return False
            if "native_latitude" not in ds or "native_longitude" not in ds: return False
            
            if ds["u10"].dims != ("case", "y", "x"): return False
            if ds["v10"].dims != ("case", "y", "x"): return False
            if ds["native_latitude"].dims != ("y", "x"): return False
            if ds["native_longitude"].dims != ("y", "x"): return False
            
            if ds["u10"].shape != (1, 17, 17) or ds["v10"].shape != (1, 17, 17): return False
            if ds["native_latitude"].shape != (17, 17) or ds["native_longitude"].shape != (17, 17): return False
            
            # Check data integrity
            if not np.all(np.isfinite(ds["u10"].values)) or not np.all(np.isfinite(ds["v10"].values)): return False
            if not np.all(np.isfinite(ds["native_latitude"].values)) or not np.all(np.isfinite(ds["native_longitude"].values)): return False
            
            # Validate coordinate grid integrity (0.25° spacing)
            lat_grid = ds["native_latitude"].values
            lon_grid = ds["native_longitude"].values
            lat_step = np.diff(lat_grid[:, 0])
            lon_step = np.diff(lon_grid[0, :])
            if not np.allclose(np.abs(lat_step), 0.25, atol=1e-6): return False
            if not np.allclose(np.abs(lon_step), 0.25, atol=1e-6): return False
            
            return True
    except Exception:
        return False

# ============================================================================
# Main Execution
# ============================================================================
def run_acquisition():
    print("=" * 85)
    print("PHASE B2.2: ERA5 Acquisition & Quality Control (v1.6 - Final)")
    print("=" * 85)
    
    script_hash = compute_sha256(Path(__file__))
    
    # 1. Load Targets
    print("\n[1/7] Loading and validating frozen target coordinates...")
    tc_selected = pd.read_csv(TC_CSV)
    b1_meta = pd.read_csv(B1_META_CSV)
    tc_merged = tc_selected.merge(b1_meta[["SID", "analysis_lat", "analysis_lon", "analysis_time"]], on="SID", how="left", validate="one_to_one")
    if tc_merged["analysis_lat"].isna().any(): raise ValueError("Missing B1 metadata.")
    tc_df = tc_merged.rename(columns={"SID": "ID", "analysis_lat": "Latitude", "analysis_lon": "Longitude", "analysis_time": "Timestamp"})
    tc_df["Type"] = "TC"
    
    ctrl_df = pd.read_csv(CTRL_CSV)
    ctrl_df = ctrl_df[ctrl_df["Status"] == "Selected"].copy().rename(columns={"ControlID": "ID"})
    ctrl_df["Type"] = "Control"
    
    targets = pd.concat([tc_df[["ID", "Type", "Timestamp", "Latitude", "Longitude"]], ctrl_df[["ID", "Type", "Timestamp", "Latitude", "Longitude"]]], ignore_index=True)
    if len(targets) != 300: raise ValueError(f"Expected 300 targets, found {len(targets)}")
    
    targets["dt"] = pd.to_datetime(targets["Timestamp"], utc=True)
    targets["ERA5Timestamp"] = targets["dt"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    target_order = {id_val: idx for idx, id_val in enumerate(targets["ID"])}
    
    print(f"  → Target longitude range: {targets['Longitude'].min():.3f} to {targets['Longitude'].max():.3f}")
    print(f"  → Validated {len(targets)} frozen targets.")

    # 2. Pre-allocate Deterministic Arrays
    print("\n[2/7] Pre-allocating deterministic assembly arrays...")
    u10_data = np.full((300, 17, 17), np.nan)
    v10_data = np.full((300, 17, 17), np.nan)
    native_lat_data = np.full((300, 17, 17), np.nan)
    native_lon_data = np.full((300, 17, 17), np.nan)
    
    case_ids = np.empty(300, dtype=object)
    case_types = np.empty(300, dtype=object)
    case_timestamps = np.empty(300, dtype=object)
    req_lats = np.full(300, np.nan)
    req_lons = np.full(300, np.nan)
    grid_lats = np.full(300, np.nan)
    grid_lons = np.full(300, np.nan)

    # 3. Validate Existing Checkpoints & Load Failures
    print("\n[3/7] Validating existing checkpoints and loading failure log...")
    completed_ids = set()
    
    failures = []
    if OUTPUT_FAILURES.exists():
        fail_df = pd.read_csv(OUTPUT_FAILURES)
        failures = fail_df.to_dict('records')
        print(f"  → Loaded {len(failures)} existing failure event records.")
        
    for nc_file in CASE_DIR.glob("*.nc"):
        case_id = nc_file.stem
        if case_id not in target_order:
            safe_delete(nc_file)
            continue
            
        if validate_checkpoint(nc_file, case_id, script_hash):
            idx = target_order[case_id]
            with xr.open_dataset(nc_file) as ds:
                u10_data[idx] = ds["u10"].values[0]
                v10_data[idx] = ds["v10"].values[0]
                native_lat_data[idx] = ds["native_latitude"].values
                native_lon_data[idx] = ds["native_longitude"].values
                
                case_ids[idx] = ds.attrs["case_id"]
                case_types[idx] = ds.attrs["case_type"]
                case_timestamps[idx] = ds.attrs["requested_timestamp"]
                req_lats[idx] = ds.attrs["requested_latitude"]
                req_lons[idx] = ds.attrs["requested_longitude"]
                grid_lats[idx] = ds.attrs["center_grid_latitude"]
                grid_lons[idx] = ds.attrs["center_grid_longitude"]
                
            completed_ids.add(case_id)
        else:
            print(f"  ⚠️  Invalid/stale checkpoint found for {case_id}. Deleting and reacquiring.")
            safe_delete(nc_file)
            
    print(f"  → Validated {len(completed_ids)}/300 completed cases.")

    # 4. Acquisition Loop
    print("\n[4/7] Executing targeted CDS API requests (with checkpointing)...")
    client = cdsapi.Client()
    
    for idx, row in targets.iterrows():
        case_id = row["ID"]
        if case_id in completed_ids:
            continue
            
        req_lat, req_lon = float(row["Latitude"]), float(row["Longitude"])
        dt = row["dt"]
        year, month, day = str(dt.year), str(dt.month).zfill(2), str(dt.day).zfill(2)
        hour = str(dt.hour).zfill(2) + ":00"
        
        min_lat, max_lat = max(-90.0, req_lat - LAT_MARGIN), min(90.0, req_lat + LAT_MARGIN)
        min_lon, max_lon = max(-180.0, req_lon - LON_MARGIN), min(180.0, req_lon + LON_MARGIN)
        
        success = False
        last_error = ""
        for attempt in range(MAX_RETRIES):
            try:
                client.retrieve(DATASET, {"variable": VARIABLES, "year": year, "month": month, "day": day, "time": hour, "area": [max_lat, min_lon, min_lat, max_lon], "data_format": "netcdf"}, "temp.nc")
                success = True; break
            except Exception as e:
                last_error = str(e)
                time.sleep(2**attempt)
                
        if not success:
            print(f"   ❌ CDS FAILED for {case_id}")
            fail_rec = {"ID": case_id, "Type": row["Type"], "RequestedTimestamp": row["ERA5Timestamp"], "RequestedLat": req_lat, "RequestedLon": req_lon, "QC_Status": "FAILED", "FailureReason": f"CDS API Error: {last_error}"}
            failures.append(fail_rec)
            with open(OUTPUT_FAILURES, 'a', newline='') as f:
                pd.DataFrame([fail_rec]).to_csv(f, header=f.tell()==0, index=False)
            safe_delete("temp.nc"); continue
            
        try:
            with xr.open_dataset("temp.nc") as ds:
                time_var = "valid_time" if "valid_time" in ds.variables else "time"
                ds_time_val = ds[time_var].values[0]
                actual_era5_ts = str(pd.Timestamp(ds_time_val))
                
                if pd.Timestamp(row["dt"]).tz_convert(None) != pd.Timestamp(ds_time_val):
                    raise ValueError("Temporal mismatch")
                
                ds_lats, ds_lons = ds["latitude"].values, ds["longitude"].values
                (lat_idx, lon_idx), grid_lat, grid_lon = find_nearest_grid_idx(req_lat, req_lon, ds_lats, ds_lons)
                
                lat_start, lat_end = lat_idx - GRID_RADIUS, lat_idx + GRID_RADIUS + 1
                lon_start, lon_end = lon_idx - GRID_RADIUS, lon_idx + GRID_RADIUS + 1
                
                if lat_start < 0 or lat_end > len(ds_lats) or lon_start < 0 or lon_end > len(ds_lons):
                    raise ValueError("17x17 window exceeds bounds")
                    
                u10_window = ds["u10"].values[0, lat_start:lat_end, lon_start:lon_end]
                v10_window = ds["v10"].values[0, lat_start:lat_end, lon_start:lon_end]
                
                # Validate entire 17x17 field
                if not np.all(np.isfinite(u10_window)): raise ValueError("Non-finite u10 value in extracted 17x17 window")
                if not np.all(np.isfinite(v10_window)): raise ValueError("Non-finite v10 value in extracted 17x17 window")
                
                # QC ON FINAL 17x17 EXTRACTED WINDOW (Shell)
                slice_lats = ds_lats[lat_start:lat_end]
                slice_lons = ds_lons[lon_start:lon_end]
                lons_grid, lats_grid = np.meshgrid(slice_lons, slice_lats)
                dists = haversine_km(req_lat, req_lon, lats_grid, lons_grid)
                shell_mask = (dists >= 30.0) & (dists <= 150.0)
                
                if not np.any(shell_mask): raise ValueError("No shell points in extracted 17x17 window")
                if np.max(dists) < 150.0: raise ValueError(f"Extracted window too small. Max dist: {np.max(dists):.1f} km")
                    
                u10_shell = u10_window[shell_mask]
                v10_shell = v10_window[shell_mask]
                
                if not np.all(np.isfinite(u10_shell)) or not np.all(np.isfinite(v10_shell)):
                    raise ValueError("Non-finite values in shell")
                    
                if np.any(np.abs(u10_shell) > 100) or np.any(np.abs(v10_shell) > 100):
                    print(f"    ⚠️  WARNING: Wind speed anomaly for {case_id} (>|100| m/s). Flagged.")
                    
                # Create Checkpoint with explicit (case, y, x) dimensions
                case_ds = xr.Dataset(
                    {
                        "u10": (["case", "y", "x"], u10_window[np.newaxis, ...]),
                        "v10": (["case", "y", "x"], v10_window[np.newaxis, ...]),
                        "native_latitude": (["y", "x"], lats_grid),
                        "native_longitude": (["y", "x"], lons_grid)
                    },
                    coords={"case": [0], "y": np.arange(17), "x": np.arange(17)}
                )
                case_ds.attrs = {
                    "case_id": case_id, "case_type": row["Type"], "requested_timestamp": row["ERA5Timestamp"],
                    "era5_timestamp": actual_era5_ts,
                    "requested_latitude": req_lat, "requested_longitude": req_lon,
                    "center_grid_latitude": grid_lat, "center_grid_longitude": grid_lon,
                    "script_hash": script_hash, "protocol_version": PROTOCOL_VERSION
                }
                
                case_ds.to_netcdf(CASE_DIR / f"{case_id}.nc")
                
                # Fill Pre-allocated Arrays
                u10_data[idx] = u10_window
                v10_data[idx] = v10_window
                native_lat_data[idx] = lats_grid
                native_lon_data[idx] = lons_grid
                case_ids[idx] = case_id
                case_types[idx] = row["Type"]
                case_timestamps[idx] = row["ERA5Timestamp"]
                req_lats[idx] = req_lat
                req_lons[idx] = req_lon
                grid_lats[idx] = grid_lat
                grid_lons[idx] = grid_lon
                
                completed_ids.add(case_id)
                print(f"  ✓ Processed {case_id} ({len(completed_ids)}/300)")
                
        except Exception as e:
            print(f"  ❌ QC FAILED for {case_id}: {str(e)}")
            fail_rec = {"ID": case_id, "Type": row["Type"], "RequestedTimestamp": row["ERA5Timestamp"], "RequestedLat": req_lat, "RequestedLon": req_lon, "QC_Status": "FAILED", "FailureReason": str(e)}
            failures.append(fail_rec)
            with open(OUTPUT_FAILURES, 'a', newline='') as f:
                pd.DataFrame([fail_rec]).to_csv(f, header=f.tell()==0, index=False)
        finally:
            safe_delete("temp.nc")

    # 5. Deterministic Assembly & Write
    print("\n[5/7] Assembling final NetCDF artifact deterministically...")
    if len(completed_ids) == 300:
        final_ds = xr.Dataset(
            {
                "u10": (["case", "y", "x"], u10_data),
                "v10": (["case", "y", "x"], v10_data),
                "native_latitude": (["case", "y", "x"], native_lat_data),
                "native_longitude": (["case", "y", "x"], native_lon_data)
            },
            coords={
                "case": range(300),
                "y": range(17),
                "x": range(17),
                "case_id": ("case", case_ids),
                "case_type": ("case", case_types),
                "case_timestamp": ("case", case_timestamps),
                "requested_latitude": ("case", req_lats),
                "requested_longitude": ("case", req_lons),
                "center_grid_latitude": ("case", grid_lats),
                "center_grid_longitude": ("case", grid_lons)
            }
        )
        final_ds.to_netcdf(OUTPUT_NC)
        print(f"  → Saved primary artifact: {OUTPUT_NC.name}")
    else:
        print(f"  ⚠️  Only {len(completed_ids)}/300 cases completed. Primary artifact not written.")

    # 6. Post-Write Validation (All 300 cases)
    print("\n[6/7] Performing comprehensive post-write validation on final artifact...")
    artifact_valid = False
    if OUTPUT_NC.exists() and len(completed_ids) == 300:
        try:
            with xr.open_dataset(OUTPUT_NC) as val_ds:
                assert val_ds["u10"].shape == (300, 17, 17), "Shape mismatch u10"
                assert val_ds["v10"].shape == (300, 17, 17), "Shape mismatch v10"
                
                # Validate exact ordering
                expected_ids = targets["ID"].astype(str).to_numpy()
                actual_ids = val_ds["case_id"].values.astype(str)
                assert np.array_equal(actual_ids, expected_ids), "Case ID ordering mismatch"
                
                expected_types = targets["Type"].astype(str).to_numpy()
                actual_types = val_ds["case_type"].values.astype(str)
                assert np.array_equal(actual_types, expected_types), "Case type ordering mismatch"
                
                expected_times = targets["ERA5Timestamp"].astype(str).to_numpy()
                actual_times = val_ds["case_timestamp"].values.astype(str)
                assert np.array_equal(actual_times, expected_times), "Case timestamp ordering mismatch"
                
                # Validate all 300 cases
                for c_idx in range(300):
                    c_lat = val_ds["requested_latitude"].values[c_idx]
                    c_lon = val_ds["requested_longitude"].values[c_idx]
                    n_lats = val_ds["native_latitude"].values[c_idx]
                    n_lons = val_ds["native_longitude"].values[c_idx]
                    
                    # Native coords are already 2D, no meshgrid needed
                    dists = haversine_km(c_lat, c_lon, n_lats, n_lons)
                    shell_mask = (dists >= 30.0) & (dists <= 150.0)
                    
                    assert np.any(shell_mask), f"No shell points in case {c_idx}"
                    assert np.max(dists) >= 150.0, f"Window does not reach 150 km in case {c_idx}"
                    
                    u10_s = val_ds["u10"].values[c_idx][shell_mask]
                    v10_s = val_ds["v10"].values[c_idx][shell_mask]
                    assert np.all(np.isfinite(u10_s)), f"Non-finite u10 values in case {c_idx} shell"
                    assert np.all(np.isfinite(v10_s)), f"Non-finite v10 values in case {c_idx} shell"
                    
            artifact_valid = True
            print("  ✅ Post-write validation passed for all 300 cases.")
        except Exception as e:
            print(f"  ❌ Post-write validation FAILED: {str(e)}")

    # 7. Audit Manifest
    print("\n[7/7] Generating cryptographic audit manifest...")
    successful_count = len(completed_ids)
    current_failed_count = 300 - successful_count
    
    audit_data = {
        "dataset_identifier": DATASET, "dataset_doi": DATASET_DOI, "variables": VARIABLES,
        "grid_resolution": "0.25 x 0.25 degrees", "extraction_window": "17x17 native cells",
        "freeze_fingerprint": {"protocol_sha256": compute_sha256(PROTOCOL_PATH), "script_sha256": script_hash, "git_commit_hash": get_git_hash(), "execution_timestamp_utc": datetime.now(timezone.utc).isoformat()},
        "input_hashes": {"tc_csv_sha256": compute_sha256(TC_CSV), "b1_meta_csv_sha256": compute_sha256(B1_META_CSV), "control_csv_sha256": compute_sha256(CTRL_CSV)},
        "output_hashes": {"era5_fields_nc_sha256": compute_sha256(OUTPUT_NC) if (OUTPUT_NC.exists() and artifact_valid) else None},
        "summary_statistics": {
            "total_requested": 300, 
            "total_successful": successful_count, 
            "total_currently_failed": current_failed_count,
            "failure_events_recorded": len(failures)
        },
        "failure_log_semantics": "append-only failure event log; repeated failures across resumptions produce multiple records"
    }
    with open(OUTPUT_AUDIT, 'w') as f: json.dump(audit_data, f, indent=2)
    
    print("\n" + "=" * 85)
    if len(completed_ids) == 300 and artifact_valid:
        print("✅ Phase B2.2 Acquisition is 100% COMPLETE and VALIDATED. Ready for Phase B3.")
    else:
        print(f"⚠️  Completed {len(completed_ids)}/300. Rerun script to resume remaining cases.")
    print("=" * 85)

if __name__ == "__main__":
    run_acquisition()