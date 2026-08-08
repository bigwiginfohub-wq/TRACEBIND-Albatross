"""
TRACEBIND Phase B3: Descriptor Extraction (C_phi)
==================================================
Purpose: Deterministically and blindly extract the mean absolute tangential 
velocity alignment descriptor (C_phi) for the 300 frozen cases.

Strictly adheres to PHASE_B3_DESCRIPTOR_EXTRACTION_PROTOCOL.md v1.0.
"""

import xarray as xr
import pandas as pd
import numpy as np
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# ============================================================================
# Configuration & Constants
# ============================================================================
PHASEB_DIR = Path(__file__).parent
INPUT_NC = PHASEB_DIR / "b2.2_era5_fields.nc"
EXPECTED_INPUT_HASH = "872635f3885917b2fba9f06f74d354e25b955d563dca769bb03a22bde085a3c0"
PROTOCOL_PATH = PHASEB_DIR / "PHASE_B3_DESCRIPTOR_EXTRACTION_PROTOCOL.md"

OUTPUT_CSV = PHASEB_DIR / "b3_descriptors.csv"
OUTPUT_AUDIT = PHASEB_DIR / "b3_audit.json"

EARTH_RADIUS_KM = 6371.0088

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
    """Compute great-circle distance in km."""
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    return EARTH_RADIUS_KM * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate initial great-circle bearing from (lat1, lon1) to (lat2, lon2).
    Returns bearing in radians, measured CLOCKWISE from North.
    """
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    
    y = np.sin(dlon) * np.cos(lat2_rad)
    x = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)
    
    bearing_rad = np.arctan2(y, x)
    # Normalize to 0 to 2*pi (clockwise from North)
    bearing_rad = np.mod(bearing_rad, 2 * np.pi)
    return bearing_rad

# ============================================================================
# Main Execution
# ============================================================================
def run_extraction():
    print("=" * 85)
    print("PHASE B3: Descriptor Extraction (C_phi)")
    print("=" * 85)
    
    # 1. Preflight Hash Check
    print("\n[1/5] Verifying input artifact integrity...")
    actual_hash = compute_sha256(INPUT_NC)
    if actual_hash != EXPECTED_INPUT_HASH:
        raise RuntimeError(f"CRITICAL: Input hash mismatch!\nExpected: {EXPECTED_INPUT_HASH}\nActual:   {actual_hash}\nAborting extraction to preserve provenance.")
    print(f"  ✅ Input artifact SHA256 verified: {actual_hash[:16]}...")

    # 2. Load Data & Validate Schema
    print("\n[2/5] Loading and validating frozen B2.2 artifact schema...")
    with xr.open_dataset(INPUT_NC) as ds:
        # Schema validation
        expected_vars = {
            "u10", "v10", "native_latitude", "native_longitude",
            "case_id", "case_type", "case_timestamp",
            "requested_latitude", "requested_longitude",
            "center_grid_latitude", "center_grid_longitude"
        }
        missing = expected_vars - set(ds.variables)
        if missing:
            raise ValueError(f"Missing required variables: {sorted(missing)}")
            
        if ds.sizes.get("case") != 300:
            raise ValueError(f"Expected case dimension = 300, got {ds.sizes.get('case')}")
        if ds.sizes.get("y") != 17 or ds.sizes.get("x") != 17:
            raise ValueError("Expected 17x17 spatial dimensions")
        if ds["u10"].shape != (300, 17, 17):
            raise ValueError(f"u10 shape mismatch: {ds['u10'].shape}")
        if ds["v10"].shape != (300, 17, 17):
            raise ValueError(f"v10 shape mismatch: {ds['v10'].shape}")
            
        print("  ✅ Schema, dimensions, and shapes validated.")
        
        n_cases = ds.sizes["case"]
        case_ids = ds["case_id"].values
        case_types = ds["case_type"].values
        case_timestamps = ds["case_timestamp"].values
        req_lats = ds["requested_latitude"].values
        req_lons = ds["requested_longitude"].values
        
        # 3. Blind Extraction Loop (Case-by-case to minimize RAM footprint)
        print("\n[3/5] Executing blind descriptor extraction...")
        results = []
        
        for i in range(n_cases):
            case_id = str(case_ids[i])
            case_type = str(case_types[i])
            case_ts = str(case_timestamps[i])
            c_lat = float(req_lats[i])
            c_lon = float(req_lons[i])
            
            # Extract single case
            u = ds["u10"].isel(case=i).values
            v = ds["v10"].isel(case=i).values
            n_lat = ds["native_latitude"].isel(case=i).values
            n_lon = ds["native_longitude"].isel(case=i).values
            
            # Calculate distance and bearing for all 17x17 points
            dists = haversine_km(c_lat, c_lon, n_lat, n_lon)
            bearings = calculate_bearing(c_lat, c_lon, n_lat, n_lon)
            
            # Shell mask: 30 <= r <= 150 km
            shell_mask = (dists >= 30.0) & (dists <= 150.0)
            n_shell = int(np.sum(shell_mask))
            
            # QC Checks
            qc_status = "PASSED"
            c_phi = np.nan
            
            if n_shell == 0:
                qc_status = "FAILED"
            else:
                u_shell = u[shell_mask]
                v_shell = v[shell_mask]
                b_shell = bearings[shell_mask]
                
                # Check for non-finite values
                if not np.all(np.isfinite(u_shell)) or not np.all(np.isfinite(v_shell)):
                    qc_status = "FAILED"
                else:
                    # Check for exact zero wind
                    v_mag = np.sqrt(u_shell**2 + v_shell**2)
                    if np.any(v_mag == 0.0):
                        qc_status = "FAILED"
                    else:
                        # Tangential projection: V_theta = -u * cos(b) + v * sin(b)
                        v_theta = -u_shell * np.cos(b_shell) + v_shell * np.sin(b_shell)
                        
                        # Normalized absolute alignment
                        alignment = np.abs(v_theta / v_mag)
                        
                        # Strict bounds check: 0 <= C_phi <= 1 (with small float epsilon)
                        if np.any(alignment < -1e-9) or np.any(alignment > 1.0 + 1e-9):
                            qc_status = "FAILED"
                        else:
                            c_phi = float(np.mean(alignment))
                            
                            # Final sanity check on the mean
                            if c_phi < 0.0 or c_phi > 1.0:
                                qc_status = "FAILED"
            
            results.append({
                "case_id": case_id,
                "case_type": case_type,
                "case_timestamp": case_ts,
                "C_phi": c_phi,
                "shell_grid_count": n_shell,
                "QC_Status": qc_status
            })
            
            if qc_status == "FAILED":
                print(f"  ⚠️  Case {case_id} FAILED QC")
            elif (i + 1) % 50 == 0:
                print(f"  → Processed {i + 1}/{n_cases} cases...")

    # 4. Save Output
    print("\n[4/5] Saving output artifacts...")
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"  → Saved descriptors: {OUTPUT_CSV.name}")
    
    # 5. Generate Audit Manifest
    print("\n[5/5] Generating cryptographic audit manifest...")
    passed_count = int(np.sum(df["QC_Status"] == "PASSED"))
    
    audit_data = {
        "input_artifact_sha256": actual_hash,
        "protocol_sha256": compute_sha256(PROTOCOL_PATH),
        "script_sha256": compute_sha256(Path(__file__)),
        "output_sha256": compute_sha256(OUTPUT_CSV),
        "git_commit_hash": get_git_hash(),
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary_statistics": {
            "total_cases": n_cases,
            "passed": passed_count,
            "failed": n_cases - passed_count
        }
    }
    
    with open(OUTPUT_AUDIT, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
    print(f"  → Saved audit manifest: {OUTPUT_AUDIT.name}")
    
    print("\n" + "=" * 85)
    if passed_count == 300:
        print("✅ Phase B3 Extraction is 100% COMPLETE and SUCCESSFUL.")
        print("   All 300 cases passed strict QC. Ready for Phase B4.")
    else:
        print(f"⚠️  Phase B3 COMPLETED WITH FAILURES: {passed_count}/300 passed.")
        print("   Review b3_descriptors.csv and b3_audit.json for details.")
    print("=" * 85)

if __name__ == "__main__":
    run_extraction()