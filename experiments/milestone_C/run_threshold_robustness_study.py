"""
TRACEBIND-Albatross: Milestone C - Filtering Threshold Robustness Study
=======================================================================
Purpose: Evaluate whether the observed negative correlation between 
Corrected Global Cφ and Median Center Distance is robust across 
different vorticity filtering thresholds, or if it is an artifact 
of a single arbitrary cutoff.

Hypothesis: The negative correlation should remain relatively stable 
(e.g., r between -0.35 and -0.50) across a reasonable range of 
exclusion thresholds (10% to 40%), proving the relationship is a 
genuine geometric property, not a tuned artifact.
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
THRESHOLDS_TO_TEST = [0, 10, 20, 30, 40, 50]  # Percent of weakest windows to exclude

def compute_vorticity_corrected(u, v, x_1d, y_1d):
    dvdx = np.gradient(v, x_1d, axis=1)
    dudy = np.gradient(u, y_1d, axis=0)
    return dvdx - dudy

def find_center_corrected(u, v, X, Y):
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    x_1d = X[0, :]
    y_1d = Y[:, 0]
    zeta = compute_vorticity_corrected(u_smooth, v_smooth, x_1d, y_1d)
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    return float(X[idx]), float(Y[idx]), float(np.max(np.abs(zeta)))

def process_file_for_robustness(filepath):
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
    
    # 1. Get Corrected Global Center and C_phi
    cor_cx, cor_cy, _ = find_center_corrected(u10, v10, X_km, Y_km)
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cor_cx, cor_cy))
    
    # 2. Extract all window data ONCE
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    x_1d = X_km[0, :]
    y_1d = Y_km[:, 0]
    
    window_data = []
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            # Local max vorticity
            u_win_smooth = gaussian_filter(u_win, sigma=0.8)
            v_win_smooth = gaussian_filter(v_win, sigma=0.8)
            zeta_win = compute_vorticity_corrected(u_win_smooth, v_win_smooth, x_win[0,:], y_win[:,0])
            max_zeta = float(np.max(np.abs(zeta_win)))
            
            loc_i, loc_j = np.unravel_index(np.argmax(np.abs(zeta_win)), zeta_win.shape)
            abs_i = (i - half_w) + loc_i
            abs_j = (j - half_w) + loc_j
            
            dist = np.sqrt((X_km[abs_i, abs_j] - cor_cx)**2 + (Y_km[abs_i, abs_j] - cor_cy)**2)
            window_data.append({"dist": dist, "max_zeta": max_zeta})
            
    return {
        "filename": Path(filepath).name,
        "global_c_phi": round(float(global_c_phi), 4),
        "window_data": window_data
    }

def run_robustness_study():
    print("=" * 85)
    print("MILESTONE C: FILTERING THRESHOLD ROBUSTNESS STUDY")
    print("=" * 85)
    print("Testing if the correlation is stable across different exclusion thresholds.\n")
    
    nc_files = sorted(list(DATA_DIR.glob("*.nc")))
    print(f"Step 1/2: Extracting window data for {len(nc_files)} cases (this takes ~1 min)...")
    
    file_results = []
    for filepath in nc_files:
        res = process_file_for_robustness(filepath)
        file_results.append(res)
        
    print("Step 2/2: Evaluating correlations across thresholds...\n")
    
    correlation_results = []
    
    for exclude_pct in THRESHOLDS_TO_TEST:
        median_dists = []
        global_cphis = []
        
        for res in file_results:
            windows = res["window_data"]
            if not windows:
                continue
                
            # Sort by max_zeta ascending
            windows.sort(key=lambda x: x["max_zeta"])
            
            # Calculate how many to exclude
            n_exclude = int(len(windows) * (exclude_pct / 100.0))
            valid_windows = windows[n_exclude:]
            
            if not valid_windows:
                continue
                
            valid_dists = [w["dist"] for w in valid_windows]
            median_dists.append(float(np.median(valid_dists)))
            global_cphis.append(res["global_c_phi"])
            
        # Compute correlation for this threshold
        if len(global_cphis) >= 3:
            pearson_r, p_r = stats.pearsonr(global_cphis, median_dists)
            spearman_rho, p_s = stats.spearmanr(global_cphis, median_dists)
        else:
            pearson_r, spearman_rho = np.nan, np.nan
            
        correlation_results.append({
            "exclude_percent": exclude_pct,
            "pearson_r": round(float(pearson_r), 4) if not np.isnan(pearson_r) else None,
            "spearman_rho": round(float(spearman_rho), 4) if not np.isnan(spearman_rho) else None,
            "n_cases": len(global_cphis)
        })
        
        print(f"Exclude {exclude_pct:2d}% weakest: Pearson r = {pearson_r:7.4f} | Spearman ρ = {spearman_rho:7.4f}")
        
    # Visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    
    exclude_pcts = [r["exclude_percent"] for r in correlation_results]
    pearsons = [r["pearson_r"] for r in correlation_results]
    spearmans = [r["spearman_rho"] for r in correlation_results]
    
    ax.plot(exclude_pcts, pearsons, 'o-', label='Pearson r', color='#1f77b4', linewidth=2, markersize=8)
    ax.plot(exclude_pcts, spearmans, 's--', label='Spearman ρ', color='#d62728', linewidth=2, markersize=8)
    
    ax.set_xlabel("Percentage of Weakest Vorticity Windows Excluded (%)", fontsize=12)
    ax.set_ylabel("Correlation Coefficient (Global Cφ vs. Median Center Distance)", fontsize=12)
    ax.set_title("Robustness of Correlation Across Filtering Thresholds", fontsize=14, fontweight='bold')
    ax.set_xticks(THRESHOLDS_TO_TEST)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)
    
    # Add a reference line at r = 0
    ax.axhline(0, color='black', linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "threshold_robustness_plot.png", dpi=200)
    plt.close()
    
    # Save JSON
    report = {
        "milestone": "C_threshold_robustness",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "results": correlation_results
    }
    
    report_path = OUTPUT_DIR / "threshold_robustness_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print("\n" + "=" * 85)
    print("✅ ROBUSTNESS STUDY COMPLETE")
    print(f"  → Plot saved to: {OUTPUT_DIR / 'threshold_robustness_plot.png'}")
    print(f"  → Data saved to: {report_path}")
    print("=" * 85)

if __name__ == "__main__":
    run_robustness_study()