"""
TRACEBIND-Albatross: Milestone D - Incremental Information Analysis
====================================================================
Purpose: Test whether Global Cφ provides explanatory power for geometric 
organization beyond conventional wind diagnostics and baseline local coherence.

Target: Median center distance (geometrically independent metric)
Predictors: Max Vorticity, Mean Local Cφ, Global Cφ
Dataset: 20-case blinded ERA5 cohort (u10, v10 only)
"""

import sys
import json
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
import xarray as xr
from scipy.ndimage import gaussian_filter

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

DATA_DIR = Path(r"C:\TRACEBIND-Atmosphere\phase8\c2\raw")
OUTPUT_DIR = Path("outputs/milestone_D")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 9

def compute_vorticity_corrected(u, v, x_1d, y_1d):
    """Robust vorticity using coordinate arrays (immune to ascending/descending grids)."""
    dvdx = np.gradient(v, x_1d, axis=1)
    dudy = np.gradient(u, y_1d, axis=0)
    return dvdx - dudy

def find_center_corrected(u, v, X, Y):
    """Find max vorticity center with smoothing."""
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    x_1d = X[0, :]
    y_1d = Y[:, 0]
    zeta = compute_vorticity_corrected(u_smooth, v_smooth, x_1d, y_1d)
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    return float(X[idx]), float(Y[idx]), float(np.max(np.abs(zeta)))

def extract_features(filepath):
    """Extract all features for one case using ONLY u10 and v10."""
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
    x_1d = X_km[0, :]
    y_1d = Y_km[:, 0]
    
    # 1. Max vorticity (conventional wind diagnostic)
    u_smooth = gaussian_filter(u10, sigma=0.8)
    v_smooth = gaussian_filter(v10, sigma=0.8)
    zeta = compute_vorticity_corrected(u_smooth, v_smooth, x_1d, y_1d)
    max_vort = float(np.max(np.abs(zeta)))
    
    # 2. Global Cφ
    cor_cx, cor_cy, _ = find_center_corrected(u10, v10, X_km, Y_km)
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cor_cx, cor_cy))
    
    # 3. Local Cφ field statistics & Median Center Distance
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    window_data = []
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            # Local Cφ (referenced to window midpoint)
            c_phi = compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win, center=None)
            
            # Local max vorticity for filtering
            u_w_smooth = gaussian_filter(u_win, sigma=0.8)
            v_w_smooth = gaussian_filter(v_win, sigma=0.8)
            zeta_w = compute_vorticity_corrected(u_w_smooth, v_w_smooth, x_win[0,:], y_win[:,0])
            max_zeta = float(np.max(np.abs(zeta_w)))
            
            # Distance to global center
            loc_i, loc_j = np.unravel_index(np.argmax(np.abs(zeta_w)), zeta_w.shape)
            abs_i = (i - half_w) + loc_i
            abs_j = (j - half_w) + loc_j
            dist = np.sqrt((X_km[abs_i, abs_j] - cor_cx)**2 + (Y_km[abs_i, abs_j] - cor_cy)**2)
            
            window_data.append({
                "c_phi": c_phi,
                "max_zeta": max_zeta,
                "dist": dist
            })
    
    # Filter: Keep strongest 80% of windows by vorticity (explicit and clear)
    window_data.sort(key=lambda w: w["max_zeta"], reverse=True)
    n_keep = int(len(window_data) * 0.80)
    valid_windows = window_data[:n_keep]
    
    mean_local_c_phi = float(np.mean([w["c_phi"] for w in valid_windows]))
    median_center_distance = float(np.median([w["dist"] for w in valid_windows]))
    
    return {
        "filename": filepath.name,
        "max_vorticity": max_vort,
        "mean_local_c_phi": mean_local_c_phi,
        "global_c_phi": global_c_phi,
        "median_center_distance": median_center_distance
    }

