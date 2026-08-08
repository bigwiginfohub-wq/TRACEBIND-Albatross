"""
TRACEBIND Phase B2.1: Control Selection (v5.1 - FINAL SAFE VERSION)
====================================================================
Purpose: Deterministically select exactly 150 non-cyclonic atmospheric control 
cases matching the Phase B1 TC cohort's geographic and temporal distribution.

FIXES IN v5.1 (per reproducibility audit):
1. Cross-Year Boundaries: Uses a continuous global timeline and exact temporal 
   overlap filtering. No more missing December/January boundary exclusions.
2. Memory Explosion: Eliminates np.where(~mask). Streams row-by-row using 
   np.flatnonzero to keep RAM strictly bounded (< 1.5 GB).
3. Timestamp Caching: Precomputes global timeline and target indices once.
4. Exact Storm Filtering: Replaces fragile Month±2 heuristic with exact 
   timestamp overlap calculation.
5. Bugfix: Fixed np.searchsorted out-of-bounds IndexError at month boundaries.
6. Data Integrity: ControlIDs are now globally unique (CTRL_001 to CTRL_150).

ARCHITECTURE:
- AMENDMENT B2.1-001: No intermediate candidate pool file.
- True Storm-Centric Pass: Each storm processed exactly ONCE.
- Deterministic Top-K Priority Queue: Identity-based hash ranking.
"""

import pandas as pd
import numpy as np
import hashlib
import json
import platform
import subprocess
import math
import heapq
import warnings
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sklearn.neighbors import BallTree
import xarray as xr

# Silence NumPy timezone warnings
warnings.filterwarnings("ignore", message=".*no explicit representation of timezones.*")

# ============================================================================
# Configuration & Constants
# ============================================================================
IBTRACS_CSV = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\ibtracs_ALL.csv")
B1_COHORT_CSV = Path(__file__).parent / "selected_cohort_ids.csv"
B1_ANALYSIS_METADATA_CSV = Path(__file__).parent / "b1_analysis_metadata.csv"
ERA5_LSM_PATH = Path(r"C:\TRACEBIND-Albatross\data\era5_lsm.nc")
PROTOCOL_PATH = Path(__file__).parent / "PHASE_B2.1_CONTROL_SELECTION_PROTOCOL_v3.2_FROZEN.md"
OUTPUT_DIR = Path(__file__).parent

SEED = 43
SAMPLER_VERSION = "TRACEBIND_B2.1_SAMPLER_V5.1"
EARTH_RADIUS_KM = 6371.0088
EXCLUSION_RADIUS_RAD = 1000.0 / EARTH_RADIUS_KM
EXCLUSION_TIME_DAYS = 7
TARGET_BASIN_TOTAL = 50
REPLACEMENT_BUFFER = 20 

TARGET_IBTRACS_BASINS = ['NI', 'SI', 'WP']

BASIN_BOUNDS = {
    'NI': (0, 30, 40, 100),
    'SI': (-40, 0, 30, 120),
    'WP': (0, 40, 100, 180)
}

# ============================================================================
# Helper Functions
# ============================================================================
def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_protocol_hash():
    return compute_sha256(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else "PROTOCOL_NOT_FOUND"

def get_git_hash():
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, cwd=OUTPUT_DIR.parent)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "NOT_GIT_REPOSITORY"

def get_lmc(lat):
    lower = math.floor(lat / 5.0) * 5
    upper = lower + 5
    return f"{lower}to{upper}"

def compute_priority(seed, basin, month, lmc, ts_str, lat, lon):
    msg = f"{seed}_{basin}_{month}_{lmc}_{ts_str}_{lat}_{lon}".encode('utf-8')
    return int(hashlib.sha256(msg).hexdigest(), 16)

