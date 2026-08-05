"""
TRACEBIND-Albatross: Milestone C - Legacy vs. Corrected Vorticity Comparison
============================================================================
Purpose: Quantify the impact of robust derivative computation on center 
estimation and Global C_phi. 

This explicitly tests the hypothesis that the scalar spacing method 
(legacy) introduced errors on descending grids, and quantifies the 
magnitude of that effect across the cohort.

Additionally, it provides a sensitivity analysis for window filtering 
(All windows vs. Top 80% by local max |vorticity|).
"""

import sys
import json
import numpy as np
import scipy.stats as stats
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

DATA_DIR = Path(r"C:\TRACEBIND-Atmosphere\phase8\c2\raw")
OUTPUT_DIR = Path("outputs/milestone_C")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 9

# ============================================================================
# Vorticity Computation Methods
# ============================================================================
def compute_vorticity_legacy(u, v, X, Y):
    """Legacy method: uses scalar spacing (assumes uniform, positive spacing)."""
    dx = abs(X[0, 1] - X[0, 0])
    dy = abs(Y[1, 0] - Y[0, 0])
    dvdx = np.gradient(v, dx, axis=1)
    dudy = np.gradient(u, dy, axis=0)
    return dvdx - dudy

def compute_vorticity_corrected(u, v, x_1d, y_1d):
    """Corrected method: uses 1D coordinate arrays, robust to ascending/descending grids."""
    dvdx = np.gradient(v, x_1d, axis=1)
    dudy = np.gradient(u, y_1d, axis=0)
    return dvdx - dudy

def find_center(u, v, X, Y, method="corrected"):
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    
    if method == "legacy":
        zeta = compute_vorticity_legacy(u_smooth, v_smooth, X, Y)
    else:
        x_1d = X[0, :]
        y_1d = Y[:, 0]
        zeta = compute_vorticity_corrected(u_smooth, v_smooth, x_1d, y_1d)
        
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    return float(X[idx]), float(Y[idx]), float(np.max(np.abs(zeta)))

# ============================================================================
# Main Analysis
# ============================================================================
def analyze_file(filepath):
    import xarray as xr
    ds = xr.open_dataset(filepath)
    u10 = ds['u10'].squeeze().values.astype('float64')
    v10 = ds['v10'].squeeze().values.astype('float64')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    ds.close()
    
    # Local Cartesian conversion
    lat_rad = np.radians(lat)
    dy = (lat - np.mean(lat)) * 111.0
    dx = (lon - np.mean(lon)) * 111.0 * np.cos(np.mean(lat_rad))
    X_km, Y_km = np.meshgrid(dx, dy)
    
    # 1. Legacy Center & C_phi
    leg_cx, leg_cy, _ = find_center(u10, v10, X_km, Y_km, method="legacy")
    leg_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(leg_cx, leg_cy))
    
    # 2. Corrected Center & C_phi
    cor_cx, cor_cy, _ = find_center(u10, v10, X_km, Y_km, method="corrected")
    cor_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cor_cx, cor_cy))
    
    # 3. Center Shift
    center_shift_km = np.sqrt((cor_cx - leg_cx)**2 + (cor_cy - leg_cy)**2)
    
    # 4. Sensitivity Analysis: Window Filtering (using CORRECTED center logic for local windows)
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    x_1d = X_km[0, :]
    y_1d = Y_km[:, 0]
    
    all_dists = []
    valid_dists = []
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            _, _, max_zeta = find_center(u_win, v_win, x_win, y_win, method="corrected")
            
            abs_i = (i - half_w) + np.unravel_index(np.argmax(np.abs(compute_vorticity_corrected(
                gaussian_filter(u_win, 0.8), gaussian_filter(v_win, 0.8), x_win[0,:], y_win[:,0]))), 
                compute_vorticity_corrected(gaussian_filter(u_win, 0.8), gaussian_filter(v_win, 0.8), x_win[0,:], y_win[:,0]).shape)[0]
            abs_j = (j - half_w) + np.unravel_index(np.argmax(np.abs(compute_vorticity_corrected(
                gaussian_filter(u_win, 0.8), gaussian_filter(v_win, 0.8), x_win[0,:], y_win[:,0]))), 
                compute_vorticity_corrected(gaussian_filter(u_win, 0.8), gaussian_filter(v_win, 0.8), x_win[0,:], y_win[:,0]).shape)[1]
            
            # Simplified local center extraction for speed/robustness in loop:
            zeta_win = compute_vorticity_corrected(gaussian_filter(u_win, 0.8), gaussian_filter(v_win, 0.8), x_win[0,:], y_win[:,0])
            loc_i, loc_j = np.unravel_index(np.argmax(np.abs(zeta_win)), zeta_win.shape)
            abs_i = (i - half_w) + loc_i
            abs_j = (j - half_w) + loc_j
            
            dist = np.sqrt((X_km[abs_i, abs_j] - cor_cx)**2 + (Y_km[abs_i, abs_j] - cor_cy)**2)
            all_dists.append(dist)
            
            # We will compute the 80% threshold after the loop
            window_data = {"dist": dist, "max_zeta": float(np.max(np.abs(zeta_win)))}
            valid_dists.append(window_data)

    n_total = len(all_dists)
    threshold = float(np.percentile([w["max_zeta"] for w in valid_dists], 20))
    filtered_dists = [w["dist"] for w in valid_dists if w["max_zeta"] > threshold]
    n_valid = len(filtered_dists)
    
    return {
        "filename": Path(filepath).name,
        "legacy_c_phi": round(leg_c_phi, 4),
        "corrected_c_phi": round(cor_c_phi, 4),
        "delta_c_phi": round(cor_c_phi - leg_c_phi, 4),
        "center_shift_km": round(center_shift_km, 2),
        "legacy_center": [round(leg_cx, 2), round(leg_cy, 2)],
        "corrected_center": [round(cor_cx, 2), round(cor_cy, 2)],
        "sensitivity_all_windows_median_km": round(float(np.median(all_dists)), 2),
        "sensitivity_top80_median_km": round(float(np.median(filtered_dists)), 2),
        "valid_fraction": round(n_valid / n_total, 4)
    }

