"""
TRACEBIND-Albatross: Milestone C - Real ERA5 Correlation Analysis
=================================================================
Validation Status: [ ] Untested  [X] Characterized  [ ] Frozen  [ ] Published

Purpose: Test Hypothesis H2 on real observational data.
"Do TRACEBIND descriptors correlate with independently measured atmospheric 
state variables relevant to flight?"

CRITICAL DOCUMENTATION - Global vs Local C_phi:
-----------------------------------------------
This script computes TWO distinct descriptors:

1. GLOBAL C_phi: Computed over the entire domain, referenced to the 
   max-vorticity estimated center. Measures whole-system rotational coherence.

2. LOCAL C_phi field: Computed via Derived Procedure A1 (sliding window).
   Each window's C_phi is referenced to ITS OWN MIDPOINT, NOT the global center.
   This measures local rotational organization at each grid location.

These are physically different quantities. The local field is used for 
spatial correlation with independent atmospheric variables.

STATISTICAL CAVEAT:
-------------------
Correlation p-values reported here are DESCRIPTIVE, not definitive.
Because we correlate thousands of spatially adjacent pixels, spatial 
autocorrelation causes standard p-values to be misleadingly small.
For publication-quality inference, a block bootstrap or effective sample 
size correction would be required. The correlation coefficients (r, ρ) 
themselves remain informative.
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

# ============================================================================
# Configuration
# ============================================================================
DATA_FILE = r"C:\TRACEBIND-Albatross\data\raw\milestone_c_sample_mocha_20230515.nc"
OUTPUT_DIR = Path("outputs/milestone_C")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 9  # For Derived Procedure A1 (Local C_phi field)

# ============================================================================
# Helper Functions
# ============================================================================
def latlon_to_km(lat, lon):
    """Convert lat/lon to approximate local Cartesian coordinates (km)."""
    lat_rad = np.radians(lat)
    dy = (lat - np.mean(lat)) * 111.0
    dx = (lon - np.mean(lon)) * 111.0 * np.cos(np.mean(lat_rad))
    X, Y = np.meshgrid(dx, dy)
    return X, Y

def compute_vorticity(u, v, dx, dy):
    """Compute relative vorticity (dv/dx - du/dy)."""
    dvdx = np.gradient(v, dx, axis=1)
    dudy = np.gradient(u, dy, axis=0)
    return dvdx - dudy

def find_max_vorticity_center(X, Y, u, v):
    """Preprocessing Contract Rule 2: Max absolute vorticity center.
    NOTE: 3x3 Gaussian smoothing applied ONLY for center estimation (Rule 2.1).
    The unsmoothed fields are used for the actual C_phi computation."""
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    
    dx = X[0, 1] - X[0, 0]
    dy = Y[1, 0] - Y[0, 0]
    
    zeta = compute_vorticity(u_smooth, v_smooth, dx, dy)
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    
    return float(X[idx]), float(Y[idx]), float(np.abs(zeta[idx]))

# ============================================================================
# Main Execution
# ============================================================================
def run_milestone_c():
    print("=" * 80)
    print("MILESTONE C: REAL ERA5 CORRELATION ANALYSIS")
    print("=" * 80)
    
    print("\n[1/7] Loading real ERA5 data...")
    try:
        import xarray as xr
        ds = xr.open_dataset(DATA_FILE)
        
        u10 = ds['u10'].squeeze().values.astype('float64')
        v10 = ds['v10'].squeeze().values.astype('float64')
        msl = ds['msl'].squeeze().values.astype('float64') / 100.0  # Pa -> hPa
        
        lat = ds['latitude'].values.astype('float64')
        lon = ds['longitude'].values.astype('float64')
        
        X_km, Y_km = latlon_to_km(lat, lon)
        dx_km = X_km[0, 1] - X_km[0, 0]
        dy_km = Y_km[1, 0] - Y_km[0, 0]
        
        # Compute actual domain spans
        lat_span = float(lat.max() - lat.min())
        lon_span = float(lon.max() - lon.min())
        ns_height_km = float(abs(Y_km[-1, 0] - Y_km[0, 0]))
        ew_width_km = float(abs(X_km[0, -1] - X_km[0, 0]))
        
        ds.close()
        
        print(f"  → Loaded shape: {u10.shape}")
        print(f"  → Lat span: {lat_span:.2f}° ({ns_height_km:.0f} km N-S)")
        print(f"  → Lon span: {lon_span:.2f}° ({ew_width_km:.0f} km E-W)")
        print(f"  → Grid spacing: dx = {abs(dx_km):.2f} km, dy = {abs(dy_km):.2f} km")
        
        # Explicit grid orientation check
        lat_descending = bool(lat[0] > lat[-1])
        print(f"  → Latitude orientation: {'DESCENDING (N→S)' if lat_descending else 'ASCENDING (S→N)'}")
        print(f"  → dy_km sign: {dy_km:.4f} (negative = descending lat)")
        
        if abs(dx_km) < 1.0 or abs(dy_km) < 1.0:
            print("  ⚠️  WARNING: Grid spacing < 1 km. Check coordinate conversion.")
            
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False

    print("\n[2/7] Applying Preprocessing Contract (Rule 2.1): Center Estimation...")
    cx, cy, max_zeta = find_max_vorticity_center(X_km, Y_km, u10, v10)
    print(f"  → Estimated center (max |vorticity|): X={cx:.2f} km, Y={cy:.2f} km")
    print(f"  → Max |vorticity| at center: {max_zeta:.4e} s^-1")
    print(f"  → (3x3 Gaussian smoothing applied ONLY for this estimation step)")

    print("\n[3/7] Computing GLOBAL C_phi (frozen operator, unsmoothed fields)...")
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cx, cy))
    print(f"  → Global C_phi (referenced to estimated center) = {global_c_phi:.4f}")

    print("\n[4/7] Computing LOCAL C_phi field (Derived Procedure A1)...")
    print(f"  → Each window's C_phi is referenced to ITS OWN midpoint.")
    print(f"  → This differs from the global C_phi (different descriptor).")
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    c_phi_field = np.full((ny, nx), np.nan)
    
    total_steps = (nx - 2 * half_w) * (ny - 2 * half_w)
    step = 0
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            # center=None = window midpoint (local reference frame)
            c_phi_field[i, j] = compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win, center=None)
            
            step += 1
            if step % 200 == 0:
                print(f"  → Progress: {step}/{total_steps}")
                
    print("  → Local C_phi field computation complete.")

    print("\n[5/7] Computing independent atmospheric variables...")
    # Relative vorticity (directly related to operator's rotational sensitivity per A2b)
    dx_m = dx_km * 1000.0  # km -> m
    dy_m = dy_km * 1000.0
    vorticity = compute_vorticity(u10, v10, dx_m, dy_m)
    
    # Pressure gradient: hPa/m × 100,000 = hPa per 100 km
    grad_msl_x = np.gradient(msl, dx_m, axis=1)  # hPa/m
    grad_msl_y = np.gradient(msl, dy_m, axis=0)  # hPa/m
    grad_msl_mag_hPa_per_100km = np.sqrt(grad_msl_x**2 + grad_msl_y**2) * 100000.0
    
    print(f"  → Relative vorticity range: [{vorticity.min():.4e}, {vorticity.max():.4e}] s^-1")
    print(f"  → Pressure gradient range: [{grad_msl_mag_hPa_per_100km.min():.3f}, {grad_msl_mag_hPa_per_100km.max():.3f}] hPa/100km")

    print("\n[6/7] Calculating spatial correlations...")
    valid_mask = ~np.isnan(c_phi_field) & ~np.isnan(msl)
    c_phi_valid = c_phi_field[valid_mask]
    msl_valid = msl[valid_mask]
    grad_valid = grad_msl_mag_hPa_per_100km[valid_mask]
    vort_valid = vorticity[valid_mask]
    
    print(f"  → Valid pixels: {int(np.sum(valid_mask))}")
    
    pearson_msl, p_msl = stats.pearsonr(c_phi_valid, msl_valid)
    spearman_msl, p_msl_s = stats.spearmanr(c_phi_valid, msl_valid)
    
    pearson_grad, p_grad = stats.pearsonr(c_phi_valid, grad_valid)
    spearman_grad, p_grad_s = stats.spearmanr(c_phi_valid, grad_valid)
    
    pearson_vort, p_vort = stats.pearsonr(c_phi_valid, np.abs(vort_valid))
    spearman_vort, p_vort_s = stats.spearmanr(c_phi_valid, np.abs(vort_valid))
    
    print(f"\n  → Local C_phi vs MSL (hPa):")
    print(f"     Pearson  r = {pearson_msl:+.4f}  (p = {p_msl:.2e})")
    print(f"     Spearman ρ = {spearman_msl:+.4f}  (p = {p_msl_s:.2e})")
    
    print(f"\n  → Local C_phi vs |Pressure Gradient| (hPa/100km):")
    print(f"     Pearson  r = {pearson_grad:+.4f}  (p = {p_grad:.2e})")
    print(f"     Spearman ρ = {spearman_grad:+.4f}  (p = {p_grad_s:.2e})")
    
    print(f"\n  → Local C_phi vs |Relative Vorticity| (s^-1):")
    print(f"     Pearson  r = {pearson_vort:+.4f}  (p = {p_vort:.2e})")
    print(f"     Spearman ρ = {spearman_vort:+.4f}  (p = {p_vort_s:.2e})")
    
    print("\n  ⚠️  NOTE: p-values are DESCRIPTIVE only. Spatial autocorrelation")
    print("     makes them artificially small. Focus on r and ρ magnitudes.")

    print("\n[7/7] Generating visualizations and saving provenance report...")
    
    # Figure 1: Spatial Fields
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    
    im0 = axes[0, 0].pcolormesh(X_km, Y_km, msl, cmap='coolwarm', shading='auto')
    axes[0, 0].plot(cx, cy, 'k+', markersize=20, markeredgewidth=3, label=f"Center")
    axes[0, 0].set_title("Mean Sea Level Pressure (hPa)")
    axes[0, 0].legend()
    fig.colorbar(im0, ax=axes[0, 0])
    
    im1 = axes[0, 1].pcolormesh(X_km, Y_km, c_phi_field, cmap='viridis', shading='auto', vmin=0.5, vmax=1.0)
    axes[0, 1].set_title(f"Local C_phi Field (Window={WINDOW_SIZE}x{WINDOW_SIZE})")
    fig.colorbar(im1, ax=axes[0, 1], label="C_phi")
    
    im2 = axes[1, 0].pcolormesh(X_km, Y_km, grad_msl_mag_hPa_per_100km, cmap='plasma', shading='auto')
    axes[1, 0].set_title("Pressure Gradient Magnitude (hPa / 100 km)")
    fig.colorbar(im2, ax=axes[1, 0])
    
    im3 = axes[1, 1].pcolormesh(X_km, Y_km, np.abs(vorticity) * 1e5, cmap='magma', shading='auto')
    axes[1, 1].set_title("|Relative Vorticity| (×10⁻⁵ s⁻¹)")
    fig.colorbar(im3, ax=axes[1, 1])
    
    plt.suptitle(f"Milestone C: Real ERA5 Analysis — Cyclone Mocha, 2023-05-15 12:00 UTC\nGlobal C_phi = {global_c_phi:.4f}", 
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "spatial_fields_real.png", dpi=200)
    plt.close()
    
    # Figure 2: Scatter plots
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    axes[0].scatter(c_phi_valid, msl_valid, alpha=0.3, s=10, edgecolor='none')
    axes[0].set_xlabel("Local C_phi")
    axes[0].set_ylabel("MSL (hPa)")
    axes[0].set_title(f"vs MSL\nSpearman ρ = {spearman_msl:+.3f}")
    axes[0].grid(True, alpha=0.3)
    
    axes[1].scatter(c_phi_valid, grad_valid, alpha=0.3, s=10, edgecolor='none')
    axes[1].set_xlabel("Local C_phi")
    axes[1].set_ylabel("|Pressure Gradient| (hPa/100km)")
    axes[1].set_title(f"vs Pressure Gradient\nSpearman ρ = {spearman_grad:+.3f}")
    axes[1].grid(True, alpha=0.3)
    
    axes[2].scatter(c_phi_valid, np.abs(vort_valid) * 1e5, alpha=0.3, s=10, edgecolor='none')
    axes[2].set_xlabel("Local C_phi")
    axes[2].set_ylabel("|Relative Vorticity| (×10⁻⁵ s⁻¹)")
    axes[2].set_title(f"vs |Vorticity|\nSpearman ρ = {spearman_vort:+.3f}")
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "scatter_plots_real.png", dpi=200)
    plt.close()
    
    # Save JSON Provenance
    results = {
        "milestone": "C",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_file": Path(DATA_FILE).name,
        "domain": {
            "lat_span_deg": round(lat_span, 4),
            "lon_span_deg": round(lon_span, 4),
            "ns_height_km": round(ns_height_km, 2),
            "ew_width_km": round(ew_width_km, 2),
            "dx_km": round(abs(dx_km), 4),
            "dy_km": round(abs(dy_km), 4),
            "lat_orientation": "descending" if lat_descending else "ascending",
            "local_cartesian_approximation": "valid for this regional domain"
        },
        "preprocessing_contract": {
            "center_method": "max_vorticity",
            "center_estimation_smoothing": "3x3 Gaussian (sigma=0.8) applied ONLY for center finding",
            "estimated_center_km": [round(cx, 2), round(cy, 2)],
            "max_vorticity_at_center_s_inv": round(max_zeta, 6)
        },
        "descriptor_definitions": {
            "global_c_phi": "Frozen operator over entire domain, referenced to estimated circulation center",
            "local_c_phi_field": "Derived Procedure A1: sliding window, each window referenced to its OWN midpoint"
        },
        "derived_procedure_a1": {
            "window_size": WINDOW_SIZE,
            "window_center": "midpoint (None) - local reference frame"
        },
        "global_c_phi": round(global_c_phi, 6),
        "correlations": {
            "note": "p-values are descriptive only; spatial autocorrelation inflates significance",
            "msl_hPa": {
                "pearson_r": round(float(pearson_msl), 4),
                "pearson_p": f"{p_msl:.2e}",
                "spearman_rho": round(float(spearman_msl), 4),
                "spearman_p": f"{p_msl_s:.2e}"
            },
            "pressure_gradient_hPa_per_100km": {
                "pearson_r": round(float(pearson_grad), 4),
                "pearson_p": f"{p_grad:.2e}",
                "spearman_rho": round(float(spearman_grad), 4),
                "spearman_p": f"{p_grad_s:.2e}"
            },
            "abs_relative_vorticity_s_inv": {
                "pearson_r": round(float(pearson_vort), 4),
                "pearson_p": f"{p_vort:.2e}",
                "spearman_rho": round(float(spearman_vort), 4),
                "spearman_p": f"{p_vort_s:.2e}"
            }
        }
    }
    
    report_path = OUTPUT_DIR / "milestone_c_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n  → Report saved to {report_path}")
    print(f"  → Plots saved to {OUTPUT_DIR}")
    
    print("\n" + "=" * 80)
    print("✅ MILESTONE C COMPLETE")
    print("Real ERA5 correlation analysis finished.")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = run_milestone_c()
    if not success:
        sys.exit(1)