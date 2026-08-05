"""
TRACEBIND Phase B2.1: Control Selection (v2.1 - CORRECTED)
===========================================================
Purpose: Deterministically select exactly 150 non-cyclonic atmospheric control 
cases from the actual ERA5 ocean grid, matching the Phase B1 TC cohort's 
geographic and temporal distribution.

FIX: Retrieve TC genesis timestamps from IBTrACS instead of relying on missing column.
"""

import pandas as pd
import numpy as np
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scipy.spatial import cKDTree

# ============================================================================
# Configuration & Constants
# ============================================================================
IBTRACS_CSV = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\ibtracs_ALL.csv")
B1_COHORT_CSV = Path(__file__).parent / "selected_cohort_ids.csv"
PROTOCOL_PATH = Path(__file__).parent / "PHASE_B2.1_CONTROL_SELECTION_PROTOCOL.md"
OUTPUT_DIR = Path(__file__).parent

SEED = 43
SAMPLER_VERSION = "TRACEBIND_B2.1_SAMPLER_V2.1_FIXED"
EXCLUSION_RADIUS_KM = 1000.0
EXCLUSION_TIME_DAYS = 7
LAND_EXCLUSION_KM = 100.0
TARGET_BASIN_TOTAL = 50
CANDIDATE_GRID_RES = 1.0

FROZEN_VERSIONS = {
    "python": "3.14.4",
    "numpy": "2.4.6",
    "pandas": "3.0.5"
}

BASIN_BOUNDS = {
    'NI': (0, 30, 40, 100),
    'SI': (-40, 0, 30, 120),
    'WP': (0, 40, 100, 180)
}

# Dense Land Point Grid (Every 2 degrees)
LAND_POINTS = []
for lat in np.arange(5, 55, 2):
    for lon in np.arange(65, 150, 2):
        LAND_POINTS.append((lat, lon))
for lat in np.arange(-35, 15, 2):
    for lon in np.arange(10, 55, 2):
        LAND_POINTS.append((lat, lon))
for lat in np.arange(-40, 5, 2):
    for lon in np.arange(95, 160, 2):
        LAND_POINTS.append((lat, lon))
for lat in np.arange(10, 35, 2):
    for lon in np.arange(35, 65, 2):
        LAND_POINTS.append((lat, lon))

LAND_TREE = cKDTree(LAND_POINTS)

# ============================================================================
# Helper Functions
# ============================================================================
def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_script_hash(): return compute_sha256(Path(__file__))
def get_protocol_hash(): return compute_sha256(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else "PROTOCOL_NOT_FOUND"
def get_git_hash():
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, cwd=OUTPUT_DIR.parent)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "NOT_GIT_REPOSITORY"

