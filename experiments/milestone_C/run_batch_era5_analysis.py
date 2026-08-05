"""
TRACEBIND-Albatross: Milestone C - Multi-Case Batch Validation
================================================================
Purpose: Apply the frozen pipeline to all available ERA5 cases to study 
variability BETWEEN meteorological events, rather than within a single scene.

This addresses the N=1 limitation of the initial pilot run.
"""

import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

# Point to your existing Phase 8 C2 raw data
DATA_DIR = Path(r"C:\TRACEBIND-Atmosphere\phase8\c2\raw")
OUTPUT_DIR = Path("outputs/milestone_C")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 9

def latlon_to_km(lat, lon):
    lat_rad = np.radians(lat)
    dy = (lat - np.mean(lat)) * 111.0
    dx = (lon - np.mean(lon)) * 111.0 * np.cos(np.mean(lat_rad))
    return np.meshgrid(dx, dy)

def compute_vorticity(u, v, dx, dy):
    dvdx = np.gradient(v, dx, axis=1)
    dudy = np.gradient(u, dy, axis=0)
    return dvdx - dudy

def find_max_vorticity_center(X, Y, u, v):
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    dx = X[0, 1] - X[0, 0]
    dy = Y[1, 0] - Y[0, 0]
    zeta = compute_vorticity(u_smooth, v_smooth, dx, dy)
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    return float(X[idx]), float(Y[idx])

def process_single_file(filepath):
    import xarray as xr
    try:
        ds = xr.open_dataset(filepath)
        u10 = ds['u10'].squeeze().values.astype('float64')
        v10 = ds['v10'].squeeze().values.astype('float64')
        lat = ds['latitude'].values.astype('float64')
        lon = ds['longitude'].values.astype('float64')
        ds.close()
    except Exception as e:
        return {"file": filepath.name, "error": str(e)}
    
    X_km, Y_km = latlon_to_km(lat, lon)
    cx, cy = find_max_vorticity_center(X_km, Y_km, u10, v10)
    
    # 1. Global C_phi
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cx, cy))
    
    # 2. Local C_phi field stats (Derived Procedure A1)
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    c_phi_vals = []
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            c_phi_vals.append(compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win, center=None))
            
    c_phi_vals = np.array(c_phi_vals)
    
    return {
        "file": filepath.name,
        "global_c_phi": round(float(global_c_phi), 4),
        "local_c_phi_mean": round(float(np.mean(c_phi_vals)), 4),
        "local_c_phi_std": round(float(np.std(c_phi_vals)), 4),
        "local_c_phi_min": round(float(np.min(c_phi_vals)), 4),
        "local_c_phi_max": round(float(np.max(c_phi_vals)), 4),
        "center_km": [round(float(cx), 2), round(float(cy), 2)],
        "status": "success"
    }

def run_batch():
    print("=" * 80)
    print("MILESTONE C: MULTI-CASE BATCH VALIDATION")
    print("=" * 80)
    
    nc_files = sorted(list(DATA_DIR.glob("*.nc")))
    print(f"\nFound {len(nc_files)} ERA5 files. Processing...\n")
    
    results = []
    for i, filepath in enumerate(nc_files, 1):
        print(f"[{i}/{len(nc_files)}] Processing {filepath.name}...", end=" ")
        res = process_single_file(filepath)
        results.append(res)
        if res["status"] == "success":
            print(f"OK (Global C_phi = {res['global_c_phi']:.4f})")
        else:
            print(f"FAILED ({res['error']})")
            
    # Separate successes from failures
    successes = [r for r in results if r["status"] == "success"]
    
    if successes:
        global_cphis = [r["global_c_phi"] for r in successes]
        local_means = [r["local_c_phi_mean"] for r in successes]
        
        print("\n" + "=" * 80)
        print("COHORT STATISTICS (N = {} successful cases)".format(len(successes)))
        print("=" * 80)
        print(f"Global C_phi:       Mean = {np.mean(global_cphis):.4f}, Std = {np.std(global_cphis):.4f}, Median = {np.median(global_cphis):.4f}")
        print(f"Local C_phi (mean): Mean = {np.mean(local_means):.4f}, Std = {np.std(local_means):.4f}, Median = {np.median(local_means):.4f}")
        print("=" * 80)
        
        # Save full report
        report = {
            "milestone": "C_batch",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cohort_size": len(successes),
            "cohort_statistics": {
                "global_c_phi": {"mean": round(float(np.mean(global_cphis)), 4), "std": round(float(np.std(global_cphis)), 4), "median": round(float(np.median(global_cphis)), 4)},
                "local_c_phi_mean": {"mean": round(float(np.mean(local_means)), 4), "std": round(float(np.std(local_means)), 4), "median": round(float(np.median(local_means)), 4)}
            },
            "individual_cases": successes
        }
        
        report_path = OUTPUT_DIR / "batch_cohort_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            
        print(f"\n✅ Full cohort report saved to {report_path}")
        
    print("=" * 80)

if __name__ == "__main__":
    run_batch()