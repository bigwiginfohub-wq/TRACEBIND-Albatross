"""
TRACEBIND-Albatross: Milestone C - Cohort Center Alignment Test
================================================================
Purpose: Evaluate the Two-Scale Interpretation hypothesis across the 
entire 20-case ERA5 cohort.

Hypothesis: Global C_phi is negatively correlated with the median distance 
between local vorticity centers and the global vorticity center. 
(Note: We test for consistency with this hypothesis, not definitive validation.)
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
VORTICITY_THRESHOLD = 1e-5  # s^-1: Minimum local max |vorticity| to be considered a "meaningful" rotational center

def latlon_to_km(lat, lon):
    lat_rad = np.radians(lat)
    dy = (lat - np.mean(lat)) * 111.0
    dx = (lon - np.mean(lon)) * 111.0 * np.cos(np.mean(lat_rad))
    return np.meshgrid(dx, dy)

def compute_vorticity(u, v, dx, dy):
    dvdx = np.gradient(v, dx, axis=1)
    dudy = np.gradient(u, dy, axis=0)
    return dvdx - dudy

def find_max_vorticity_center(X, Y, u, v, dx, dy):
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    zeta = compute_vorticity(u_smooth, v_smooth, dx, dy)
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    return float(X[idx]), float(Y[idx]), idx[0], idx[1], float(np.max(np.abs(zeta)))

def analyze_alignment(filepath):
    import xarray as xr
    ds = xr.open_dataset(filepath)
    u10 = ds['u10'].squeeze().values.astype('float64')
    v10 = ds['v10'].squeeze().values.astype('float64')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    ds.close()
    
    X_km, Y_km = latlon_to_km(lat, lon)
    dx_km = abs(X_km[0, 1] - X_km[0, 0])
    dy_km = abs(Y_km[1, 0] - Y_km[0, 0])
    
    # 1. Find Global Center
    global_cx, global_cy, _, _, _ = find_max_vorticity_center(X_km, Y_km, u10, v10, dx_km, dy_km)
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(global_cx, global_cy))
    
    # 2. Slide window and find LOCAL center for each
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    
    distances_to_global = []
    n_total_windows = 0
    n_valid_windows = 0
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            n_total_windows += 1
            
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            # Check if window has meaningful rotation
            _, _, loc_i, loc_j, max_abs_zeta = find_max_vorticity_center(x_win, y_win, u_win, v_win, dx_km, dy_km)
            
            if max_abs_zeta > VORTICITY_THRESHOLD:
                n_valid_windows += 1
                # Convert local grid indices back to global grid indices
                abs_i = (i - half_w) + loc_i
                abs_j = (j - half_w) + loc_j
                
                # Distance from this local center to the global center
                dist = np.sqrt((X_km[abs_i, abs_j] - global_cx)**2 + (Y_km[abs_i, abs_j] - global_cy)**2)
                distances_to_global.append(dist)
            
    # Compute distribution statistics
    dist_arr = np.array(distances_to_global)
    
    return {
        "filename": Path(filepath).name,
        "global_c_phi": round(float(global_c_phi), 4),
        "n_total_windows": n_total_windows,
        "n_valid_windows": n_valid_windows,
        "valid_fraction": round(n_valid_windows / n_total_windows, 4) if n_total_windows > 0 else 0.0,
        "mean_distance_km": round(float(np.mean(dist_arr)), 2) if len(dist_arr) > 0 else np.nan,
        "median_distance_km": round(float(np.median(dist_arr)), 2) if len(dist_arr) > 0 else np.nan,
        "p25_distance_km": round(float(np.percentile(dist_arr, 25)), 2) if len(dist_arr) > 0 else np.nan,
        "p75_distance_km": round(float(np.percentile(dist_arr, 75)), 2) if len(dist_arr) > 0 else np.nan,
        "p90_distance_km": round(float(np.percentile(dist_arr, 90)), 2) if len(dist_arr) > 0 else np.nan,
    }

def run_cohort_test():
    print("=" * 80)
    print("MILESTONE C: COHORT CENTER ALIGNMENT TEST (N=20)")
    print("=" * 80)
    print(f"Filtering threshold: local max |vorticity| > {VORTICITY_THRESHOLD} s^-1")
    
    nc_files = sorted(list(DATA_DIR.glob("*.nc")))
    print(f"\nProcessing {len(nc_files)} cases. This may take 2-3 minutes...\n")
    
    results = []
    for i, filepath in enumerate(nc_files, 1):
        print(f"[{i}/{len(nc_files)}] Analyzing {filepath.name}...", end=" ")
        try:
            res = analyze_alignment(filepath)
            results.append(res)
            print(f"OK (Global Cφ = {res['global_c_phi']:.4f}, Median Dist = {res['median_distance_km']:.1f} km, Valid = {res['valid_fraction']*100:.1f}%)")
        except Exception as e:
            print(f"FAILED ({e})")
            
    if not results:
        print("\n❌ No successful analyses.")
        return

    # Sort by Global C_phi for display
    results.sort(key=lambda x: x['global_c_phi'], reverse=True)
    
    print("\n" + "=" * 80)
    print("COHORT RESULTS (Sorted by Global C_phi)")
    print("=" * 80)
    print(f"{'File':<25} | {'Global Cφ':<9} | {'Median Dist':<12} | {'Valid Windows'}")
    print("-" * 80)
    for r in results:
        print(f"{r['filename']:<25} | {r['global_c_phi']:<9.4f} | {r['median_distance_km']:<12.1f} | {r['n_valid_windows']}/{r['n_total_windows']} ({r['valid_fraction']*100:.1f}%)")
        
    # Compute Correlation (using Median distance as it is more robust to outliers)
    global_cphis = [r['global_c_phi'] for r in results]
    median_dists = [r['median_distance_km'] for r in results]
    
    pearson_r, pearson_p = stats.pearsonr(global_cphis, median_dists)
    spearman_rho, spearman_p = stats.spearmanr(global_cphis, median_dists)
    
    print("\n" + "=" * 80)
    print("CORRELATION ANALYSIS: Global Cφ vs. Median Center Distance")
    print("=" * 80)
    print(f"Pearson  r = {pearson_r:7.4f}  (p = {pearson_p:.4e})")
    print(f"Spearman ρ = {spearman_rho:7.4f}  (p = {spearman_p:.4e})")
    print("⚠️  NOTE: With N=20, p-values should be interpreted cautiously. Focus on the magnitude and direction of r and ρ.")
    print("=" * 80)
    
    # Visualization
    fig, ax = plt.subplots(figsize=(10, 7))
    
    ax.scatter(median_dists, global_cphis, color='#1f77b4', s=80, alpha=0.7, edgecolor='black')
    
    # Add trendline
    z = np.polyfit(median_dists, global_cphis, 1)
    p = np.poly1d(z)
    x_trend = np.linspace(min(median_dists)-50, max(median_dists)+50, 100)
    ax.plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2, label=f"Linear Fit (r = {pearson_r:.3f})")
    
    # Annotate highest and lowest
    highest = results[0]
    lowest = results[-1]
    ax.annotate(f"Highest\n{highest['filename'][:12]}", 
                (highest['median_distance_km'], highest['global_c_phi']), 
                xytext=(10, 10), textcoords='offset points', fontsize=9, color='green', fontweight='bold')
    ax.annotate(f"Lowest\n{lowest['filename'][:12]}", 
                (lowest['median_distance_km'], lowest['global_c_phi']), 
                xytext=(-80, -20), textcoords='offset points', fontsize=9, color='orange', fontweight='bold')
    
    ax.set_xlabel("Median Distance: Local Vorticity Center to Global Center (km)", fontsize=12)
    ax.set_ylabel("Global C_phi", fontsize=12)
    ax.set_title("Evaluating the Two-Scale Interpretation: N=20 ERA5 Cases\nDoes Global Coherence Require Center Alignment?", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "cohort_center_alignment_scatter.png", dpi=200)
    plt.close()
    
    # Save JSON
    report = {
        "milestone": "C_cohort_alignment",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "vorticity_threshold_s_inv": VORTICITY_THRESHOLD,
        "correlation": {
            "pearson_r": round(float(pearson_r), 4),
            "pearson_p": float(pearson_p),
            "spearman_rho": round(float(spearman_rho), 4),
            "spearman_p": float(spearman_p)
        },
        "cases": results
    }
    
    report_path = OUTPUT_DIR / "cohort_alignment_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n✅ Analysis complete.")
    print(f"  → Scatter plot: {OUTPUT_DIR / 'cohort_center_alignment_scatter.png'}")
    print(f"  → Stats report: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_cohort_test()