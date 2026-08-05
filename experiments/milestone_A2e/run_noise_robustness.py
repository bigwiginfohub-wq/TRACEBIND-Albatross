"""
TRACEBIND-Albatross: Milestone A2e - Noise Robustness Benchmark
===============================================================
Validation Status: [ ] Untested  [ ] Characterized  [ ] Frozen  [ ] Published

Purpose: Quantify the operational limits of the center estimation + frozen 
operator pipeline under realistic measurement noise.

Produces two critical curves:
  1. Center error vs. noise level (how well can we find the center?)
  2. Descriptor error vs. noise level (how much does Cφ degrade?)

These curves define the operational envelope of the instrument before
deployment on real ERA5 data.
"""

import sys
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

OUTPUT_DIR = Path("outputs/milestone_A2e")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Synthetic Vortex with Known True Center
# ============================================================================
def build_grid(nx=100, ny=100, span=100.0):
    x = np.linspace(-span/2, span/2, nx)
    y = np.linspace(-span/2, span/2, ny)
    return np.meshgrid(x, y)

def lamb_oseen_vortex(X, Y, cx=0.0, cy=0.0, r0=15.0, gamma=1e5):
    R = np.sqrt((X - cx)**2 + (Y - cy)**2) + 1e-12
    v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
    u = -v_theta * (Y - cy) / R
    v = v_theta * (X - cx) / R
    return u, v

def estimate_max_vorticity_center(X, Y, u, v):
    dx = X[0, 1] - X[0, 0]
    dy = Y[1, 0] - Y[0, 0]
    dvdx = np.gradient(v, dx, axis=1)
    dudy = np.gradient(u, dy, axis=0)
    vorticity = dvdx - dudy
    idx = np.unravel_index(np.argmax(np.abs(vorticity)), vorticity.shape)
    return (float(X[idx]), float(Y[idx]))

# ============================================================================
# Main Benchmark
# ============================================================================
def run_noise_robustness():
    print("=" * 80)
    print("MILESTONE A2e: NOISE ROBUSTNESS BENCHMARK")
    print("=" * 80)
    
    np.random.seed(42)
    X, Y = build_grid(nx=100, ny=100, span=100.0)
    
    # Baseline: clean vortex at (0, 0)
    u_clean, v_clean = lamb_oseen_vortex(X, Y, cx=0.0, cy=0.0, r0=15.0, gamma=1e5)
    true_center = (0.0, 0.0)
    
    # Noise levels (as fraction of field std)
    noise_levels = [0.0, 0.05, 0.10, 0.20, 0.50, 1.00, 2.00]
    n_replicates = 30
    
    results = {
        "milestone": "A2e",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_replicates": n_replicates,
        "noise_levels": []
    }
    
    print(f"\nTesting {len(noise_levels)} noise levels x {n_replicates} replicates...")
    print(f"{'Noise %':<10} | {'Center Err':<12} | {'Cφ Mean':<10} | {'Cφ Std':<10}")
    print("-" * 55)
    
    for noise_frac in noise_levels:
        center_errors = []
        cphi_values = []
        
        std_u = np.std(u_clean)
        std_v = np.std(v_clean)
        
        for _ in range(n_replicates):
            # Add noise
            u_noisy = u_clean + np.random.normal(0, noise_frac * std_u, u_clean.shape)
            v_noisy = v_clean + np.random.normal(0, noise_frac * std_v, v_clean.shape)
            
            # Estimate center
            est_center = estimate_max_vorticity_center(X, Y, u_noisy, v_noisy)
            center_err = np.sqrt((est_center[0] - true_center[0])**2 + 
                                (est_center[1] - true_center[1])**2)
            center_errors.append(center_err)
            
            # Compute Cφ with estimated center
            c_phi = compute_phase_coherence(u_noisy, v_noisy, X=X, Y=Y, center=est_center)
            cphi_values.append(c_phi)
        
        mean_err = float(np.mean(center_errors))
        std_err = float(np.std(center_errors))
        mean_cphi = float(np.mean(cphi_values))
        std_cphi = float(np.std(cphi_values))
        
        results["noise_levels"].append({
            "noise_fraction": noise_frac,
            "center_error_mean": round(mean_err, 4),
            "center_error_std": round(std_err, 4),
            "cphi_mean": round(mean_cphi, 6),
            "cphi_std": round(std_cphi, 6)
        })
        
        print(f"{noise_frac*100:6.0f}%   | {mean_err:8.4f} ± {std_err:.3f}  | {mean_cphi:8.4f}   | {std_cphi:.4f}")
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    noise_pcts = [e["noise_fraction"] * 100 for e in results["noise_levels"]]
    center_errs = [e["center_error_mean"] for e in results["noise_levels"]]
    center_errs_std = [e["center_error_std"] for e in results["noise_levels"]]
    cphi_means = [e["cphi_mean"] for e in results["noise_levels"]]
    cphi_stds = [e["cphi_std"] for e in results["noise_levels"]]
    
    # Plot 1: Center error vs noise
    ax1.errorbar(noise_pcts, center_errs, yerr=center_errs_std, 
                 marker='o', capsize=5, linewidth=2, color='#d62728')
    ax1.set_xlabel("Noise Level (% of field std)")
    ax1.set_ylabel("Center Estimation Error (units)")
    ax1.set_title("A2e: Center Error vs. Noise")
    ax1.grid(True, alpha=0.3)
    ax1.axhline(1.0, color='gray', linestyle='--', alpha=0.5, label='Sub-grid threshold')
    ax1.legend()
    
    # Plot 2: Cφ vs noise
    ax2.errorbar(noise_pcts, cphi_means, yerr=cphi_stds, 
                 marker='s', capsize=5, linewidth=2, color='#1f77b4')
    ax2.set_xlabel("Noise Level (% of field std)")
    ax2.set_ylabel("Cφ (mean ± std)")
    ax2.set_title("A2e: Descriptor Degradation vs. Noise")
    ax2.grid(True, alpha=0.3)
    ax2.axhline(0.65, color='gray', linestyle='--', alpha=0.5, label='Background shear baseline')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "noise_robustness.png", dpi=200)
    plt.close()
    
    # Save JSON
    report_path = Path("experiments/milestone_A2e/noise_robustness_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Interpretation
    print("\n" + "=" * 80)
    print("OPERATIONAL LIMITS")
    print("=" * 80)
    
    # Find the noise level where center error exceeds 5 units (significant degradation)
    for entry in results["noise_levels"]:
        if entry["center_error_mean"] > 5.0:
            print(f"\n⚠️  OPERATIONAL LIMIT: At {entry['noise_fraction']*100:.0f}% noise,")
            print(f"   center estimation error exceeds 5 units ({entry['center_error_mean']:.2f})")
            print(f"   and Cφ degrades to {entry['cphi_mean']:.4f}")
            break
    else:
        print("\n✅ ROBUST: Center estimation remains accurate (< 5 units error)")
        print("   across all tested noise levels (up to 200% of field std).")
    
    print("=" * 80)
    print(f"✓ Report saved to {report_path}")
    print(f"✓ Visualization saved to {OUTPUT_DIR / 'noise_robustness.png'}")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    run_noise_robustness()