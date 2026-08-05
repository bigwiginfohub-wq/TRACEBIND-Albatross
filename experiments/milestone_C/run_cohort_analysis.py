"""
TRACEBIND-Albatross: Milestone C - Cohort Analysis Phase
========================================================
Purpose: Shift from software validation to physical interpretation.
Analyze the distributional properties of the Local C_phi field across
the 20-case ERA5 cohort, focusing on the highest and lowest Global C_phi cases.
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

BATCH_REPORT = Path("outputs/milestone_C/batch_cohort_report.json")
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

def compute_local_cphi_field(u, v, X, Y, window_size=9):
    half_w = window_size // 2
    ny, nx = u.shape
    c_phi_field = np.full((ny, nx), np.nan)
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            c_phi_field[i, j] = compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win, center=None)
    return c_phi_field

def analyze_case(filepath):
    import xarray as xr
    ds = xr.open_dataset(filepath)
    u10 = ds['u10'].squeeze().values.astype('float64')
    v10 = ds['v10'].squeeze().values.astype('float64')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    ds.close()
    
    X_km, Y_km = latlon_to_km(lat, lon)
    cx, cy = find_max_vorticity_center(X_km, Y_km, u10, v10)
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cx, cy))
    
    c_phi_field = compute_local_cphi_field(u10, v10, X_km, Y_km, WINDOW_SIZE)
    valid_c_phi = c_phi_field[~np.isnan(c_phi_field)]
    
    speed = np.sqrt(u10**2 + v10**2)
    
    return {
        "filename": filepath.name,
        "global_c_phi": round(float(global_c_phi), 4),
        "local_mean": round(float(np.mean(valid_c_phi)), 4),
        "local_std": round(float(np.std(valid_c_phi)), 4),
        "local_skew": round(float(stats.skew(valid_c_phi)), 4),
        "local_95th": round(float(np.percentile(valid_c_phi, 95)), 4),
        "local_frac_gt_080": round(float(np.mean(valid_c_phi > 0.80)), 4),
        "max_speed": round(float(np.max(speed)), 2),
        "c_phi_field": c_phi_field,
        "speed_field": speed,
        "X": X_km,
        "Y": Y_km
    }

def run_analysis():
    print("=" * 80)
    print("MILESTONE C: COHORT ANALYSIS PHASE")
    print("=" * 80)
    
    with open(BATCH_REPORT, "r") as f:
        batch_data = json.load(f)
    
    cases = batch_data["individual_cases"]
    cases.sort(key=lambda x: x["global_c_phi"], reverse=True)
    
    top_3 = [c["file"] for c in cases[:3]]
    bottom_3 = [c["file"] for c in cases[-3:]]
    targets = top_3 + bottom_3
    
    print(f"\nAnalyzing {len(targets)} target cases (Top 3 and Bottom 3 by Global C_phi)...")
    
    analysis_results = []
    for fname in targets:
        print(f"  → Processing {fname}...")
        filepath = DATA_DIR / fname
        res = analyze_case(filepath)
        analysis_results.append(res)
        
    # Sort results back to high-to-low for plotting
    analysis_results.sort(key=lambda x: x["global_c_phi"], reverse=True)
    
    print("\n[1/2] Distributional Statistics:")
    print(f"{'File':<25} | {'Global':<7} | {'Local Mean':<11} | {'Local Std':<10} | {'95th %ile':<10} | {'Frac >0.80':<10}")
    print("-" * 85)
    for res in analysis_results:
        print(f"{res['filename']:<25} | {res['global_c_phi']:<7.4f} | {res['local_mean']:<11.4f} | {res['local_std']:<10.4f} | {res['local_95th']:<10.4f} | {res['local_frac_gt_080']:<10.4f}")
    
    print("\n[2/2] Generating comparative visualizations...")
    
    # Figure 1: Global C_phi ranking
    fig, ax = plt.subplots(figsize=(12, 6))
    all_files = [c["file"] for c in cases]
    all_globals = [c["global_c_phi"] for c in cases]
    colors = ['#d62728' if f in top_3 else ('#1f77b4' if f in bottom_3 else '#7f7f7f') for f in all_files]
    
    ax.bar(range(len(all_files)), all_globals, color=colors)
    ax.set_xticks(range(len(all_files)))
    ax.set_xticklabels([f.split('_')[2][:4] for f in all_files], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Global C_phi")
    ax.set_title("TRACEBIND Global C_phi Across 20 ERA5 Cases\n(Red = Top 3, Blue = Bottom 3)")
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "cohort_global_ranking.png", dpi=200)
    plt.close()
    
    # Figure 2: Deep dive into Highest vs Lowest
    highest = analysis_results[0]
    lowest = analysis_results[-1]
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # Highest Case
    axes[0, 0].pcolormesh(highest["X"], highest["Y"], highest["speed_field"], cmap='plasma', shading='auto')
    axes[0, 0].set_title(f"HIGHEST Global C_phi: {highest['filename']}\n(Global = {highest['global_c_phi']:.3f}, Max Speed = {highest['max_speed']:.1f} m/s)")
    axes[0, 0].set_aspect('equal')
    
    axes[0, 1].pcolormesh(highest["X"], highest["Y"], highest["c_phi_field"], cmap='viridis', shading='auto', vmin=0.4, vmax=1.0)
    axes[0, 1].set_title("Local C_phi Field")
    axes[0, 1].set_aspect('equal')
    
    axes[0, 2].hist(highest["c_phi_field"][~np.isnan(highest["c_phi_field"])], bins=30, color='green', alpha=0.7)
    axes[0, 2].axvline(highest["local_95th"], color='red', linestyle='--', label=f"95th: {highest['local_95th']:.3f}")
    axes[0, 2].set_title("Local C_phi Distribution")
    axes[0, 2].legend()
    
    # Lowest Case
    axes[1, 0].pcolormesh(lowest["X"], lowest["Y"], lowest["speed_field"], cmap='plasma', shading='auto')
    axes[1, 0].set_title(f"LOWEST Global C_phi: {lowest['filename']}\n(Global = {lowest['global_c_phi']:.3f}, Max Speed = {lowest['max_speed']:.1f} m/s)")
    axes[1, 0].set_aspect('equal')
    
    axes[1, 1].pcolormesh(lowest["X"], lowest["Y"], lowest["c_phi_field"], cmap='viridis', shading='auto', vmin=0.4, vmax=1.0)
    axes[1, 1].set_title("Local C_phi Field")
    axes[1, 1].set_aspect('equal')
    
    axes[1, 2].hist(lowest["c_phi_field"][~np.isnan(lowest["c_phi_field"])], bins=30, color='orange', alpha=0.7)
    axes[1, 2].axvline(lowest["local_95th"], color='red', linestyle='--', label=f"95th: {lowest['local_95th']:.3f}")
    axes[1, 2].set_title("Local C_phi Distribution")
    axes[1, 2].legend()
    
    plt.suptitle("Physical Interpretation: Highest vs Lowest Global Coherence Cases", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "cohort_deep_dive.png", dpi=200)
    plt.close()
    
    # Save analysis JSON
    # Remove large numpy arrays before saving
    for res in analysis_results:
        del res["c_phi_field"]
        del res["speed_field"]
        del res["X"]
        del res["Y"]
        
    analysis_report = {
        "milestone": "C_analysis",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_cases": analysis_results
    }
    
    report_path = OUTPUT_DIR / "cohort_analysis_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(analysis_report, f, indent=2)
        
    print(f"\n✅ Analysis complete.")
    print(f"  → Ranking plot: {OUTPUT_DIR / 'cohort_global_ranking.png'}")
    print(f"  → Deep dive plot: {OUTPUT_DIR / 'cohort_deep_dive.png'}")
    print(f"  → Stats report: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_analysis()