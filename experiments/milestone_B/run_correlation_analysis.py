"""
TRACEBIND-Albatross: Milestone B - Atmospheric Correlation Analysis (Optimized)
===============================================================================
Purpose: Test H2 using Derived Analysis Procedure A1 (sliding window).
"""
import sys
import json
import numpy as np
from pathlib import Path

print("DEBUG 1: Script started.")

try:
    import scipy.stats as stats
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    print("DEBUG 2: SciPy and Matplotlib imported successfully.")
except Exception as e:
    print(f"DEBUG ERROR: Import failed. Please run: pip install scipy matplotlib")
    print(f"Details: {e}")
    sys.exit(1)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))
print("DEBUG 3: Source path appended.")

try:
    from src.tracebind.frozen_operators import compute_phase_coherence
    print("DEBUG 4: Frozen operator imported successfully.")
except Exception as e:
    print(f"DEBUG ERROR: Could not import frozen_operators. Details: {e}")
    sys.exit(1)

print("=" * 60)
print("MILESTONE B: ATMOSPHERIC CORRELATION ANALYSIS")
print("=" * 60)

print("\n[1/4] Generating synthetic atmospheric field (50x50 grid)...")
nx, ny = 50, 50
x = np.linspace(-50.0, 50.0, nx)
y = np.linspace(-50.0, 50.0, ny)
X, Y = np.meshgrid(x, y)

# Background Jet
U_jet = 20.0 / np.cosh(Y / 15.0)**2
V_jet = np.zeros_like(Y)

# Embedded Vortex
cx, cy = 10.0, 0.0
R = np.sqrt((X - cx)**2 + (Y - cy)**2) + 1e-12
r0, gamma = 15.0, 8e4
v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
U_vort = -v_theta * (Y - cy) / R
V_vort = v_theta * (X - cx) / R

u = U_jet + U_vort
v = V_jet + V_vort

# Vertical Velocity (w) correlated with vortex
np.random.seed(42)
w_core = 0.5 * np.exp(-((R / 20.0)**2))
w = w_core + np.random.normal(0, 0.05, u.shape)
print("  → Field generated.")

print("[2/4] Computing spatially resolved C_phi field (9x9 sliding window)...")
window_size = 9
c_phi_field = np.full((ny, nx), np.nan)
half_w = window_size // 2

total_steps = (nx - 2 * half_w) * (ny - 2 * half_w)
step = 0

for i in range(half_w, ny - half_w):
    for j in range(half_w, nx - half_w):
        u_win = u[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
        v_win = v[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
        x_win = X[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
        y_win = Y[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
        
        c_phi_field[i, j] = compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win)
        
        step += 1
        if step % 400 == 0:
            print(f"  → Progress: {step}/{total_steps}")

print("  → C_phi field computation complete.")

print("[3/4] Calculating spatial correlations...")
valid_mask = ~np.isnan(c_phi_field) & ~np.isnan(w)
c_phi_valid = c_phi_field[valid_mask]
w_valid = w[valid_mask]

pearson_w, pval_w = stats.pearsonr(c_phi_valid, w_valid)
spearman_w, pval_w_s = stats.spearmanr(c_phi_valid, w_valid)

print(f"  → C_phi vs Vertical Velocity (w):")
print(f"     Pearson  r = {pearson_w:7.4f}  (p = {pval_w:.6f})")
print(f"     Spearman ρ = {spearman_w:7.4f}  (p = {pval_w_s:.6f})")

print("[4/4] Saving report...")
OUTPUT_DIR = Path("outputs/milestone_B")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

results = {
    "milestone": "B",
    "grid_size": f"{nx}x{ny}",
    "window_size": window_size,
    "n_valid_pixels": int(np.sum(valid_mask)),
    "correlations": {
        "vertical_velocity_w": {
            "pearson_r": round(float(pearson_w), 4),
            "pearson_p": round(float(pval_w), 6),
            "spearman_rho": round(float(spearman_w), 4),
            "spearman_p": round(float(pval_w_s), 6)
        }
    }
}

report_path = OUTPUT_DIR / "correlation_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"  → Report saved to {report_path}")
print("\n" + "=" * 60)
print("✅ MILESTONE B COMPLETE")
print("=" * 60)