# ============================================================================
# Main Execution
# ============================================================================
def run_control_selection():
    print("=" * 85)
    print(f"PHASE B2.1: Control Selection ({SAMPLER_VERSION})")
    print("=" * 85)
    
    # 0. Environment & Protocol Verification
    print("\n[0/7] Verifying environment and protocol...")
    current_versions = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    for pkg, frozen_ver in FROZEN_VERSIONS.items():
        if current_versions[pkg] != frozen_ver: raise RuntimeError(f"CRITICAL: Environment mismatch for {pkg}.")
        print(f"  → {pkg.capitalize()}: {current_versions[pkg]} [✓]")
    print(f"  → Protocol SHA256: {get_protocol_hash()[:16]}...")

    # 1. Load Phase B1 Cohort & Retrieve Genesis Timestamps from IBTrACS
    print("\n[1/7] Loading Phase B1 cohort and retrieving genesis timestamps...")
    b1_cohort = pd.read_csv(B1_COHORT_CSV)
    
    # Load IBTrACS to get genesis times
    ibtracs_full = pd.read_csv(IBTRACS_CSV, low_memory=False, dtype={'SEASON': str})
    ibtracs_full['ISO_TIME_DT'] = pd.to_datetime(ibtracs_full['ISO_TIME'], errors='coerce')
    
    # Get first timestamp (genesis) for each SID
    genesis_times = ibtracs_full.groupby('SID')['ISO_TIME_DT'].min().reset_index()
    genesis_times.columns = ['SID', 'genesis_time']
    
    # Merge with B1 cohort
    b1_with_time = b1_cohort.merge(genesis_times, on='SID', how='left')
    b1_with_time['month'] = b1_with_time['genesis_time'].dt.month
    
    required_distribution = b1_with_time.groupby(['Basin', 'month']).size().reset_index(name='required_count')
    print(f"  → B1 Cohort: {len(b1_cohort)} TCs. Required strata: {len(required_distribution)}.")

    # 2. Load IBTrACS Exclusion Zone Data (1980-Present)
    print("\n[2/7] Loading IBTrACS exclusion zone data...")
    ibtracs_modern = ibtracs_full[ibtracs_full['SEASON'].astype(int) >= 1980].copy()
    ibtracs_modern = ibtracs_modern.dropna(subset=['LAT', 'LON', 'ISO_TIME_DT'])
    
    ib_coords = np.column_stack((ibtracs_modern['LAT'].values, ibtracs_modern['LON'].values))
    ib_times = ibtracs_modern['ISO_TIME_DT'].values
    ib_sids = ibtracs_modern['SID'].values
    
    ib_tree = cKDTree(ib_coords)
    print(f"  → Loaded {len(ibtracs_modern):,} IBTrACS points. KDTree built.")

    # 3. Generate Candidate Grid & Timestamps
    print("\n[3/7] Generating candidate pool (1° grid, all 6-hourly times)...")
    
    all_valid_candidates = []
    all_filter_logs = []
    
    basin_grids = {}
    for basin, (lat_min, lat_max, lon_min, lon_max) in BASIN_BOUNDS.items():
        lats = np.arange(lat_min, lat_max + 1, CANDIDATE_GRID_RES)
        lons = np.arange(lon_min, lon_max + 1, CANDIDATE_GRID_RES)
        grid_points = [(lat, lon) for lat in lats for lon in lons if LAND_TREE.query((lat, lon))[0] > LAND_EXCLUSION_KM]
        basin_grids[basin] = np.array(grid_points)
        print(f"  → {basin}: {len(grid_points)} valid ocean grid points.")

    for year in range(1980, 2026):
        for basin, grid_points in basin_grids.items():
            if len(grid_points) == 0: continue
            
            req_months = required_distribution[required_distribution['Basin'] == basin]['month'].unique()
            
            for month in req_months:
                days_in_month = pd.Timestamp(year=year, month=month, day=1).days_in_month
                timestamps = []
                for day in range(1, days_in_month + 1):
                    for hour in [0, 6, 12, 18]:
                        timestamps.append(datetime(year, month, day, hour))
                timestamps = np.array(timestamps)
                
                # Vectorized spatial query
                dists, indices = ib_tree.query(grid_points, k=50, distance_upper_bound=EXCLUSION_RADIUS_KM / 6371.0 * 180 / np.pi)
                
                for i, (lat, lon) in enumerate(grid_points):
                    valid_indices = indices[i][indices[i] < len(ib_times)]
                    if len(valid_indices) == 0:
                        for t in timestamps:
                            all_valid_candidates.append({'Basin': basin, 'Lat': lat, 'Lon': lon, 'Timestamp': t})
                        continue
                        
                    nearby_times = ib_times[valid_indices]
                    
                    for t in timestamps:
                        time_diffs = np.abs((t - nearby_times).astype('timedelta64[D]').astype(float))
                        min_time_diff = time_diffs.min()
                        
                        if min_time_diff < EXCLUSION_TIME_DAYS:
                            all_filter_logs.append({
                                'Basin': basin, 'Lat': lat, 'Lon': lon, 'Year': year, 'Month': month,
                                'RejectionReason': 'Temporal Exclusion (<7 days)',
                                'NearestTimeDiffDays': min_time_diff
                            })
                        else:
                            all_valid_candidates.append({'Basin': basin, 'Lat': lat, 'Lon': lon, 'Timestamp': t})

    print(f"  → Total valid candidates after exclusion: {len(all_valid_candidates):,}")
    print(f"  → Rejected candidates: {len(all_filter_logs):,}")

    # 4. Stratified Random Sampling
    print("\n[4/7] Executing stratified random sampling (seed=43)...")
    rng = np.random.default_rng(SEED)
    
    cand_df = pd.DataFrame(all_valid_candidates)
    cand_df['Month'] = cand_df['Timestamp'].dt.month
    cand_df['Year'] = cand_df['Timestamp'].dt.year
    cand_df['Hour'] = cand_df['Timestamp'].dt.hour
    
    selected_records = []
    randomized_order_records = []
    
    for _, row in required_distribution.iterrows():
        basin, month, count = row['Basin'], row['month'], row['required_count']
        stratum = cand_df[(cand_df['Basin'] == basin) & (cand_df['Month'] == month)]
        
        if len(stratum) < count:
            raise RuntimeError(f"CRITICAL: Insufficient candidates for Basin={basin}, Month={month}.")
            
        shuffled_indices = stratum.index.tolist()
        rng.shuffle(shuffled_indices)
        
        for rank, idx in enumerate(shuffled_indices, start=1):
            c = cand_df.loc[idx]
            randomized_order_records.append({
                'Basin': c['Basin'], 'Month': c['Month'], 'RandomRank': rank,
                'Lat': c['Lat'], 'Lon': c['Lon'], 'Year': c['Year'], 'Hour': c['Hour'],
                'Timestamp': c['Timestamp'].strftime('%Y-%m-%dT%H:%M:%S'),
                'Status': 'Selected' if rank <= count else 'Standby (Replacement)'
            })
            
        for rank, idx in enumerate(shuffled_indices[:count], start=1):
            c = cand_df.loc[idx]
            selected_records.append({
                'Type': 'CONTROL', 'Basin': c['Basin'], 'Month': c['Month'],
                'Lat': c['Lat'], 'Lon': c['Lon'], 'Year': c['Year'], 'Hour': c['Hour'],
                'Timestamp': c['Timestamp'].strftime('%Y-%m-%dT%H:%M:%S'), 'RandomRank': rank
            })

    # 5. Save Deliverables
    print("\n[5/7] Saving deliverables...")
    selected_df = pd.DataFrame(selected_records)
    selected_path = OUTPUT_DIR / "selected_control_ids.csv"
    selected_df.to_csv(selected_path, index=False)
    
    rand_order_df = pd.DataFrame(randomized_order_records)
    rand_order_path = OUTPUT_DIR / "control_randomized_order.csv"
    rand_order_df.to_csv(rand_order_path, index=False)
    
    filter_log_df = pd.DataFrame(all_filter_logs)
    filter_log_path = OUTPUT_DIR / "control_candidate_filter_log.csv"
    filter_log_df.to_csv(filter_log_path, index=False)
    
    # 6. Generate Audit Manifest
    print("\n[6/7] Generating cryptographic audit manifest...")
    
    pool_hasher = hashlib.sha256()
    for c in all_valid_candidates:
        pool_hasher.update(f"{c['Basin']}_{c['Lat']}_{c['Lon']}_{c['Timestamp'].isoformat()}".encode())
    candidate_pool_hash = pool_hasher.hexdigest()
    
    audit_data = {
        "sampler_version": SAMPLER_VERSION,
        "sampler_sha256": get_script_hash(),
        "protocol_sha256": get_protocol_hash(),
        "git_commit_hash": get_git_hash(),
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "software_versions": current_versions,
        "frozen_versions": FROZEN_VERSIONS,
        "exclusion_parameters": {
            "radius_km": EXCLUSION_RADIUS_KM,
            "time_days": EXCLUSION_TIME_DAYS,
            "land_exclusion_km": LAND_EXCLUSION_KM,
            "candidate_grid_res_deg": CANDIDATE_GRID_RES
        },
        "candidate_pool_hash": candidate_pool_hash,
        "sampling_summary": {
            "total_selected_controls": len(selected_df),
            "basin_totals": selected_df['Basin'].value_counts().to_dict(),
            "total_valid_candidates": len(all_valid_candidates),
            "total_rejected": len(all_filter_logs)
        }
    }
    
    audit_path = OUTPUT_DIR / "control_audit.json"
    with open(audit_path, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
        
    # 7. Final Invariant Checks
    print("\n[7/7] Running final invariant checks...")
    assert len(selected_df) == 150, f"CRITICAL: Selected {len(selected_df)} controls, expected 150."
    basin_counts = selected_df['Basin'].value_counts().to_dict()
    assert basin_counts == {'NI': 50, 'SI': 50, 'WP': 50}, f"CRITICAL: Basin mismatch! {basin_counts}"
    
    print("-" * 85)
    print(f"  ✓ Total Controls Selected: 150")
    print(f"  ✓ Basin Balance: NI=50, SI=50, WP=50")
    print(f"  → Selected Controls saved to: {selected_path.name}")
    print(f"  → Randomized Order saved to: {rand_order_path.name}")
    print(f"  → Filter Log saved to: {filter_log_path.name}")
    print(f"  → Audit Manifest saved to: {audit_path.name}")
    print("=" * 85)
    print("✅ Phase B2.1 Control Selection is now FROZEN.")
    print("=" * 85)

if __name__ == "__main__":
    run_control_selection()