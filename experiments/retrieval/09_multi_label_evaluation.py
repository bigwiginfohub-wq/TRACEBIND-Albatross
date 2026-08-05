"""
TRACEBIND-Albatross: Retrieval Experiment — Step 9 (Final Phase A)
===================================================================
Multi-Label Retrieval Evaluation

Purpose: Evaluate retrieval performance across all predefined meteorological 
targets using the frozen methodology. This is the final analysis of Phase A.

Outputs:
- reports/multi_label_evaluation.json
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# ============================================================================
# Configuration
# ============================================================================
LABELS_CSV = Path(__file__).parent / "labels" / "storm_labels_comprehensive.csv"
REPORT_DIR = Path(__file__).parent / "reports"

# Predefined research questions for Phase A
TARGET_LABELS = ["basin", "max_category", "min_pressure_hpa", "landfall_yn"]
REPRESENTATIONS = {
    "TRACEBIND (12D)": "rankings_descriptor_matrix_scaled_euclidean.csv",
    "PCA (5D, 95% Var)": "rankings_pca_95_coordinates_euclidean.csv"
}
K = 5
N_PERMUTATIONS = 1000
N_BOOTSTRAP = 1000
RANDOM_SEED = 42

# ============================================================================
# Evaluation Logic (Reused from Step 4 for consistency)
# ============================================================================
def compute_precision_with_ci(df_rankings, labels_lookup, k, n_boot=N_BOOTSTRAP, rng=None):
    queries = df_rankings['query'].unique()
    precisions = []
    
    for q in queries:
        if q not in labels_lookup:
            continue
        q_class = labels_lookup[q]
        top_k = df_rankings[df_rankings['query'] == q].head(k)['neighbor'].tolist()
        matches = sum(1 for n in top_k if labels_lookup.get(n) == q_class)
        precisions.append(matches / k)
        
    if not precisions:
        return 0.0, 0.0, 0.0
        
    mean_p = float(np.mean(precisions))
    boot_means = [np.mean(rng.choice(precisions, size=len(precisions), replace=True)) for _ in range(n_boot)]
    return mean_p, float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))

def permutation_test(df_rankings, labels_lookup, k, n_perms=N_PERMUTATIONS, rng=None):
    queries = df_rankings['query'].unique()
    query_neighbors = {q: df_rankings[df_rankings['query'] == q]['neighbor'].tolist() for q in queries}
    
    obs_precisions = []
    for q in queries:
        if q not in labels_lookup: continue
        q_class = labels_lookup[q]
        top_k = query_neighbors[q][:k]
        obs_precisions.append(sum(1 for n in top_k if labels_lookup.get(n) == q_class) / k)
    obs_mean = float(np.mean(obs_precisions))
    
    perm_means = []
    for _ in range(n_perms):
        perm_precisions = []
        for q in queries:
            if q not in labels_lookup: continue
            q_class = labels_lookup[q]
            shuffled = rng.permutation(query_neighbors[q])
            perm_precisions.append(sum(1 for n in shuffled[:k] if labels_lookup.get(n) == q_class) / k)
        perm_means.append(np.mean(perm_precisions))
        
    return obs_mean, float((np.sum(np.array(perm_means) >= obs_mean) + 1) / (n_perms + 1))

# ============================================================================
# Main Execution
# ============================================================================
def run_multi_label_evaluation():
    print("=" * 85)
    print("PHASE A: Step 9 — Final Multi-Label Evaluation")
    print("=" * 85)
    print("⚠️  This is the final analysis of Phase A. Methodology is frozen.")
    
    rng = np.random.default_rng(RANDOM_SEED)
    
    if not LABELS_CSV.exists():
        print(f"❌ Comprehensive labels not found: {LABELS_CSV}")
        print("   Please ensure 08_enrich_metadata.py completed successfully.")
        return False
        
    df_labels = pd.read_csv(LABELS_CSV)
    print(f"\n  → Loaded comprehensive metadata for {len(df_labels)} cases.")
    
    final_results = {}
    
    for target in TARGET_LABELS:
        if target not in df_labels.columns:
            print(f"  ⚠️  Skipping '{target}': Column not found in metadata.")
            continue
            
        print(f"\n  Evaluating Target: {target.upper()}")
        
        # Drop NA values for this specific target (e.g., drops controls for intensity)
        df_valid = df_labels[df_labels[target].notna()].copy()
        
        # For continuous variables like pressure, bin them for retrieval evaluation
        if target == 'min_pressure_hpa':
            # Create pressure bins: <960 (Very Severe), 960-980 (Severe), >980 (Cyclonic)
            bins = [0, 960, 980, 1050]
            labels_bin = ['<960_hPa', '960-980_hPa', '>980_hPa']
            df_valid['eval_label'] = pd.cut(df_valid[target], bins=bins, labels=labels_bin).astype(str)
            eval_target = 'eval_label'
            print(f"    → Binned continuous variable into: {labels_bin}")
        else:
            df_valid['eval_label'] = df_valid[target].astype(str)
            eval_target = 'eval_label'
            
        labels_lookup = dict(zip(df_valid['filename'], df_valid['eval_label']))
        valid_files = df_valid['filename'].tolist()
        print(f"    → {len(valid_files)} cases have valid '{target}' labels.")
        
        target_results = {}
        for rep_name, ranking_file in REPRESENTATIONS.items():
            ranking_path = REPORT_DIR / ranking_file
            if not ranking_path.exists():
                continue
                
            df_rankings = pd.read_csv(ranking_path)
            # Filter rankings to only include valid queries/neighbors for this target
            df_rankings = df_rankings[df_rankings['query'].isin(valid_files) & df_rankings['neighbor'].isin(valid_files)]
            
            if len(df_rankings) == 0:
                continue
                
            mean_p, ci_l, ci_u = compute_precision_with_ci(df_rankings, labels_lookup, K, rng=rng)
            _, p_val = permutation_test(df_rankings, labels_lookup, K, rng=rng)
            
            target_results[rep_name] = {
                "precision_mean": round(mean_p, 4),
                "ci_95_lower": round(ci_l, 4),
                "ci_95_upper": round(ci_u, 4),
                "permutation_p_value": round(p_val, 4)
            }
            
        final_results[target] = target_results
        
    # Save Final Report
    summary_data = {
        "metadata": {
            "phase": "A (Pilot)",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "FROZEN"
        },
        "results": final_results
    }
    
    summary_path = REPORT_DIR / "multi_label_evaluation.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
        
    print("\n" + "=" * 85)
    print("FINAL PHASE A EVALUATION SUMMARY (Precision@5)")
    print("=" * 85)
    
    for target, res in final_results.items():
        print(f"\n[{target.upper()}]")
        print(f"{'Representation':<25} | {'Mean P@5':<10} | {'95% CI':<18} | {'p-value':<10}")
        print("-" * 85)
        for rep_name, metrics in res.items():
            ci_str = f"[{metrics['ci_95_lower']:.2f} - {metrics['ci_95_upper']:.2f}]"
            print(f"{rep_name:<25} | {metrics['precision_mean']:<10.4f} | {ci_str:<18} | {metrics['permutation_p_value']:<10.4f}")
            
    print("\n" + "=" * 85)
    print("✅ Phase A Multi-Label Evaluation Complete.")
    print("   The methodology is now FROZEN. Proceed to Phase A Report and Phase B.")
    print("=" * 85)
    return True

if __name__ == "__main__":
    run_multi_label_evaluation()