"""
TRACEBIND-Albatross: Milestone A2a - Operator Characterization
==============================================================
Validation Status: [ ] Untested  [ ] Characterized  [ ] Frozen  [ ] Published

Purpose: Rigorously characterize the frozen TRACEBIND operator with:
  - Statistical uncertainty (mean, std, 95% CI) on all measurements
  - Multiple independent null models
  - Explicit, programmatically-evaluated acceptance criteria
  - Automatic visualization (PNG)
  - Full provenance capture
  
CRITICAL: This script does NOT print "SUCCESS" unconditionally.
It evaluates objective criteria and reports PASS/FAIL for each.
"""

import sys
import json
import csv
import platform
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for PNG generation
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
from scipy import stats

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

# ============================================================================
# Configuration
# ============================================================================
RANDOM_SEED = 42
N_BASELINE_REPEATS = 20
N_NOISE_REPLICATES = 50
N_NULL_ITERATIONS = 200
NOISE_LEVELS = [0.0, 0.05, 0.10, 0.20, 0.50, 1.00]
R0_VALUES = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0, 60.0]
OUTPUT_DIR = Path("outputs/milestone_A2a")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Synthetic Flow Generators
# ============================================================================
def build_grid(nx=100, ny=100, span=100.0):
    x = np.linspace(-span/2, span/2, nx)
    y = np.linspace(-span/2, span/2, ny)
    X, Y = np.meshgrid(x, y)
    return X, Y

def lamb_oseen_vortex(X, Y, r0=20.0, gamma=1e5):
    R = np.sqrt(X**2 + Y**2) + 1e-12
    v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
    u = -v_theta * (Y / R)
    v = v_theta * (X / R)
    return u, v

# ============================================================================
# Null Model Implementations
# ============================================================================
def null_fourier_phase_scramble(u, v, rng):
    """Preserves amplitude spectrum, destroys phase alignment."""
    def scramble(field):
        fft = np.fft.fft2(field)
        amp = np.abs(fft)
        phase = rng.uniform(0, 2 * np.pi, fft.shape)
        return np.real(np.fft.ifft2(amp * np.exp(1j * phase)))
    return scramble(u), scramble(v)

def null_spatial_shuffle(u, v, rng):
    """Randomly permutes grid cells, destroying spatial structure."""
    u_flat = u.flatten().copy()
    v_flat = v.flatten().copy()
    idx = rng.permutation(u_flat.size)
    return u_flat[idx].reshape(u.shape), v_flat[idx].reshape(v.shape)

def null_vector_direction_randomize(u, v, rng):
    """Preserves speed magnitude, randomizes direction."""
    speed = np.sqrt(u**2 + v**2)
    angle = rng.uniform(0, 2 * np.pi, u.shape)
    return speed * np.cos(angle), speed * np.sin(angle)

def null_uniform_noise(u, v, rng):
    """Pure white noise, no structure."""
    return rng.standard_normal(u.shape) * 10.0, rng.standard_normal(v.shape) * 10.0

# ============================================================================
# Statistical Helpers
# ============================================================================
def compute_stats(values):
    arr = np.array(values)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    if len(arr) > 1:
        ci = stats.t.interval(0.95, len(arr)-1, loc=mean, scale=stats.sem(arr))
    else:
        ci = (mean, mean)
    cv = (std / mean) if mean > 1e-9 else 0.0
    return {
        "mean": round(mean, 6),
        "std": round(std, 6),
        "ci_95_lower": round(ci[0], 6),
        "ci_95_upper": round(ci[1], 6),
        "cv": round(cv, 6),
        "n": len(arr)
    }