def run_comparison():
    print("=" * 90)
    print("MILESTONE C: LEGACY VS. CORRECTED VORTICITY COMPARISON (N=20)")
    print("=" * 90)
    print("Testing hypothesis: Scalar spacing on descending grids alters center estimation.\n")
    
    nc_files = sorted(list(DATA_DIR.glob("*.nc")))
    results = []
    
    for i, filepath in enumerate(nc_files, 1):
        print(f"[{i}/{len(nc_files)}] Analyzing {filepath.name}...", end=" ")
        try:
            res = analyze_file(filepath)
            results.append(res)
            print(f"OK (Legacy Cφ={res['legacy_c_phi']:.4f}, Corrected Cφ={res['corrected_c_phi']:.4f}, Shift={res['center_shift_km']:.1f} km)")
        except Exception as e:
            print(f"FAILED ({e})")
            
    if not results:
        return

    # Sort by magnitude of center shift to highlight the effect
    results.sort(key=lambda x: x['center_shift_km'], reverse=True)
    
    print("\n" + "=" * 90)
    print("COMPARISON RESULTS (Sorted by Center Shift Magnitude)")
    print("=" * 90)
    print(f"{'File':<25} | {'Legacy Cφ':<9} | {'Corr Cφ':<9} | {'Δ Cφ':<8} | {'Shift (km)':<10}")
    print("-" * 90)
    for r in results:
        print(f"{r['filename']:<25} | {r['legacy_c_phi']:<9.4f} | {r['corrected_c_phi']:<9.4f} | {r['delta_c_phi']:>+8.4f} | {r['center_shift_km']:<10.1f}")
        
    # Sensitivity Analysis Summary
    print("\n" + "=" * 90)
    print("SENSITIVITY ANALYSIS: Median Distance to Corrected Center")
    print("=" * 90)
    print(f"{'File':<25} | {'All Windows':<15} | {'Top 80% (by |ζ|)':<18} | {'Valid %'}")
    print("-" * 90)
    for r in results:
        print(f"{r['filename']:<25} | {r['sensitivity_all_windows_median_km']:<15.1f} | {r['sensitivity_top80_median_km']:<18.1f} | {r['valid_fraction']*100:.1f}%")

    # Save JSON
    report = {
        "milestone": "C_legacy_vs_corrected",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "Scalar spacing on descending grids alters center estimation and Global C_phi",
        "cases": results
    }
    
    report_path = OUTPUT_DIR / "legacy_vs_corrected_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n✅ Analysis complete. Report saved to {report_path}")
    print("=" * 90)

if __name__ == "__main__":
    run_comparison()