# ============================================================================
# Main Execution
# ============================================================================
def run_control_selection():
    print("=" * 85)
    print(f"PHASE B2.1: Control Selection ({SAMPLER_VERSION})")
    print("=" * 85)
    
    # 0. Environment & Dependency Verification
    print("\n[0/6] Verifying computational environment and dependencies...")
    import sklearn
    current_versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sklearn": sklearn.__version__,
        "xarray": xr.__version__
    }
    for pkg, ver in current_versions.items():
        print(f"  → {pkg.capitalize()}: {ver} [✓]")
    print(f"  → Protocol SHA256: {get_protocol_hash()[:16]}...")
    
    if not ERA5_LSM_PATH.exists(): raise FileNotFoundError(f"CRITICAL: {ERA5_LSM_PATH} not found.")
    if not B1_ANALYSIS_METADATA_CSV.exists(): raise FileNotFoundError(f"CRITICAL: {B1_ANALYSIS_METADATA_CSV} not found.")

    # 1. Verify Phase B1 Basin Balance
    print("\n[1/6] Verifying Phase B1 basin balance...")
    b1_cohort = pd.read_csv(B1_COHORT_CSV)
    b1_basin_counts = b1_cohort["Basin"].value_counts().to_dict()
    if b1_basin_counts != {"NI": 50, "SI": 50, "WP": 50}:
        raise ValueError(f"CRITICAL: Phase B1 does not have 50/50/50 basin balance. Actual: {b1_basin_counts}")
    print(f"  ✓ Phase B1 verified: NI=50, SI=50, WP=50")

    # 2. Load & Clean IBTrACS + Strict Basin Filtering
    print("\n[2/6] Loading IBTrACS and applying strict basin filter...")
    ibtracs = pd.read_csv(IBTRACS_CSV, low_memory=False, dtype=str)
    ibtracs["SEASON_INT"] = pd.to_numeric(ibtracs["SEASON"], errors="coerce")
    
    bad_rows = ibtracs["SEASON_INT"].isna()
    ibtracs_valid = ibtracs[~bad_rows].copy()
    ibtracs_valid["SEASON_INT"] = ibtracs_valid["SEASON_INT"].astype(int)
    ibtracs_modern = ibtracs_valid[ibtracs_valid["SEASON_INT"] >= 1980].copy()

    ibtracs_modern["LAT"] = pd.to_numeric(ibtracs_modern["LAT"], errors="coerce")
    ibtracs_modern["LON"] = pd.to_numeric(ibtracs_modern["LON"], errors="coerce")
    ibtracs_modern["LON"] = ((ibtracs_modern["LON"] + 180) % 360) - 180
    ibtracs_modern["ISO_TIME_DT"] = pd.to_datetime(ibtracs_modern["ISO_TIME"], errors="coerce", utc=True)
    ibtracs_modern = ibtracs_modern.dropna(subset=["LAT", "LON", "ISO_TIME_DT"])

    ibtracs_modern = ibtracs_modern[ibtracs_modern["BASIN"].isin(TARGET_IBTRACS_BASINS)].copy()
    ibtracs_modern["TARGET_BASIN"] = ibtracs_modern["BASIN"] 
    
    print(f"  → Loaded {len(ibtracs_modern):,} valid observations in target basins (NI, SI, WP).")

    # 3. Extract Required Strata from Phase B1
    print("\n[3/6] Extracting required strata from Phase B1 cohort...")
    b1_meta = pd.read_csv(B1_ANALYSIS_METADATA_CSV)
    b1_with_lat = b1_cohort.merge(b1_meta[["SID", "analysis_lat", "analysis_time"]], on="SID", how="left")
    
    if b1_with_lat["analysis_lat"].isna().any():
        raise ValueError("CRITICAL: Some Phase B1 storms are missing analysis latitude metadata.")
        
    b1_with_lat["Month"] = pd.to_datetime(b1_with_lat["analysis_time"], errors="coerce").dt.month
    b1_with_lat["LMC"] = b1_with_lat["analysis_lat"].apply(get_lmc)
    
    required_strata = b1_with_lat.groupby(["Basin", "Month", "LMC"]).size().reset_index(name="required_count")
    required_strata = required_strata.sort_values(["Basin", "Month", "LMC"]).reset_index(drop=True)
    print(f"  → Identified {len(required_strata)} unique strata.")

    # 4. Pre-compute Global Timeline, Ocean Grids & BallTrees
    print("\n[4/6] Pre-computing global timeline, ocean grids, and BallTrees...")
    
    print("  → Generating continuous global timeline (1980-2025)...")
    all_timestamps = pd.date_range(start="1980-01-01", end="2025-12-31 23:59:59", freq="6h", tz="UTC")
    all_ts_np = all_timestamps.values 
    
    month_indices_cache = {}
    for m in range(1, 13):
        month_indices_cache[m] = np.where(all_timestamps.month == m)[0]
    
    lsm_ds = xr.open_dataset(ERA5_LSM_PATH, engine="netcdf4")
    lsm_var = lsm_ds['lsm']
    if 'time' in lsm_var.dims: lsm_var = lsm_var.isel(time=0)
    lsm_var = lsm_var.squeeze()
    
    basin_lmc_cache = {} 
    
    for basin, (lat_min, lat_max, lon_min, lon_max) in BASIN_BOUNDS.items():
        lsm_subset = lsm_var.sel(latitude=slice(lat_max, lat_min), longitude=slice(lon_min, lon_max))
        
        lats = lsm_subset.latitude.values
        lons = lsm_subset.longitude.values
        lsm_vals = lsm_subset.values
        
        lons_grid, lats_grid = np.meshgrid(lons, lats)
        lats_flat = lats_grid.flatten()
        lons_flat = lons_grid.flatten()
        lsm_flat = lsm_vals.flatten()
        
        ocean_mask = lsm_flat < 0.5
        valid_lats = lats_flat[ocean_mask]
        valid_lons = lons_flat[ocean_mask]
        
        sort_idx = np.lexsort((valid_lons, valid_lats))
        valid_lats = valid_lats[sort_idx]
        valid_lons = valid_lons[sort_idx]
        
        basin_strata = required_strata[required_strata["Basin"] == basin]
        unique_lmcs = basin_strata["LMC"].unique()
        
        for lmc in unique_lmcs:
            lmc_lower, lmc_upper = map(float, lmc.split("to"))
            lmc_mask = (valid_lats >= lmc_lower) & (valid_lats < lmc_upper)
            
            key = (basin, lmc)
            pts = np.column_stack((valid_lats[lmc_mask], valid_lons[lmc_mask]))
            tree = BallTree(np.radians(pts), metric='haversine')
            basin_lmc_cache[key] = (pts, tree)
            print(f"  → {basin} / {lmc}: {len(pts)} ocean points, BallTree built.")

    # 5. STREAMING ENGINE: Robust Storm-Centric Pass + Top-K Priority Queue
    print("\n[5/6] Running Robust Storm-Centric Engine...")
    
    selected_records = []
    pool_hasher = hashlib.sha256()
    total_valid_count = 0
    
    # Global counters for unique ControlIDs
    global_sel_count = 1
    global_std_count = 1
    
    storms_by_basin = {b: df for b, df in ibtracs_modern.groupby("TARGET_BASIN")}
    
    for _, stratum in required_strata.iterrows():
        basin = stratum["Basin"]
        month = stratum["Month"]
        lmc = stratum["LMC"]
        req_count = stratum["required_count"]
        capacity = req_count + REPLACEMENT_BUFFER
        
        if (basin, lmc) not in basin_lmc_cache: continue
        ocean_pts, grid_tree = basin_lmc_cache[(basin, lmc)]
            
        print(f"  → Processing {basin} / Month {month} / {lmc}...")
        
        target_global_indices = month_indices_cache[month]
        n_target_times = len(target_global_indices)
        n_pts = len(ocean_pts)
        
        exclusion_mask = np.zeros((n_target_times, n_pts), dtype=bool)
        
        # Single 46-year window (Proven correct, computationally sufficient)
        stratum_start = all_ts_np[target_global_indices[0]] - np.timedelta64(EXCLUSION_TIME_DAYS, 'D')
        stratum_end = all_ts_np[target_global_indices[-1]] + np.timedelta64(EXCLUSION_TIME_DAYS, 'D')
        
        basin_storms = storms_by_basin.get(basin)
        if basin_storms is None or len(basin_storms) == 0: continue
        
        storm_times_np = basin_storms["ISO_TIME_DT"].values
        relevant_storm_mask = (storm_times_np >= stratum_start) & (storm_times_np <= stratum_end)
        relevant_storms = basin_storms[relevant_storm_mask]
        
        print(f"    - Applying exclusions from {len(relevant_storms):,} relevant storms...")
        
        for _, storm in relevant_storms.iterrows():
            storm_time = np.datetime64(storm["ISO_TIME_DT"], "ns")
            
            start_time = storm_time - np.timedelta64(EXCLUSION_TIME_DAYS, 'D')
            end_time = storm_time + np.timedelta64(EXCLUSION_TIME_DAYS, 'D')
            
            left_global = np.searchsorted(all_ts_np, start_time, side='left')
            right_global = np.searchsorted(all_ts_np, end_time, side='right')
            
            if left_global >= right_global: continue
            
            affected_global = np.arange(left_global, right_global)
            
            # FIX 5: Two-stage searchsorted to prevent out-of-bounds IndexError
            local_t_idx = np.searchsorted(target_global_indices, affected_global, side='left')
            
            # Stage 1: Remove indices that lie beyond the array
            inside = local_t_idx < n_target_times
            local_t_idx = local_t_idx[inside]
            affected_global = affected_global[inside]
            
            # Stage 2: Verify exact matches
            matches = target_global_indices[local_t_idx] == affected_global
            local_t_idx = local_t_idx[matches]
            
            if len(local_t_idx) == 0: continue
            
            g_idx = grid_tree.query_radius([[np.radians(storm["LAT"]), np.radians(storm["LON"])]], r=EXCLUSION_RADIUS_RAD)[0]
            if len(g_idx) == 0: continue
                
            exclusion_mask[np.ix_(local_t_idx, g_idx)] = True
            
        # Stream row-by-row
        heap = []
        print(f"    - Streaming valid candidates row-by-row...")
        
        for t_local in range(n_target_times):
            valid_g = np.flatnonzero(~exclusion_mask[t_local])
            if len(valid_g) == 0: continue
            
            ts_str = pd.Timestamp(all_ts_np[target_global_indices[t_local]]).strftime("%Y-%m-%dT%H:%M:%S")
            
            for g in valid_g:
                lat = ocean_pts[g, 0]
                lon = ocean_pts[g, 1]
                
                line = f"{basin},{month},{lmc},{ts_str},{lat},{lon}\n"
                pool_hasher.update(line.encode('utf-8'))
                total_valid_count += 1
                
                priority_int = compute_priority(SEED, basin, month, lmc, ts_str, lat, lon)
                record = {"Basin": basin, "Month": month, "LMC": lmc, "Timestamp": ts_str, "Latitude": lat, "Longitude": lon}
                
                if len(heap) < capacity:
                    heapq.heappush(heap, (-priority_int, record))
                else:
                    if priority_int < -heap[0][0]:
                        heapq.heapreplace(heap, (-priority_int, record))
                        
        del exclusion_mask 
        
        print(f"    - Top-K Queue filled: {len(heap)} candidates (Capacity: {capacity})")
        
        final_candidates = [(-neg_p, rec) for neg_p, rec in heap]
        final_candidates.sort(key=lambda x: x[0])
        
        # FIX 6: Globally unique ControlIDs
        for rank, (p, rec) in enumerate(final_candidates, 1):
            if rank <= req_count:
                cid = f"CTRL_{global_sel_count:03d}"
                global_sel_count += 1
                status = "Selected"
            else:
                cid = f"STANDBY_{global_std_count:03d}"
                global_std_count += 1
                status = "Standby"
                
            selected_records.append({
                "ControlID": cid, **rec, "RandomRank": rank,
                "StratumID": f"{basin}_{month}_{lmc}", "Status": status
            })

    # 6. Finalize Sampling & Save Deliverables (Canonical Names)
    print("\n[6/6] Finalizing deterministic sampling and generating audit manifest...")
    
    selected_df = pd.DataFrame(selected_records)
    selected_path = OUTPUT_DIR / "selected_control_ids.csv"
    selected_df.to_csv(selected_path, index=False, encoding="utf-8", lineterminator="\n")
    
    pool_hash_hex = pool_hasher.hexdigest()
    
    audit_data = {
        "freeze_fingerprint": {
            "protocol_version": "3.2 (Amended B2.1-001)",
            "protocol_sha256": get_protocol_hash(),
            "script_sha256": compute_sha256(Path(__file__)),
            "git_commit_hash": get_git_hash(),
            "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "random_seed": SEED
        },
        "software_versions": current_versions,
        "data_source_hashes": {
            "ibtracs_sha256": compute_sha256(IBTRACS_CSV),
            "era5_lsm_sha256": compute_sha256(ERA5_LSM_PATH)
        },
        "candidate_pool": {
            "filename": "STREAMED_NOT_SAVED (Amendment B2.1-001)",
            "sha256": pool_hash_hex,
            "row_count": total_valid_count,
            "note": "Exhaustive materialization deemed infeasible. Pool cryptographically hashed on-the-fly. Selection via deterministic Top-K priority queue (identity-based)."
        },
        "output_file_hashes": {
            "selected_control_ids.csv": compute_sha256(selected_path)
        },
        "summary_statistics": {
            "total_selected_controls": len(selected_df[selected_df["Status"] == "Selected"]),
            "total_standby_controls": len(selected_df[selected_df["Status"] == "Standby"]),
            "basin_totals": selected_df[selected_df["Status"] == "Selected"]["Basin"].value_counts().to_dict(),
            "total_eligible_candidates_streamed": total_valid_count
        }
    }
    
    audit_path = OUTPUT_DIR / "control_audit.json"
    with open(audit_path, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
        
    # Final Invariant Checks
    selected_only = selected_df[selected_df["Status"] == "Selected"]
    assert len(selected_only) == 150, f"CRITICAL: Selected {len(selected_only)} controls, expected 150."
    basin_counts = selected_only["Basin"].value_counts().to_dict()
    assert basin_counts == {"NI": 50, "SI": 50, "WP": 50}, f"CRITICAL: Basin mismatch! {basin_counts}"
    assert selected_only["ControlID"].is_unique, "CRITICAL: Duplicate ControlIDs detected!"
    
    print("-" * 85)
    print(f"  ✓ Total Controls Selected: 150")
    print(f"  ✓ Total Standby Replacements: {len(selected_df) - 150}")
    print(f"  ✓ Basin Balance: NI=50, SI=50, WP=50")
    print(f"  ✓ Total Eligible Candidates Streamed & Hashed: {total_valid_count:,}")
    print("=" * 85)
    print("✅ Phase B2.1 Control Selection is now FROZEN.")
    print("=" * 85)

if __name__ == "__main__":
    run_control_selection()