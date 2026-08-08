"""
TRACEBIND Phase B4: Statistical Analysis Engine
================================================
Purpose: Strictly preregistered statistical comparison of C_phi between
150 TC cases and 150 Control cases using frozen B3 descriptors.

Strictly adheres to PHASE_B4_STATISTICAL_ANALYSIS_PROTOCOL.md v1.0.
NOTE: This engine is strictly non-result-printing to preserve preregistration discipline.
Use verify_b4_integrity.py to inspect the results after execution.
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
matplotlib.use('Agg')
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
    n_x, n_y = len(x), len(y)
    x_col = x[:, np.newaxis]
    y_row = y[np.newaxis, :]
    greater = np.sum(x_col > y_row)
    less = np.sum(x_col < y_row)
    return (greater - less) / (n_x * n_y)

def hedges_g(x, y):
    n_x, n_y = len(x), len(y)
    mean_x, mean_y = np.mean(x), np.mean(y)
    var_x, var_y = np.var(x, ddof=1), np.var(y, ddof=1)
    pooled_std = np.sqrt(((n_x - 1) * var_x + (n_y - 1) * var_y) / (n_x + n_y - 2))
    d = (mean_x - mean_y) / pooled_std
    correction = 1 - 3 / (4 * (n_x + n_y - 2) - 1)
    return d * correction

def bootstrap_auc(tc_values, ctrl_values, n_boot=2000, seed=43):
    rng = np.random.default_rng(seed)
    n_tc, n_ctrl = len(tc_values), len(ctrl_values)
    aucs = []
    for _ in range(n_boot):
        tc_sample = rng.choice(tc_values, size=n_tc, replace=True)
        ctrl_sample = rng.choice(ctrl_values, size=n_ctrl, replace=True)
        y_true = np.concatenate([np.ones(n_tc), np.zeros(n_ctrl)])
        y_score = np.concatenate([tc_sample, ctrl_sample])
        aucs.append(roc_auc_score(y_true, y_score))
    
    aucs = np.array(aucs)
    return float(np.mean(aucs)), float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))

def ecdf(data):
    x = np.sort(data)
    y = np.arange(1, len(x) + 1) / len(x)
    return x, y

# ============================================================================
# Main Execution
# ============================================================================
def run_analysis():
    print("=" * 85)
    print("PHASE B4: Statistical Analysis Engine (Strictly Non-Result-Printing)")
    print("=" * 85)
    
    # 1. Preflight
    print("\n[1/10] Verifying input artifact integrity...")
    actual_hash = compute_sha256(INPUT_CSV)
    if actual_hash != EXPECTED_INPUT_HASH:
        raise RuntimeError(f"CRITICAL: Input hash mismatch!")
    
    # 2. Load and Schema Validation
    print("[2/10] Loading and validating data schema...")
    df = pd.read_csv(INPUT_CSV)
    required_columns = {"case_id", "case_type", "case_timestamp", "C_phi", "shell_grid_count", "QC_Status"}
    if not required_columns.issubset(set(df.columns)):
        raise ValueError("Missing required columns.")
    if not set(df["case_type"].dropna().unique()).issubset({"TC", "Control"}):
        raise ValueError("Unexpected case_type value.")
        
    df_filtered = df[df["QC_Status"] == "PASSED"].copy()
    if not np.all(np.isfinite(df_filtered["C_phi"].values)):
        raise ValueError("Non-finite C_phi value detected.")
    if len(df_filtered) != 300:
        raise ValueError(f"Expected 300 PASSED cases, found {len(df_filtered)}")
    
    tc_values = df_filtered[df_filtered["case_type"] == "TC"]["C_phi"].values
    ctrl_values = df_filtered[df_filtered["case_type"] == "Control"]["C_phi"].values
    
    # 3. Descriptive Statistics
    print("[3/10] Computing descriptive statistics...")
    desc_stats = {
        "TC": {"n": int(len(tc_values)), "mean": float(np.mean(tc_values)), "sd": float(np.std(tc_values, ddof=1)), "median": float(np.median(tc_values)), "iqr": float(np.percentile(tc_values, 75) - np.percentile(tc_values, 25))},
        "Control": {"n": int(len(ctrl_values)), "mean": float(np.mean(ctrl_values)), "sd": float(np.std(ctrl_values, ddof=1)), "median": float(np.median(ctrl_values)), "iqr": float(np.percentile(ctrl_values, 75) - np.percentile(ctrl_values, 25))}
    }
    
    # 4. Primary Test
    print("[4/10] Running primary test: Mann-Whitney U (asymptotic)...")
    mw_stat, mw_p = stats.mannwhitneyu(tc_values, ctrl_values, alternative='two-sided', method='asymptotic')
    
    # 5. Primary Effect Size
    print("[5/10] Computing primary effect size: Cliff's delta...")
    cd = cliffs_delta(tc_values, ctrl_values)
    
    # 6. Sensitivity Test
    print("[6/10] Running sensitivity test: Welch's t-test...")
    t_stat, t_p = stats.ttest_ind(tc_values, ctrl_values, equal_var=False)
    
    # 7. Sensitivity Effect Size
    print("[7/10] Computing sensitivity effect size: Hedges' g...")
    hg = hedges_g(tc_values, ctrl_values)
    
    # 8. ROC/AUC
    print("[8/10] Computing ROC/AUC with bootstrap (2000 replicates, seed=43)...")
    y_true = np.concatenate([np.ones(len(tc_values)), np.zeros(len(ctrl_values))])
    y_score = np.concatenate([tc_values, ctrl_values])
    full_auc = float(roc_auc_score(y_true, y_score))
    mean_auc, ci_lower, ci_upper = bootstrap_auc(tc_values, ctrl_values, BOOTSTRAP_N, BOOTSTRAP_SEED)
    
    # 9. Visualizations
    print("[9/10] Generating publication-ready visualizations...")
    TC_COLOR, CTRL_COLOR = '#D62728', '#1F77B4'
    
    # ECDF
    fig, ax = plt.subplots(figsize=(8, 6))
    tc_x, tc_y = ecdf(tc_values)
    ctrl_x, ctrl_y = ecdf(ctrl_values)
    ax.step(tc_x, tc_y, where='post', color=TC_COLOR, linewidth=2, label=f'TC (n={len(tc_values)})')
    ax.step(ctrl_x, ctrl_y, where='post', color=CTRL_COLOR, linewidth=2, label=f'Control (n={len(ctrl_values)})')
    ax.set_xlabel('$C_\\phi$ (Tangential Alignment)', fontsize=12)
    ax.set_ylabel('Cumulative Probability', fontsize=12)
    ax.set_title('Empirical Cumulative Distribution Function', fontsize=14)
    ax.legend(fontsize=11); ax.grid(True, alpha=0.3); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    plt.tight_layout(); plt.savefig(OUTPUT_VIZ_DIR / "b4_ecdf_plot.png", dpi=300, bbox_inches='tight'); plt.close()
    
    # Boxplot + Jitter
    fig, ax = plt.subplots(figsize=(8, 6))
    bp = ax.boxplot([tc_values, ctrl_values], positions=[1, 2], widths=0.5, patch_artist=True, showfliers=False)
    bp['boxes'][0].set_facecolor(TC_COLOR); bp['boxes'][1].set_facecolor(CTRL_COLOR)
    bp['boxes'][0].set_alpha(0.6); bp['boxes'][1].set_alpha(0.6)
    rng_jitter = np.random.default_rng(BOOTSTRAP_SEED)
    ax.scatter(np.ones(len(tc_values)) + rng_jitter.uniform(-0.1, 0.1, size=len(tc_values)), tc_values, color=TC_COLOR, alpha=0.5, s=20, edgecolors='white', linewidth=0.5)
    ax.scatter(2 * np.ones(len(ctrl_values)) + rng_jitter.uniform(-0.1, 0.1, size=len(ctrl_values)), ctrl_values, color=CTRL_COLOR, alpha=0.5, s=20, edgecolors='white', linewidth=0.5)
    ax.set_xticks([1, 2]); ax.set_xticklabels(['TC', 'Control'], fontsize=12)
    ax.set_ylabel('$C_\\phi$ (Tangential Alignment)', fontsize=12); ax.set_title('Distribution Comparison: TC vs Control', fontsize=14)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout(); plt.savefig(OUTPUT_VIZ_DIR / "b4_boxplot_jitter.png", dpi=300, bbox_inches='tight'); plt.close()
    
    # ROC
    fig, ax = plt.subplots(figsize=(8, 6))
    fpr, tpr, _ = roc_curve(y_true, y_score)
    ax.plot(fpr, tpr, color='black', linewidth=2, label=f'ROC Curve (AUC = {full_auc:.3f} [{ci_lower:.3f}, {ci_upper:.3f}])')
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Chance (AUC = 0.5)')
    ax.set_xlabel('False Positive Rate', fontsize=12); ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('Receiver Operating Characteristic Curve', fontsize=14)
    ax.legend(fontsize=11, loc='lower right'); ax.grid(True, alpha=0.3); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    plt.tight_layout(); plt.savefig(OUTPUT_VIZ_DIR / "b4_roc_curve.png", dpi=300, bbox_inches='tight'); plt.close()
    
    # 10. Save Results & Audit
    print("[10/10] Writing machine-readable results and audit manifest...")
    
    results = {
        "descriptive_statistics": desc_stats,
        "primary_analysis": {"test": "Mann-Whitney U", "alternative": "two-sided", "method": "asymptotic", "statistic": float(mw_stat), "p_value": float(mw_p), "alpha": ALPHA, "significant": bool(mw_p < ALPHA)},
        "primary_effect_size": {"metric": "Cliff's delta", "value": float(cd), "interpretation": "P(TC > Control) - P(TC < Control)"},
        "sensitivity_analysis": {"test": "Welch's t-test", "statistic": float(t_stat), "p_value": float(t_p), "alpha": ALPHA, "significant": bool(t_p < ALPHA)},
        "sensitivity_effect_size": {"metric": "Hedges' g", "value": float(hg)},
        "discrimination": {"metric": "ROC AUC", "value": float(full_auc), "bootstrap_n": BOOTSTRAP_N, "bootstrap_seed": BOOTSTRAP_SEED, "ci_lower_95": ci_lower, "ci_upper_95": ci_upper, "positive_class": "TC", "direction": "Higher C_phi predicts TC"},
        "directional_expectation": {"hypothesized_direction": "TC > Control", "observed_cliffs_delta_sign": "positive" if cd > 0 else "negative" if cd < 0 else "zero", "observed_auc_direction": "above_0.5" if full_auc > 0.5 else "below_0.5" if full_auc < 0.5 else "0.5"}
    }
    with open(OUTPUT_RESULTS, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
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
        "sample_sizes": {"TC": int(len(tc_values)), "Control": int(len(ctrl_values))},
        "software_environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "matplotlib": matplotlib.__version__
        }
    }
    with open(OUTPUT_AUDIT, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
    
    print("\n" + "=" * 85)
    print("✅ Phase B4 Statistical Analysis COMPLETE.")
    print("   All machine-readable artifacts and visualizations have been generated.")
    print("   Run verify_b4_integrity.py to inspect the results.")
    print("=" * 85)

if __name__ == "__main__":
    run_analysis()