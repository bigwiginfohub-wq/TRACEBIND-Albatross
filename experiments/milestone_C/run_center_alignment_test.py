"""
TRACEBIND-Albatross: Milestone C - Center Alignment Test
========================================================
Purpose: Test the Two-Scale Interpretation hypothesis.

Hypothesis: High Global Cφ storms have local vorticity centers tightly 
clustered around the global center. Low Global Cφ storms have local 
vorticity centers scattered across the domain.
"""

import sys
import json
import numpy as np
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

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
    return float(X[idx]), float(Y[idx]), idx[0], idx[1]

def analyze_alignment(filepath):
    import xarray as xr
    ds = xr.open_dataset(filepath)
    u10 = ds['u10'].squeeze().values.astype('float64')
    v10 = ds['v10'].squeeze().values.astype('float64')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    ds.close()
    
    X_km, Y_km = latlon_to_km(lat, lon)
    
    # 1. Find Global Center
    global_cx, global_cy, global_i, global_j = find_max_vorticity_center(X_km, Y_km, u10, v10)
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(global_cx, global_cy))
    
    # 2. Slide window and find LOCAL center for each
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    
    distances_to_global = []
    local_c_phis = []
    
    # Pre-compute global vorticity field for speed (optional, but we need local)
    dx_km = abs(X_km[0, 1] - X_km[0, 0])
    dy_km = abs(Y_km[1, 0] - Y_km[0, 0])
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            # Local C_phi (relative to window midpoint)
            c_phi = compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win, center=None)
            local_c_phis.append(c_phi)
            
            # Local Vorticity Center
            _, _, loc_i, loc_j = find_max_vorticity_center(x_win, y_win, u_win, v_win)
            
            # Convert local grid indices back to global grid indices
            abs_i = (i - half_w) + loc_i
            abs_j = (j - half_w) + loc_j
            
            # Distance from this local center to the global center
            dist = np.sqrt((X_km[abs_i, abs_j] - global_cx)**2 + (Y_km[abs_i, abs_j] - global_cy)**2)
            distances_to_global.append(dist)
            
    return {
        "filename": Path(filepath).name,
        "global_c_phi": round(global_c_phi, 4),
        "distances": np.array(distances_to_global),
        "local_c_phis": np.array(local_c_phis),
        "global_center": (global_cx, global_cy)
    }

def run_test():
    print("=" * 80)
    print("MILESTONE C: CENTER ALIGNMENT TEST")
    print("=" * 80)
    
    # Analyze Highest and Lowest cases from previous run
    high_file = DATA_DIR / "c2_uuid_ec81d97e.nc"   # Global C_phi = 0.9331
    low_file = DATA_DIR / "c2_uuid_dc364aad.nc"    # Global C_phi = 0.4384
    
    print("\n[1/2] Analyzing HIGHEST Global C_phi case (0.9331)...")
    high_res = analyze_alignment(high_file)
    print(f"  → Processed {len(high_res['distances'])} local windows.")
    
    print("\n[2/2] Analyzing LOWEST Global C_phi case (0.4384)...")
    low_res = analyze_alignment(low_file)
    print(f"  → Processed {len(low_res['distances'])} local windows.")
    
    print("\n[3/3] Generating comparative visualizations...")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Histogram of distances
    bins = np.linspace(0, 600, 30)
    axes[0].hist(high_res["distances"], bins=bins, alpha=0.7, label=f"HIGH Global (μ={np.mean(high_res['distances']):.0f} km)", color='green')
    axes[0].hist(low_res["distances"], bins=bins, alpha=0.7, label=f"LOW Global (μ={np.mean(low_res['distances']):.0f} km)", color='orange')
    axes[0].set_xlabel("Distance from Local Vorticity Center to Global Center (km)")
    axes[0].set_ylabel("Frequency (Number of Windows)")
    axes[0].set_title("Distribution of Local Center Alignment")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Scatter: Local C_phi vs Distance to Global Center
    # Subsample for visibility (e.g., 1 in 5 points)
    step = 5
    axes[1].scatter(high_res["distances"][::step], high_res["local_c_phis"][::step], 
                    alpha=0.3, s=10, label="HIGH Global Case", color='green')
    axes[1].scatter(low_res["distances"][::step], low_res["local_c_phis"][::step], 
                    alpha=0.3, s=10, label="LOW Global Case", color='orange')
    
    axes[1].set_xlabel("Distance from Local Vorticity Center to Global Center (km)")
    axes[1].set_ylabel("Local C_phi (window midpoint reference)")
    axes[1].set_title("Local Coherence vs. Alignment with Global Center")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.suptitle("Testing the Two-Scale Interpretation Hypothesis", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "center_alignment_test.png", dpi=200)
    plt.close()
    
    # Save stats
    stats = {
        "high_global_case": {
            "filename": high_res["filename"],
            "global_c_phi": high_res["global_c_phi"],
            "mean_distance_to_global_center_km": round(float(np.mean(high_res["distances"])), 2),
            "std_distance_km": round(float(np.std(high_res["distances"])), 2),
            "median_distance_km": round(float(np.median(high_res["distances"])), 2)
        },
        "low_global_case": {
            "filename": low_res["filename"],
            "global_c_phi": low_res["global_c_phi"],
            "mean_distance_to_global_center_km": round(float(np.mean(low_res["distances"])), 2),
            "std_distance_km": round(float(np.std(low_res["distances"])), 2),
            "median_distance_km": round(float(np.median(low_res["distances"])), 2)
        }
    }
    
    report_path = OUTPUT_DIR / "center_alignment_stats.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"HIGH Global Case Mean Distance: {stats['high_global_case']['mean_distance_to_global_center_km']:>6.1f} km (Std: {stats['high_global_case']['std_distance_km']:.1f})")
    print(f"LOW  Global Case Mean Distance: {stats['low_global_case']['mean_distance_to_global_center_km']:>6.1f} km (Std: {stats['low_global_case']['std_distance_km']:.1f})")
    print("=" * 80)
    print(f"✅ Visualizations saved to {OUTPUT_DIR / 'center_alignment_test.png'}")
    print("=" * 80)

if __name__ == "__main__":
    run_test()