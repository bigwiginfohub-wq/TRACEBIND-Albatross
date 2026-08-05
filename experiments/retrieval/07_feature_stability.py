"""
TRACEBIND-Albatross: Retrieval Experiment — Step 7
===================================================
Feature Stability & Redundancy Analysis

Purpose: Rigorously quantify descriptor redundancy and identify which 
features consistently drive retrieval performance, avoiding the pitfalls 
of arbitrary feature selection on small datasets.

Methods:
1. Variance Inflation Factor (VIF) to quantify multicollinearity.
2. Bootstrap Leave-One-Descriptor-Out (LODO) to assess ranking stability.

Outputs:
- reports/feature_stability.json
- reports/vif_results.csv
- reports/bootstrap_lodo_stability.csv
- reports/feature_stability_plot.png
"""

import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.stats.outliers_influence import variance_inflation_factor

# ============================================================================
# Configuration
# ============================================================================
SCALED_CSV = Path(__file__).parent / "outputs" / "descriptor_matrix_scaled.csv"
LABELS_CSV = Path(__file__).parent / "labels" / "storm_labels_rich.csv"
REPORT_DIR = Path(__file__).parent / "reports"

TARGET_LABEL = "basin"
K = 5
N_BOOTSTRAP = 1000
RANDOM_SEED = 42

# ============================================================================
# Retrieval Logic
# ============================================================================
def compute_precision_for_queries(X, query_indices, all_filenames, labels_lookup, k=5):
    """Compute mean Precision@K for a specific subset of queries (with replacement)."""
    precisions = []
    for q_idx in query_indices:
        q_file = all_filenames[q_idx]
        q_class = labels_lookup[q_file]
        
        # Search against the FULL dataset to maintain consistent neighborhood structure
        distances = np.linalg.norm(X - X[q_idx], axis=1)
        sorted_indices = np.argsort(distances)
        
        matches = 0
        count = 0
        for idx in sorted_indices:
            if idx == q_idx:
                continue
            if labels_lookup[all_filenames[idx]] == q_class:
                matches += 1
            count += 1
            if count == k:
                break
        precisions.append(matches / k)
        
    return float(np.mean(precisions))