# ============================================================================
# Main Characterization
# ============================================================================
def run_characterization():
    print("=" * 75)
    print("MILESTONE A2a: OPERATOR CHARACTERIZATION (RIGOROUS)")
    print("=" * 75)
    
    rng = np.random.default_rng(RANDOM_SEED)
    X, Y = build_grid(nx=100, ny=100, span=100.0)
    
    # ---- Provenance ----
    provenance = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": stats.__name__.split('.')[0] if hasattr(stats, '__name__') else "unknown",
        "random_seed": RANDOM_SEED,
        "n_baseline_repeats": N_BASELINE_REPEATS,
        "n_noise_replicates": N_NOISE_REPLICATES,
        "n_null_iterations": N_NULL_ITERATIONS,
    }
    
    results = {
        "milestone": "A2a",
        "provenance": provenance,
        "baseline": {},
        "noise_sweep": [],
        "radius_sweep": [],
        "null_models": {},
        "acceptance_criteria": {}
    }
    
    # ---- 1. Baseline with uncertainty ----
    print("\n[1/6] Baseline stability (Lamb-Oseen, 20 repeats with numerical jitter)...")
    u_base, v_base = lamb_oseen_vortex(X, Y, r0=20.0, gamma=1e5)
    baseline_cphis = []
    for i in range(N_BASELINE_REPEATS):
        # Tiny numerical jitter to test floating-point stability
        jitter_u = u_base + rng.normal(0, 1e-10, u_base.shape)
        jitter_v = v_base + rng.normal(0, 1e-10, v_base.shape)
        baseline_cphis.append(compute_phase_coherence(jitter_u, jitter_v, X=X, Y=Y))
    
    baseline_stats = compute_stats(baseline_cphis)
    results["baseline"] = baseline_stats
    print(f"  → Mean: {baseline_stats['mean']:.6f} ± {baseline_stats['std']:.6f}")
    print(f"  → 95% CI: [{baseline_stats['ci_95_lower']:.6f}, {baseline_stats['ci_95_upper']:.6f}]")
    print(f"  → CV: {baseline_stats['cv']*100:.4f}%")
    
    # ---- 2. Noise sweep with replicates ----
    print("\n[2/6] Gaussian noise sweep (50 replicates per level)...")
    noise_csv_rows = []
    for level in NOISE_LEVELS:
        replicates = []
        for _ in range(N_NOISE_REPLICATES):
            std_u = np.std(u_base) if np.std(u_base) > 1e-5 else 1.0
            std_v = np.std(v_base) if np.std(v_base) > 1e-5 else 1.0
            u_noisy = u_base + rng.normal(0, level * std_u, u_base.shape)
            v_noisy = v_base + rng.normal(0, level * std_v, v_base.shape)
            c = compute_phase_coherence(u_noisy, v_noisy, X=X, Y=Y)
            replicates.append(c)
            noise_csv_rows.append({"noise_fraction": level, "c_phi": c})
        stats_dict = compute_stats(replicates)
        stats_dict["noise_fraction"] = level
        results["noise_sweep"].append(stats_dict)
        print(f"  → Noise {level*100:4.0f}%: {stats_dict['mean']:.4f} ± {stats_dict['std']:.4f}")
    
    # Save CSV
    csv_path = OUTPUT_DIR / "noise_sweep_replicates.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["noise_fraction", "c_phi"])
        writer.writeheader()
        writer.writerows(noise_csv_rows)
    
    # ---- 3. Radius sweep (fine-grained) ----
    print("\n[3/6] Lamb-Oseen core radius sweep (fine-grained)...")
    for r0 in R0_VALUES:
        u_r, v_r = lamb_oseen_vortex(X, Y, r0=r0, gamma=1e5)
        c = compute_phase_coherence(u_r, v_r, X=X, Y=Y)
        results["radius_sweep"].append({"core_radius": r0, "c_phi": round(c, 6)})
        print(f"  → r0 = {r0:4.1f}: C_phi = {c:.6f}")
    
    # ---- 4. Multiple null models ----
    print("\n[4/6] Multiple null models (200 iterations each)...")
    null_models = {
        "fourier_phase_scramble": null_fourier_phase_scramble,
        "spatial_shuffle": null_spatial_shuffle,
        "vector_direction_randomize": null_vector_direction_randomize,
        "uniform_noise": null_uniform_noise,
    }
    for name, func in null_models.items():
        null_cphis = []
        for _ in range(N_NULL_ITERATIONS):
            u_n, v_n = func(u_base, v_base, rng)
            null_cphis.append(compute_phase_coherence(u_n, v_n, X=X, Y=Y))
        stats_dict = compute_stats(null_cphis)
        results["null_models"][name] = stats_dict
        print(f"  → {name:30s}: {stats_dict['mean']:.4f} ± {stats_dict['std']:.4f}")
    
    # ---- 5. Acceptance criteria evaluation ----
    print("\n[5/6] Evaluating acceptance criteria...")
    criteria = {}
    
    # Criterion A: Baseline > Null Mean + 3σ for ALL null models
    crit_a_pass = True
    for name, ns in results["null_models"].items():
        threshold = ns["mean"] + 3 * ns["std"]
        if baseline_stats["mean"] <= threshold:
            crit_a_pass = False
            print(f"  ✗ Criterion A FAIL: baseline ({baseline_stats['mean']:.4f}) <= {name} threshold ({threshold:.4f})")
    criteria["A_baseline_exceeds_nulls_3sigma"] = {
        "status": "PASS" if crit_a_pass else "FAIL",
        "baseline_mean": baseline_stats["mean"],
        "thresholds": {name: round(ns["mean"] + 3 * ns["std"], 6) for name, ns in results["null_models"].items()}
    }
    print(f"  → Criterion A (Baseline > Null+3σ): {criteria['A_baseline_exceeds_nulls_3sigma']['status']}")
    
    # Criterion B: Noise response monotonically non-increasing (within 1σ bands)
    noise_means = [entry["mean"] for entry in results["noise_sweep"]]
    crit_b_pass = True
    for i in range(1, len(noise_means)):
        prev_upper = results["noise_sweep"][i-1]["mean"] + results["noise_sweep"][i-1]["std"]
        curr_mean = noise_means[i]
        # Allow small non-monotonicity within uncertainty
        if curr_mean > prev_upper + 0.01:
            crit_b_pass = False
    criteria["B_noise_response_monotonic"] = {"status": "PASS" if crit_b_pass else "FAIL"}
    print(f"  → Criterion B (Noise monotonic): {criteria['B_noise_response_monotonic']['status']}")
    
    # Criterion C: Radius response smooth (no jumps > 0.1 between adjacent points)
    r_cphis = [entry["c_phi"] for entry in results["radius_sweep"]]
    max_jump = max(abs(r_cphis[i] - r_cphis[i-1]) for i in range(1, len(r_cphis)))
    crit_c_pass = max_jump < 0.1
    criteria["C_radius_response_smooth"] = {"status": "PASS" if crit_c_pass else "FAIL", "max_jump": round(max_jump, 6)}
    print(f"  → Criterion C (Radius smooth, max jump {max_jump:.4f}): {criteria['C_radius_response_smooth']['status']}")
    
    # Criterion D: Baseline CV < 2%
    crit_d_pass = baseline_stats["cv"] < 0.02
    criteria["D_baseline_repeatability_cv_lt_2pct"] = {
        "status": "PASS" if crit_d_pass else "FAIL",
        "cv": baseline_stats["cv"]
    }
    print(f"  → Criterion D (Baseline CV < 2%): {criteria['D_baseline_repeatability_cv_lt_2pct']['status']}")
    
    results["acceptance_criteria"] = criteria
    
    all_pass = all(c["status"] == "PASS" for c in criteria.values())
    
    # ---- 6. Visualization ----
    print("\n[6/6] Generating visualizations...")
    
    # Figure 1: Null model distributions vs baseline
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for (name, ns), color in zip(results["null_models"].items(), colors):
        ax.axvline(ns["mean"], color=color, linestyle='--', label=f"{name} (μ={ns['mean']:.3f})")
        ax.axvspan(ns["mean"] - ns["std"], ns["mean"] + ns["std"], color=color, alpha=0.1)
    ax.axvline(baseline_stats["mean"], color='black', linewidth=3, label=f"BASELINE (μ={baseline_stats['mean']:.3f})")
    ax.set_xlabel("C_phi")
    ax.set_ylabel("Density")
    ax.set_title("A2a: Null Model Distributions vs Structured Baseline")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "null_distributions.png", dpi=200)
    plt.close()
    
    # Figure 2: Noise response curve with error bars
    fig, ax = plt.subplots(figsize=(8, 5))
    levels = [e["noise_fraction"] * 100 for e in results["noise_sweep"]]
    means = [e["mean"] for e in results["noise_sweep"]]
    stds = [e["std"] for e in results["noise_sweep"]]
    ax.errorbar(levels, means, yerr=stds, marker='o', capsize=5, linewidth=2)
    ax.set_xlabel("Noise Fraction (%)")
    ax.set_ylabel("C_phi (mean ± std)")
    ax.set_title("A2a: Noise Sensitivity Response")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "noise_response.png", dpi=200)
    plt.close()
    
    # Figure 3: Radius response
    fig, ax = plt.subplots(figsize=(8, 5))
    radii = [e["core_radius"] for e in results["radius_sweep"]]
    cphis = [e["c_phi"] for e in results["radius_sweep"]]
    ax.plot(radii, cphis, 'o-', linewidth=2, markersize=8)
    ax.set_xlabel("Lamb-Oseen Core Radius r0")
    ax.set_ylabel("C_phi")
    ax.set_title("A2a: Core Radius Response")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "radius_response.png", dpi=200)
    plt.close()
    
    # Figure 4: Baseline vortex field
    fig, ax = plt.subplots(figsize=(6, 6))
    speed = np.sqrt(u_base**2 + v_base**2)
    im = ax.pcolormesh(X, Y, speed, cmap='viridis', shading='auto')
    ax.quiver(X[::5, ::5], Y[::5, ::5], u_base[::5, ::5], v_base[::5, ::5], 
              color='white', scale=500, alpha=0.7)
    ax.set_title(f"Baseline Lamb-Oseen Vortex (C_phi = {baseline_stats['mean']:.4f})")
    ax.set_aspect('equal')
    plt.colorbar(im, ax=ax, label='Speed')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "baseline_vortex.png", dpi=200)
    plt.close()
    
    # ---- Save JSON report ----
    report_path = Path("experiments/milestone_A2a/a2a_characterization_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # ---- Final verdict ----
    print("\n" + "=" * 75)
    if all_pass:
        print("✅ MILESTONE A2a: ALL ACCEPTANCE CRITERIA PASSED")
        print("The operator is statistically stable, separates nulls, and responds smoothly.")
    else:
        failed = [k for k, v in criteria.items() if v["status"] == "FAIL"]
        print(f"❌ MILESTONE A2a: ACCEPTANCE CRITERIA FAILED")
        print(f"   Failed criteria: {failed}")
        print("   Do NOT proceed to Milestone A2b or B until resolved.")
    print("=" * 75)
    
    return all_pass

if __name__ == "__main__":
    success = run_characterization()
    if not success:
        sys.exit(1)