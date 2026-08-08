"""
TRACEBIND Phase B4: Statistical Analysis
=========================================
Purpose: Strictly preregistered statistical comparison of C_phi between
150 TC cases and 150 Control cases using frozen B3 descriptors.

Strictly adheres to PHASE_B4_STATISTICAL_ANALYSIS_PROTOCOL.md v1.0.
"""

import pandas as pd
import numpy as np
import json
import hashlib
import subprocess
import sys
import scipy
import sklearn
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve

# ============================================================================
# Configuration & Constants
# ============================================================================
PHASEB_DIR = Path(__file__).parent
INPUT_CSV = PHASEB_DIR / "b3_descriptors.csv"
EXPECTED_INPUT_HASH = "eb16205e233c3eb3d35de2e1e17c934bfd4ecb767dae6148d1b0f3f70e708ded"
PROTOCOL_PATH = PHASEB_DIR / "PHASE_B4_STATISTICAL_ANALYSIS_PROTOCOL.md"

OUTPUT_RESULTS = PHASEB_DIR / "b4_statistical_results.json"
OUTPUT_AUDIT = PHASEB_DIR / "b4_audit.json"
OUTPUT_VIZ_DIR = PHASEB_DIR / "b4_visualizations"
OUTPUT_VIZ_DIR.mkdir(exist_ok=True)

BOOTSTRAP_SEED = 43
BOOTSTRAP_N = 2000
ALPHA = 0.05

# ============================================================================
# Helper Functions
# ============================================================================
def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_git_hash():
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, cwd=PHASEB_DIR.parent)
        return result.stdout.strip()
    except Exception:
        return "NOT_GIT_REPOSITORY"

def cliffs_delta(x, y):
    """Compute Cliff's delta: P(X > Y) - P(X < Y)"""
    n_x, n_y = len(x), len(y)
    x_col = x[:, np.newaxis]
    y_row = y[np.newaxis, :]
    greater = np.sum(x_col > y_row)
    less = np.sum(x_col < y_row)
    return (greater - less) / (n_x * n_y)

def hedges_g(x, y):
    """Compute Hedges' g with small-sample bias correction."""
    n_x, n_y = len(x), len(y)
    mean_x, mean_y = np.mean(x), np.mean(y)
    var_x, var_y = np.var(x, ddof=1), np.var(y, ddof=1)
    pooled_std = np.sqrt(((n_x - 1) * var_x + (n_y - 1) * var_y) / (n_x + n_y - 2))
    d = (mean_x - mean_y) / pooled_std
    correction = 1 - 3 / (4 * (n_x + n_y - 2) - 1)
    return d * correction

def bootstrap_auc(tc_values, ctrl_values, n_boot=2000, seed=43):
    """Bootstrap AUC with within-class independent resampling."""
    rng = np.random.default_rng(seed)
    n_tc = len(tc_values)
    n_ctrl = len(ctrl_values)
    
    aucs = []
    for _ in range(n_boot):
        tc_sample = rng.choice(tc_values, size=n_tc, replace=True)
        ctrl_sample = rng.choice(ctrl_values, size=n_ctrl, replace=True)
        
        y_true = np.concatenate([np.ones(n_tc), np.zeros(n_ctrl)])
        y_score = np.concatenate([tc_sample, ctrl_sample])
        
        auc = roc_auc_score(y_true, y_score)
        aucs.append(auc)
    
    aucs = np.array(aucs)
    ci_lower = float(np.percentile(aucs, 2.5))
    ci_upper = float(np.percentile(aucs, 97.5))
    return float(np.mean(aucs)), ci_lower, ci_upper, aucs

def ecdf(data):
    """Compute empirical CDF"""
    x = np.sort(data)
    y = np.arange(1, len(x) + 1) / len(x)
    return x, y

