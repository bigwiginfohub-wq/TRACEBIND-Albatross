"""
TRACEBIND-Albatross: Milestone C - Real Data Center Perturbation Analysis
=========================================================================
Purpose: Quantify the robustness of the Global C_phi estimate on real ERA5 
data when the estimated center is perturbed by small grid shifts.

This validates the preprocessing contract on observational data, ensuring 
that minor estimation errors do not artificially inflate or deflate the 
descriptor.
"""

import sys
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
from scipy.ndimage import gaussian_filter

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

DATA_FILE = r"C:\TRACEBIND-Albatross\data\raw\milestone_c_sample_mocha_20230515.nc"
OUTPUT_DIR = Path("outputs/milestone_C")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    return idx[0], idx[1] # Return indices for easy grid shifting

def run_perturbation():
    print("=" * 80)
    print("MILESTONE C: REAL DATA CENTER PERTURBATION ANALYSIS")
    print("=" * 80)
    
    import xarray as xr
    ds = xr.open_dataset(DATA_FILE)
    u10 = ds['u10'].squeeze().values.astype('float64')
    v10 = ds['v10'].squeeze().values.astype('float64')
    lat = ds['latitude'].values.astype('float64')
    lon = ds['longitude'].values.astype('float64')
    ds.close()
    
    X_km, Y_km = latlon_to_km(lat, lon)
    dx_km = abs(X_km[0, 1] - X_km[0, 0])
    dy_km = abs(Y_km[1, 0] - Y_km[0, 0])
    
    print(f"\n[1/3] Finding baseline center...")
    base_i, base_j = find_max_vorticity_center(X_km, Y_km, u10, v10)
    base_cx, base_cy = float(X_km[base_i, base_j]), float(Y_km[base_i, base_j])
    
    base_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(base_cx, base_cy))
    print(f"  → Baseline center: grid ({base_i}, {base_j}) -> ({base_cx:.1f}, {base_cy:.1f}) km")
    print(f"  → Baseline Global C_phi = {base_c_phi:.4f}")
    
    print("\n[2/3] Perturbing center by ±1, ±2, ±3 grid cells...")
    shifts = [-3, -2, -1, 0, 1, 2, 3]
    results = []
    
    print(f"{'Shift (cells)':<15} | {'Shift (km)':<15} | {'Global C_phi':<12} | {'Delta'}")
    print("-" * 60)
    
    for shift in shifts:
        # Perturb in both X and Y simultaneously for a diagonal worst-case, 
        # or we can do a grid. Let's do a radial shift (diagonal) for simplicity.
        i_shift = base_i + shift
        j_shift = base_j + shift
        
        # Boundary check
        i_shift = max(0, min(u10.shape[0]-1, i_shift))
        j_shift = max(0, min(u10.shape[1]-1, j_shift))
        
        cx_shift = float(X_km[i_shift, j_shift])
        cy_shift = float(Y_km[i_shift, j_shift])
        
        dist_km = np.sqrt((cx_shift - base_cx)**2 + (cy_shift - base_cy)**2)
        
        c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cx_shift, cy_shift))
        delta = c_phi - base_c_phi
        
        results.append({
            "shift_cells": shift,
            "shift_km": round(dist_km, 2),
            "c_phi": round(c_phi, 4),
            "delta": round(delta, 4)
        })
        
        print(f"{shift:>4}, {shift:>4}       | {dist_km:>11.2f} km  | {c_phi:>12.4f} | {delta:+.4f}")
    
    print("\n[3/3] Generating visualization and saving report...")
    
    fig, ax = plt.subplots(figsize=(8, 5))
    shifts_km = [r["shift_km"] for r in results]
    cphis = [r["c_phi"] for r in results]
    
    ax.plot(shifts_km, cphis, 'o-', linewidth=2, markersize=8, color='#d62728')
    ax.axhline(base_c_phi, color='gray', linestyle='--', alpha=0.7, label=f'Baseline ({base_c_phi:.4f})')
    ax.set_xlabel("Center Perturbation Distance (km)")
    ax.set_ylabel("Global C_phi")
    ax.set_title("Real Data: Center Perturbation Sensitivity")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "center_perturbation_real.png", dpi=200)
    plt.close()
    
    report = {
        "milestone": "C_perturbation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_file": Path(DATA_FILE).name,
        "baseline": {"grid": [int(base_i), int(base_j)], "km": [round(base_cx, 2), round(base_cy, 2)], "c_phi": round(base_c_phi, 4)},
        "perturbations": results
    }
    
    report_path = OUTPUT_DIR / "center_perturbation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n✅ Analysis complete. Report saved to {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_perturbation()