# ============================================================================
# Main Execution
# ============================================================================
def run_feature_stability():
    print("=" * 85)
    print("RETRIEVAL EXPERIMENT: Step 7 — Feature Stability & Redundancy Analysis")
    print("=" * 85)
    
    rng = np.random.default_rng(RANDOM_SEED)
    
    # 1. Load Data
    print("\n[1/4] Loading data...")
    if not SCALED_CSV.exists():
        print(f"❌ Scaled descriptor file not found: {SCALED_CSV}")
        return False
        
    df_scaled = pd.read_csv(SCALED_CSV)
    df_labels = pd.read_csv(LABELS_CSV)
    
    filenames = df_scaled['filename'].values
    descriptor_names = [col for col in df_scaled.columns if col != 'filename']
    X_scaled = df_scaled[descriptor_names].values.astype('float64')
    labels_lookup = dict(zip(df_labels['filename'], df_labels[TARGET_LABEL]))
    n_queries = len(filenames)
    
    print(f"  → Loaded {n_queries} cases, {len(descriptor_names)} descriptors.")
    
    # 2. Variance Inflation Factor (VIF) Analysis
    print("\n[2/4] Computing Variance Inflation Factor (VIF)...")
    vif_data = pd.DataFrame()
    vif_data["Descriptor"] = descriptor_names
    
    # Add constant for VIF calculation
    X_with_const = pd.DataFrame(X_scaled, columns=descriptor_names)
    X_with_const = pd.concat([pd.Series(1, index=X_with_const.index, name='const'), X_with_const], axis=1)
    vif_data["VIF"] = [variance_inflation_factor(X_with_const.values, i) for i in range(len(X_with_const.columns))][1:]
    vif_data = vif_data.sort_values("VIF", ascending=False)
    
    vif_path = REPORT_DIR / "vif_results.csv"
    vif_data.to_csv(vif_path, index=False)
    print(f"  → VIF results saved to {vif_path}")
    
    print("  → High multicollinearity (VIF > 5.0):")
    high_vif = vif_data[vif_data["VIF"] > 5.0]
    if len(high_vif) > 0:
        for _, row in high_vif.iterrows():
            print(f"     - {row['Descriptor']}: VIF = {row['VIF']:.2f}")
    else:
        print("     None found.")
        
    # 3. Bootstrap LODO Stability
    print(f"\n[3/4] Running Bootstrap LODO Stability ({N_BOOTSTRAP} iterations)...")
    
    # Initialize counters for ranking stability
    stability_counts = {desc: {"top_1": 0, "top_3": 0, "top_5": 0} for desc in descriptor_names}
    mean_deltas = {desc: 0.0 for desc in descriptor_names}
    
    for boot in range(N_BOOTSTRAP):
        # Resample query indices with replacement
        boot_q_indices = rng.choice(n_queries, size=n_queries, replace=True)
        
        # Baseline P@K for this bootstrap sample (all 12 descriptors)
        base_p = compute_precision_for_queries(X_scaled, boot_q_indices, filenames, labels_lookup, k=K)
        
        # LODO for this bootstrap sample
        deltas = {}
        for i, desc in enumerate(descriptor_names):
            X_reduced = np.delete(X_scaled, i, axis=1)
            reduced_p = compute_precision_for_queries(X_reduced, boot_q_indices, filenames, labels_lookup, k=K)
            deltas[desc] = base_p - reduced_p
            mean_deltas[desc] += deltas[desc]
            
        # Rank descriptors by delta (descending: highest drop = most important)
        ranked_descs = sorted(deltas.keys(), key=lambda x: deltas[x], reverse=True)
        
        # Record ranks
        for rank, desc in enumerate(ranked_descs, start=1):
            if rank <= 1: stability_counts[desc]["top_1"] += 1
            if rank <= 3: stability_counts[desc]["top_3"] += 1
            if rank <= 5: stability_counts[desc]["top_5"] += 1
            
    # Calculate percentages
    stability_results = []
    for desc in descriptor_names:
        stability_results.append({
            "Descriptor": desc,
            "Mean_Delta_P5": round(mean_deltas[desc] / N_BOOTSTRAP, 4),
            "Top_1_Frequency_%": round((stability_counts[desc]["top_1"] / N_BOOTSTRAP) * 100, 1),
            "Top_3_Frequency_%": round((stability_counts[desc]["top_3"] / N_BOOTSTRAP) * 100, 1),
            "Top_5_Frequency_%": round((stability_counts[desc]["top_5"] / N_BOOTSTRAP) * 100, 1)
        })
        
    # Sort by Top 3 frequency (a good balance of specificity and stability)
    stability_df = pd.DataFrame(stability_results).sort_values("Top_3_Frequency_%", ascending=False)
    
    stability_path = REPORT_DIR / "bootstrap_lodo_stability.csv"
    stability_df.to_csv(stability_path, index=False)
    print(f"  → Bootstrap stability results saved to {stability_path}")
    
    print("\n  → Descriptor Importance Stability (Top 3 Frequency):")
    for _, row in stability_df.head(5).iterrows():
        print(f"     {row['Descriptor']:<25} Top-3: {row['Top_3_Frequency_%']:>5.1f}% | Mean ΔP@5: {row['Mean_Delta_P5']:+.4f}")
        
    # 4. Visualization
    print("\n[4/4] Generating feature stability plot...")
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Plot Top 3 Frequency as horizontal bar chart
    y_pos = np.arange(len(stability_df))
    ax1.barh(y_pos, stability_df["Top_3_Frequency_%"], color='tab:blue', alpha=0.7)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(stability_df["Descriptor"])
    ax1.set_xlabel('Frequency in Top 3 Most Important (%)', fontsize=12)
    ax1.set_title('Bootstrap LODO Stability: Consistent Descriptor Importance', fontsize=14, fontweight='bold')
    ax1.set_xlim(0, 100)
    ax1.grid(True, alpha=0.3, axis='x')
    
    # Add mean delta as text labels
    for i, v in enumerate(stability_df["Mean_Delta_P5"]):
        ax1.text(v * 100 + 2, i, f"ΔP@5: {v:+.3f}", va='center', fontsize=9, color='dimgray')
    
    plot_path = REPORT_DIR / "feature_stability_plot.png"
    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"  → Plot saved to {plot_path}")
    
    # 5. Save Summary
    summary = {
        "n_cases": n_queries,
        "n_bootstrap_iterations": N_BOOTSTRAP,
        "vif_results": vif_data.to_dict(orient='records'),
        "bootstrap_stability": stability_df.to_dict(orient='records')
    }
    
    summary_path = REPORT_DIR / "feature_stability.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  → Summary saved to {summary_path}")
    
    print("\n" + "=" * 85)
    print("✅ Feature stability analysis complete.")
    print("\nKey Insights:")
    print("  1. VIF identifies mathematically redundant descriptors (e.g., max vs. center vorticity).")
    print("  2. Bootstrap LODO reveals which descriptors consistently drive retrieval, avoiding arbitrary thresholds.")
    print("  3. Descriptors with low Top-3 frequency may be candidates for removal in future iterations.")
    print("=" * 85)
    
    return True

if __name__ == "__main__":
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
    except ImportError:
        print("❌ Missing dependency. Please run: pip install statsmodels")
        sys.exit(1)
        
    success = run_feature_stability()
    if not success:
        sys.exit(1)