def run_incremental_value_test():
    print("=" * 85)
    print("MILESTONE D: INCREMENTAL INFORMATION ANALYSIS")
    print("=" * 85)
    print("Testing if Global Cφ explains geometric organization beyond conventional")
    print("wind diagnostics (max vorticity) and baseline local coherence (mean local Cφ).")
    print("Target: Median Center Distance\n")
    
    nc_files = sorted(DATA_DIR.glob("*.nc"))
    print(f"Extracting features from {len(nc_files)} cases...\n")
    
    features = []
    for i, filepath in enumerate(nc_files, 1):
        print(f"[{i}/{len(nc_files)}] {filepath.name}...", end=" ")
        try:
            feat = extract_features(filepath)
            features.append(feat)
            print(f"OK (Global Cφ={feat['global_c_phi']:.4f})")
        except Exception as e:
            print(f"FAILED ({e})")
    
    if len(features) < 4:
        print("\n❌ Not enough successful cases to run regression.")
        return
        
    df = pd.DataFrame(features)
    
    # Save feature dataframe for supplementary material
    csv_path = OUTPUT_DIR / "milestone_d_features.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✅ Feature dataframe saved to {csv_path}")
    
    # 1. Correlation Matrix Check
    print("\n" + "=" * 85)
    print("MULTICOLLINEARITY CHECK: Correlation Matrix")
    print("=" * 85)
    cols_to_check = ["max_vorticity", "mean_local_c_phi", "global_c_phi", "median_center_distance"]
    corr_matrix = df[cols_to_check].corr()
    print(corr_matrix.round(3))
    
    # 2. Variance Inflation Factor (VIF) Check for Model D predictors
    print("\n" + "=" * 85)
    print("MULTICOLLINEARITY CHECK: Variance Inflation Factor (VIF)")
    print("=" * 85)
    X_vif = df[["max_vorticity", "mean_local_c_phi", "global_c_phi"]]
    X_vif = sm.add_constant(X_vif)
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X_vif.columns
    vif_data["VIF"] = [variance_inflation_factor(X_vif.values, i) for i in range(X_vif.shape[1])]
    print(vif_data.to_string(index=False))
    print("(Note: VIF > 5 or 10 indicates problematic multicollinearity)")
    
    # 3. Nested Model Comparison
    print("\n" + "=" * 85)
    print("NESTED MODEL COMPARISON (Predicting Median Center Distance)")
    print("=" * 85)
    
    y = df["median_center_distance"]
    
    model_a = sm.OLS(y, sm.add_constant(df[["max_vorticity"]])).fit()
    model_b = sm.OLS(y, sm.add_constant(df[["mean_local_c_phi"]])).fit()
    model_c = sm.OLS(y, sm.add_constant(df[["max_vorticity", "mean_local_c_phi"]])).fit()
    model_d = sm.OLS(y, sm.add_constant(df[["max_vorticity", "mean_local_c_phi", "global_c_phi"]])).fit()
    
    print(f"\nModel A (Max Vorticity only):          Adj R² = {model_a.rsquared_adj:.4f}")
    print(f"Model B (Mean Local Cφ only):          Adj R² = {model_b.rsquared_adj:.4f}")
    print(f"Model C (Max Vort + Mean Local Cφ):    Adj R² = {model_c.rsquared_adj:.4f}")
    print(f"Model D (+ Global Cφ):                 Adj R² = {model_d.rsquared_adj:.4f}")
    
    # 4. Full Regression Summary for Model D
    print("\n" + "=" * 85)
    print("FULL REGRESSION SUMMARY: Model D")
    print("=" * 85)
    print(model_d.summary())
    
    # 5. Interpretation
    print("\n" + "=" * 85)
    print("INCREMENTAL INFORMATION ASSESSMENT")
    print("=" * 85)
    
    delta_r2 = model_d.rsquared_adj - model_c.rsquared_adj
    p_cphi = model_d.pvalues["global_c_phi"]
    coef_cphi = model_d.params["global_c_phi"]
    
    print(f"Adding Global Cφ to Model C changes Adjusted R² by: {delta_r2:+.4f}")
    print(f"Global Cφ coefficient in Model D: {coef_cphi:.4f} (p = {p_cphi:.4f})")
    
    print("\nInterpretation:")
    if p_cphi < 0.05 and delta_r2 > 0.01:
        print("✅ Global Cφ provides statistically significant incremental information.")
        print("   It explains variance in center distance that max vorticity and mean local Cφ miss.")
    elif delta_r2 > 0:
        print("⚠️  Global Cφ improves model fit slightly, but is not strictly significant (p > 0.05).")
        print("   Given N=20, statistical power is limited. The trend suggests potential incremental")
        print("   value, but a larger cohort is required for definitive confirmation.")
    else:
        print("❌ Global Cφ does not provide incremental information for this target.")
        print("   Conventional wind diagnostics and local coherence already capture the relevant variance.")
        print("   This is a valuable negative result that clarifies the operational boundaries of Cφ.")
    
    print("=" * 85)
    
    # Save JSON report
    report = {
        "milestone": "D_incremental_value",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "correlation_matrix": corr_matrix.round(4).to_dict(),
        "vif": vif_data.set_index("Feature")["VIF"].round(4).to_dict(),
        "models": {
            "A_max_vort": {"adj_r2": round(model_a.rsquared_adj, 4)},
            "B_mean_local_cphi": {"adj_r2": round(model_b.rsquared_adj, 4)},
            "C_combined": {"adj_r2": round(model_c.rsquared_adj, 4)},
            "D_with_global_cphi": {
                "adj_r2": round(model_d.rsquared_adj, 4),
                "delta_r2": round(delta_r2, 4),
                "global_cphi_coef": round(coef_cphi, 4),
                "global_cphi_pvalue": round(p_cphi, 4)
            }
        }
    }
    
    report_path = OUTPUT_DIR / "milestone_d_incremental_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ JSON Report saved to {report_path}")

if __name__ == "__main__":
    try:
        import statsmodels.api as sm
        import pandas as pd
    except ImportError:
        print("❌ Missing dependencies. Please run: pip install statsmodels pandas")
        sys.exit(1)
        
    run_incremental_value_test()