"""
TRACEBIND B2.2: Read-Only B3 Input Contract Verification
=========================================================
Verifies the frozen B2.2 artifacts meet all requirements for Phase B3.
Schema-agnostic: handles whatever keys the audit JSON actually contains.
"""
import pandas as pd
import numpy as np
import xarray as xr
import json
import hashlib
from pathlib import Path

PHASEB_DIR = Path(__file__).parent
NC_PATH = PHASEB_DIR / "b2.2_era5_fields.nc"
INDEX_PATH = PHASEB_DIR / "b2.2_target_index.csv"
AUDIT_PATH = PHASEB_DIR / "b2.2_qc_audit.json"

EARTH_RADIUS_KM = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    return EARTH_RADIUS_KM * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

print("=" * 75)
print("TRACEBIND B2.2: B3 INPUT CONTRACT VERIFICATION")
print("=" * 75)

all_pass = True

# ============================================================================
# 1. Audit Manifest
# ============================================================================
print("\n[1] AUDIT MANIFEST")
print("-" * 50)
with open(AUDIT_PATH, 'r') as f:
    audit = json.load(f)

stats = audit.get("summary_statistics", {})
print(f"  total_requested:      {stats.get('total_requested', 'N/A')}")
print(f"  total_successful:     {stats.get('total_successful', 'N/A')}")
# Handle both possible schemas
if 'total_currently_failed' in stats:
    print(f"  total_currently_failed: {stats['total_currently_failed']}")
    print(f"  failure_events_recorded: {stats.get('failure_events_recorded', 'N/A')}")
else:
    print(f"  total_failed (events):  {stats.get('total_failed', 'N/A')}")

manifest_hash = audit.get("output_hashes", {}).get("era5_fields_nc_sha256")
print(f"\n  Manifest SHA256: {manifest_hash}")

# ============================================================================
# 2. Primary Artifact Integrity
# ============================================================================
print("\n[2] PRIMARY ARTIFACT INTEGRITY")
print("-" * 50)

actual_hash = compute_sha256(NC_PATH)
print(f"  Actual SHA256:   {actual_hash}")

if manifest_hash is None:
    print("  ⚠️  Manifest does not contain era5_fields_nc_sha256")
    all_pass = False
elif actual_hash == manifest_hash:
    print("  ✅ SHA256 MATCHES manifest")
else:
    print("  ❌ SHA256 MISMATCH")
    all_pass = False