# ============================================================================
# Main Execution
# ============================================================================
def run_analysis():
    print("=" * 85)
    print("PHASE B4: Statistical Analysis")
    print("=" * 85)
    
    # 1. Preflight: Verify Input Hash
    print("\n[1/8] Verifying input artifact integrity...")
    actual_hash = compute_sha256(INPUT_CSV)
    if actual_hash != EXPECTED_INPUT_HASH:
        raise RuntimeError(f"CRITICAL: Input hash mismatch!\nExpected: {EXPECTED_INPUT_HASH}\nActual:   {actual_hash}")
    print(f"  ✅ Input CSV SHA256 verified: {actual_hash[:16]}...")
    
    # 2. Load and Schema Validation
    print("\n[2/8] Loading and validating data schema...")
    df = pd.read_csv(INPUT_CSV)
    
    required_columns = {"case_id", "case_type", "case_timestamp", "C_phi", "shell_grid_count", "QC_Status"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
        
    allowed_types = {"TC", "Control"}
    if not set(df["case_type"].dropna().unique()).issubset(allowed_types):
        raise ValueError("Unexpected case_type value detected.")
        
    df_filtered = df[df["QC_Status"] == "PASSED"].copy()
    
    if not np.all(np.isfinite(df_filtered["C_phi"].values)):
        raise ValueError("Non-finite C_phi value detected in PASSED cases.")
        
    if len(df_filtered) != 300:
        raise ValueError(f"Expected 300 PASSED cases, found {len(df_filtered)}")
    
    # 3. Split into Groups
    tc_df = df_filtered[df_filtered["case_type"] == "TC"].copy()
    ctrl_df = df_filtered[df_filtered["case_type"] == "Control"].copy()
    
    if len(tc_df) != 150 or len(ctrl_df) != 150:
        raise ValueError(f"Expected 150 TC and 150 Control, found {len(tc_df)} TC and {len(ctrl_df)} Control")
    
    tc_values = tc_df["C_phi"].values
    ctrl_values = ctrl_df["C_phi"].values
    print(f"  ✅ TC: {len(tc_df)} cases, Control: {len(ctrl_df)} cases")
    
    # 4. Descriptive Statistics
    print("\n[3/8] Computing descriptive statistics...")
    desc_stats = {
        "TC": {
            "n": int(len(tc_values)),
            "mean": float(np.mean(tc_values)),
            "sd": float(np.std(tc_values, ddof=1)),
            "median": float(np.median(tc_values)),
            "iqr": float(np.percentile(tc_values, 75) - np.percentile(tc_values, 25))
        },
        "Control": {
            "n": int(len(ctrl_values)),
            "mean": float(np.mean(ctrl_values)),
            "sd": float(np.std(ctrl_values, ddof=1)),
            "median": float(np.median(ctrl_values)),
            "iqr": float(np.percentile(ctrl_values, 75) - np.percentile(ctrl_values, 25))
        }
    }
    print(f"  TC mean: {desc_stats['TC']['mean']:.4f}, Control mean: {desc_stats['Control']['mean']:.4f}")
    
    # 5. Primary Inferential Test: Mann-Whitney U (Explicit Asymptotic)
    print("\n[4/8] Running primary test: Mann-Whitney U (asymptotic)...")
    mw_stat, mw_p = stats.mannwhitneyu(tc_values, ctrl_values, alternative='two-sided', method='asymptotic')
    print(f"  U = {mw_stat:.2f}, p = {mw_p:.6e}")
    
    # 6. Primary Effect Size: Cliff's delta
    print("\n[5/8] Computing primary effect size: Cliff's delta...")
    cd = cliffs_delta(tc_values, ctrl_values)
    print(f"  Cliff's delta = {cd:.4f}")
    
    # 7. Sensitivity Analysis: Welch's t-test
    print("\n[6/8] Running sensitivity test: Welch's t-test...")
    t_stat, t_p = stats.ttest_ind(tc_values, ctrl_values, equal_var=False)
    print(f"  t = {t_stat:.4f}, p = {t_p:.6e}")
    
    # 8. Sensitivity Effect Size: Hedges' g
    print("\n[7/8] Computing sensitivity effect size: Hedges' g...")
    hg = hedges_g(tc_values, ctrl_values)
    print(f"  Hedges' g = {hg:.4f}")
    
    # 9. ROC/AUC with Bootstrap
    print("\n[8/8] Computing ROC/AUC with bootstrap (2000 replicates, seed=43)...")
    y_true = np.concatenate([np.ones(len(tc_values)), np.zeros(len(ctrl_values))])
    y_score = np.concatenate([tc_values, ctrl_values])
    
    full_auc = float(roc_auc_score(y_true, y_score))
    mean_auc, ci_lower, ci_upper, boot_aucs = bootstrap_auc(tc_values, ctrl_values, BOOTSTRAP_N, BOOTSTRAP_SEED)
    print(f"  AUC = {full_auc:.4f} [95% CI: {ci_lower:.4f}, {ci_upper:.4f}]")
    
    # ========================================================================
    # 10. Visualizations
    # ========================================================================
    print("\n[9/10] Generating publication-ready visualizations...")
    TC_COLOR = '#D62728'
    CTRL_COLOR = '#1F77B4'
    
    # --- ECDF Plot ---
    fig, ax = plt.subplots(figsize=(8, 6))
    tc_x, tc_y = ecdf(tc_values)
    ctrl_x, ctrl_y = ecdf(ctrl_values)
    ax.step(tc_x, tc_y, where='post', color=TC_COLOR, linewidth=2, label=f'TC (n={len(tc_values)})')
    ax.step(ctrl_x, ctrl_y, where='post', color=CTRL_COLOR, linewidth=2, label=f'Control (n={len(ctrl_values)})')
    ax.set_xlabel('$C_\\phi$ (Tangential Alignment)', fontsize=12)
    ax.set_ylabel('Cumulative Probability', fontsize=12)
    ax.set_title('Empirical Cumulative Distribution Function', fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(OUTPUT_VIZ_DIR / "b4_ecdf_plot.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- Boxplot with Jitter ---
    fig, ax = plt.subplots(figsize=(8, 6))
    positions = [1, 2]
    bp = ax.boxplot([tc_values, ctrl_values], positions=positions, widths=0.5, patch_artist=True, showfliers=False)
    bp['boxes'][0].set_facecolor(TC_COLOR)
    bp['boxes'][1].set_facecolor(CTRL_COLOR)
    bp['boxes'][0].set_alpha(0.6)
    bp['boxes'][1].set_alpha(0.6)
    
    rng_jitter = np.random.default_rng(BOOTSTRAP_SEED)
    tc_jitter = rng_jitter.uniform(-0.1, 0.1, size=len(tc_values))
    ctrl_jitter = rng_jitter.uniform(-0.1, 0.1, size=len(ctrl_values))
    
    ax.scatter(np.ones(len(tc_values)) + tc_jitter, tc_values, color=TC_COLOR, alpha=0.5, s=20, edgecolors='white', linewidth=0.5)
    ax.scatter(2 * np.ones(len(ctrl_values)) + ctrl_jitter, ctrl_values, color=CTRL_COLOR, alpha=0.5, s=20, edgecolors='white', linewidth=0.5)
    
    ax.set_xticks(positions)
    ax.set_xticklabels(['TC', 'Control'], fontsize=12)
    ax.set_ylabel('$C_\\phi$ (Tangential Alignment)', fontsize=12)
    ax.set_title('Distribution Comparison: TC vs Control', fontsize=14)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(OUTPUT_VIZ_DIR / "b4_boxplot_jitter.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- ROC Curve ---
    fig, ax = plt.subplots(figsize=(8, 6))
    fpr, tpr, _ = roc_curve(y_true, y_score)
    ax.plot(fpr, tpr, color='black', linewidth=2, label=f'ROC Curve (AUC = {full_auc:.3f} [{ci_lower:.3f}, {ci_upper:.3f}])')
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Chance (AUC = 0.5)')
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('Receiver Operating Characteristic Curve', fontsize=14)
    ax.legend(fontsize=11, loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(OUTPUT_VIZ_DIR / "b4_roc_curve.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  → Saved 3 visualizations to {OUTPUT_VIZ_DIR.name}/")
    
    # ========================================================================
    # 11. Save Statistical Results
    # ========================================================================
    print("\n[10/10] Saving statistical results and audit manifest...")
    
    results = {
        "descriptive_statistics": desc_stats,
        "primary_analysis": {
            "test": "Mann-Whitney U",
            "alternative": "two-sided",
            "method": "asymptotic",
            "statistic": float(mw_stat),
            "p_value": float(mw_p),
            "alpha": ALPHA,
            "significant": bool(mw_p < ALPHA)
        },
        "primary_effect_size": {
            "metric": "Cliff's delta",
            "value": float(cd),
            "interpretation": "P(TC > Control) - P(TC < Control)"
        },
        "sensitivity_analysis": {
            "test": "Welch's t-test",
            "statistic": float(t_stat),
            "p_value": float(t_p),
            "alpha": ALPHA,
            "significant": bool(t_p < ALPHA)
        },
        "sensitivity_effect_size": {
            "metric": "Hedges' g",
            "value": float(hg)
        },
        "discrimination": {
            "metric": "ROC AUC",
            "value": float(full_auc),
            "bootstrap_n": BOOTSTRAP_N,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "ci_lower_95": ci_lower,
            "ci_upper_95": ci_upper,
            "positive_class": "TC",
            "direction": "Higher C_phi predicts TC"
        },
        "directional_expectation": {
            "hypothesized_direction": "TC > Control",
            "observed_cliffs_delta_sign": "positive" if cd > 0 else "negative" if cd < 0 else "zero",
            "observed_auc_direction": "above_0.5" if full_auc > 0.5 else "below_0.5" if full_auc < 0.5 else "0.5"
        }
    }
    
    with open(OUTPUT_RESULTS, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"  → Saved: {OUTPUT_RESULTS.name}")
    
    # ========================================================================
    # 12. Generate Audit Manifest
    # ========================================================================
    audit_data = {
        "input_artifact_sha256": actual_hash,
        "protocol_sha256": compute_sha256(PROTOCOL_PATH),
        "script_sha256": compute_sha256(Path(__file__)),
        "output_sha256": compute_sha256(OUTPUT_RESULTS),
        "git_commit_hash": get_git_hash(),
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_n": BOOTSTRAP_N,
        "alpha": ALPHA,
        "sample_sizes": {
            "TC": int(len(tc_values)),
            "Control": int(len(ctrl_values))
        },
        "software_environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__
        }
    }
    
    with open(OUTPUT_AUDIT, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
    print(f"  → Saved: {OUTPUT_AUDIT.name}")
    
    print("\n" + "=" * 85)
    print("✅ Phase B4 Statistical Analysis COMPLETE.")
    print(f"   Primary test (Mann-Whitney U): p = {mw_p:.6e} ({'SIGNIFICANT' if mw_p < ALPHA else 'NOT SIGNIFICANT'})")
    print(f"   Cliff's delta: {cd:.4f}")
    print(f"   ROC AUC: {full_auc:.4f} [95% CI: {ci_lower:.4f}, {ci_upper:.4f}]")
    print("=" * 85)

if __name__ == "__main__":
    run_analysis()