with xr.open_dataset(NC_PATH) as ds:
    dims = dict(ds.dims)
    print(f"\n  Dimensions: {dims}")
    print(f"  Variables:  {list(ds.data_vars)}")
    
    # Dimension checks
    if dims.get("case") != 300:
        print(f"  ❌ Expected case=300, got {dims.get('case')}")
        all_pass = False
    else:
        print(f"  ✅ case dimension = 300")
        
    if dims.get("y") != 17 or dims.get("x") != 17:
        print(f"  ❌ Expected y=17, x=17")
        all_pass = False
    else:
        print(f"  ✅ y=17, x=17")
        
    # Variable presence
    for v in ["u10", "v10", "native_latitude", "native_longitude"]:
        if v not in ds.data_vars and v not in ds.coords:
            print(f"  ❌ Missing {v}")
            all_pass = False
    print(f"  ✅ All required variables present")
    
    # Shape checks
    if ds["u10"].shape != (300, 17, 17):
        print(f"  ❌ u10 shape {ds['u10'].shape} != (300,17,17)")
        all_pass = False
    else:
        print(f"  ✅ u10 shape = (300,17,17)")
        
    if ds["v10"].shape != (300, 17, 17):
        print(f"  ❌ v10 shape {ds['v10'].shape} != (300,17,17)")
        all_pass = False
    else:
        print(f"  ✅ v10 shape = (300,17,17)")
    
    # Unique IDs
    case_ids = ds["case_id"].values.astype(str)
    if len(set(case_ids)) != 300:
        print(f"  ❌ Duplicate case IDs detected")
        all_pass = False
    else:
        print(f"  ✅ All 300 case IDs unique")
        
    # Case type balance
    case_types = ds["case_type"].values.astype(str)
    tc_count = np.sum(case_types == "TC")
    ctrl_count = np.sum(case_types == "Control")
    print(f"\n  TC count:      {tc_count}")
    print(f"  Control count: {ctrl_count}")
    if tc_count != 150 or ctrl_count != 150:
        print(f"  ❌ Expected 150/150 balance")
        all_pass = False
    else:
        print(f"  ✅ 150/150 basin balance confirmed")
    
    # ========================================================================
    # 3. Full 300-Case Finiteness & Shell Validation
    # ========================================================================
    print("\n[3] FULL 300-CASE VALIDATION (finiteness + shell)")
    print("-" * 50)
    
    finite_failures = 0
    shell_failures = 0
    
    for c_idx in range(300):
        # Check entire 17x17 field is finite
        if not np.all(np.isfinite(ds["u10"].values[c_idx])):
            finite_failures += 1
        if not np.all(np.isfinite(ds["v10"].values[c_idx])):
            finite_failures += 1
        if not np.all(np.isfinite(ds["native_latitude"].values[c_idx])):
            finite_failures += 1
        if not np.all(np.isfinite(ds["native_longitude"].values[c_idx])):
            finite_failures += 1
            
        # Check shell
        c_lat = float(ds["requested_latitude"].values[c_idx])
        c_lon = float(ds["requested_longitude"].values[c_idx])
        n_lats = ds["native_latitude"].values[c_idx]  # already 2D
        n_lons = ds["native_longitude"].values[c_idx]  # already 2D
        
        dists = haversine_km(c_lat, c_lon, n_lats, n_lons)
        shell_mask = (dists >= 30.0) & (dists <= 150.0)
        
        if not np.any(shell_mask):
            shell_failures += 1
            continue
        if np.max(dists) < 150.0:
            shell_failures += 1
            continue
            
        u10_s = ds["u10"].values[c_idx][shell_mask]
        v10_s = ds["v10"].values[c_idx][shell_mask]
        if not np.all(np.isfinite(u10_s)) or not np.all(np.isfinite(v10_s)):
            shell_failures += 1
    
    if finite_failures == 0:
        print(f"  ✅ All 300 cases have finite u10/v10/native coords")
    else:
        print(f"  ❌ {finite_failures} finite-value failures")
        all_pass = False
        
    if shell_failures == 0:
        print(f"  ✅ All 300 cases have valid 30-150 km shells")
    else:
        print(f"  ❌ {shell_failures} shell failures")
        all_pass = False

# ============================================================================
# 4. Index ↔ NetCDF Cross-Check
# ============================================================================
print("\n[4] INDEX ↔ NETCDF CROSS-CHECK")
print("-" * 50)

index_df = pd.read_csv(INDEX_PATH)
print(f"  Index rows: {len(index_df)}")

if len(index_df) != 300:
    print(f"  ❌ Expected 300 index rows")
    all_pass = False
else:
    print(f"  ✅ Index has 300 rows")

# Load NetCDF IDs in order
with xr.open_dataset(NC_PATH) as ds:
    nc_ids = ds["case_id"].values.astype(str)
    nc_types = ds["case_type"].values.astype(str)
    nc_times = ds["case_timestamp"].values.astype(str)

index_ids = index_df["ID"].astype(str).to_numpy()
index_types = index_df["Type"].astype(str).to_numpy()
index_times = index_df["ERA5Timestamp"].astype(str).to_numpy()

if np.array_equal(index_ids, nc_ids):
    print(f"  ✅ Index IDs exactly match NetCDF case ordering")
else:
    print(f"  ❌ Index IDs do NOT match NetCDF ordering")
    all_pass = False
    
if np.array_equal(index_types, nc_types):
    print(f"  ✅ Index Types exactly match NetCDF ordering")
else:
    print(f"  ❌ Index Types do NOT match NetCDF ordering")
    all_pass = False
    
if np.array_equal(index_times, nc_times):
    print(f"  ✅ Index Timestamps exactly match NetCDF ordering")
else:
    print(f"  ❌ Index Timestamps do NOT match NetCDF ordering")
    all_pass = False

# All QC PASSED?
if (index_df["QC_Status"] == "PASSED").all():
    print(f"  ✅ All index records have QC_Status = PASSED")
else:
    print(f"  ❌ Some index records not PASSED")
    all_pass = False

# ============================================================================
# 5. Final Verdict
# ============================================================================
print("\n" + "=" * 75)
if all_pass:
    print("✅ B3 INPUT CONTRACT FULLY VERIFIED.")
    print("   Phase B2.2 is ready for Git freeze and transition to Phase B3.")
else:
    print("❌ B3 INPUT CONTRACT HAS ISSUES. Review above.")
print("=" * 75)