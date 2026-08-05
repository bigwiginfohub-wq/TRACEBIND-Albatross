"""
TRACEBIND-Albatross: Retrieval Experiment — Step 4
===================================================
Evaluate Retrieval Performance

Purpose: Objectively compare retrieval performance with rigorous statistical 
validation, addressing self-match exclusion, effect sizes, ranking agreement, 
and class imbalance.

Inputs:
- labels/storm_labels_rich.csv
- reports/rankings_{rep}_euclidean.csv

Outputs:
- reports/evaluation_summary.json (Comprehensive metrics + metadata)
- reports/per_query_metrics.csv (Per-query breakdown)
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from scipy.stats import spearmanr
import platform
import subprocess

# ============================================================================
# Configuration
# ============================================================================
LABELS_PATH = Path(__file__).parent / "labels" / "storm_labels_rich.csv"
TARGET_LABEL = "basin"  # Evaluate retrieval based on Basin matching
REPORT_DIR = Path(__file__).parent / "reports"

REPRESENTATIONS = {
    "TRACEBIND (12D)": "rankings_descriptor_matrix_scaled_euclidean.csv",
    "PCA (5D, 95% Var)": "rankings_pca_95_coordinates_euclidean.csv"
}

K_VALUES = [1, 3, 5]
N_PERMUTATIONS = 1000
N_BOOTSTRAP = 1000
N_MC_BASELINE = 10000
RANDOM_SEED = 42

# ============================================================================
# Metadata Gathering
# ============================================================================
def get_git_hash():
    try:
        # Suppress stderr to avoid noisy "fatal: not a git repository" messages
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).parent.parent.parent,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        return "not_available"

METADATA = {
    "descriptor_version": "R1.0",
    "operator_hash": "02732f08923752fa274bb490311929b2fc88cfc3826ebe59caecb4bab881e5cd",
    "distance_metric": "euclidean",
    "python_version": platform.python_version(),
    "numpy_version": np.__version__,
    "pandas_version": pd.__version__,
    "scipy_version": __import__('scipy').__version__,
    "sklearn_version": __import__('sklearn').__version__,
    "git_commit": get_git_hash(),
    "random_seed": RANDOM_SEED
}

# ============================================================================
# Statistical Evaluation Logic
# ============================================================================
def compute_mc_random_baseline(rankings_df, labels_lookup, k, n_sims=N_MC_BASELINE, rng=None):
    """Monte Carlo simulation of random retrieval, excluding self-matches."""
    if rng is None:
        rng = np.random.default_rng(RANDOM_SEED)
        
    queries = rankings_df['query'].unique()
    
    precisions = []
    recalls = []
    
    for _ in range(n_sims):
        sim_precisions = []
        sim_recalls = []
        for q in queries:
            q_class = labels_lookup[q]
            
            # Exclude query itself from candidate neighbors
            candidate_neighbors = [n for n in rankings_df['neighbor'].unique() if n != q]
            
            # Count retrievable items of same class (excluding query)
            total_possible = sum(1 for n in candidate_neighbors if labels_lookup[n] == q_class)
            
            # Randomly sample k neighbors without replacement
            sampled = rng.choice(candidate_neighbors, size=min(k, len(candidate_neighbors)), replace=False)
            matches = sum(1 for n in sampled if labels_lookup[n] == q_class)
            
            sim_precisions.append(matches / k)
            sim_recalls.append(matches / total_possible if total_possible > 0 else 0.0)
            
        precisions.append(np.mean(sim_precisions))
        recalls.append(np.mean(sim_recalls))
        
    return {
        f"precision@{k}_mean": float(np.mean(precisions)),
        f"precision@{k}_ci_lower": float(np.percentile(precisions, 2.5)),
        f"precision@{k}_ci_upper": float(np.percentile(precisions, 97.5)),
        f"recall@{k}_mean": float(np.mean(recalls)),
        f"recall@{k}_ci_lower": float(np.percentile(recalls, 2.5)),
        f"recall@{k}_ci_upper": float(np.percentile(recalls, 97.5))
    }

def permutation_test_rankings(rankings_df, labels_lookup, k, n_perms=N_PERMUTATIONS, rng=None):
    """Permute rankings from original candidate list to test retrieval order."""
    queries = rankings_df['query'].unique()
    
    # Precompute query-to-neighbors mapping for efficiency
    query_neighbors = {}
    for q in queries:
        query_neighbors[q] = rankings_df[rankings_df['query'] == q]['neighbor'].tolist()
    
    # Observed
    obs_precisions = []
    for q in queries:
        q_class = labels_lookup[q]
        top_k = query_neighbors[q][:k]
        matches = sum(1 for n in top_k if labels_lookup[n] == q_class)
        obs_precisions.append(matches / k)
    obs_mean = float(np.mean(obs_precisions))
    
    # Permutation: shuffle each query's original neighbor list
    perm_means = []
    for _ in range(n_perms):
        perm_precisions = []
        for q in queries:
            q_class = labels_lookup[q]
            shuffled = rng.permutation(query_neighbors[q])
            top_k_perm = shuffled[:k]
            matches = sum(1 for n in top_k_perm if labels_lookup[n] == q_class)
            perm_precisions.append(matches / k)
        perm_means.append(np.mean(perm_precisions))
        
    # P-value: proportion of permuted means >= observed mean
    p_value = float((np.sum(np.array(perm_means) >= obs_mean) + 1) / (n_perms + 1))
    return obs_mean, p_value, obs_precisions

def bootstrap_paired_difference_ci(df_tb, df_pca, labels_lookup, k, n_boot=N_BOOTSTRAP, rng=None):
    """Bootstrap PAIRED per-query differences between TRACEBIND and PCA.
    
    This is statistically cleaner than bootstrapping separate means because
    it preserves the natural pairing between representations for each query.
    """
    queries = df_tb['query'].unique()
    n_queries = len(queries)
    
    # Precompute query-to-neighbors mappings
    tb_neighbors = {}
    pca_neighbors = {}
    for q in queries:
        tb_neighbors[q] = df_tb[df_tb['query'] == q]['neighbor'].tolist()
        pca_neighbors[q] = df_pca[df_pca['query'] == q]['neighbor'].tolist()
    
    # Compute per-query paired differences ONCE
    paired_diffs = []
    for q in queries:
        q_class = labels_lookup[q]
        
        top_k_tb = tb_neighbors[q][:k]
        matches_tb = sum(1 for n in top_k_tb if labels_lookup[n] == q_class)
        p_tb = matches_tb / k
        
        top_k_pca = pca_neighbors[q][:k]
        matches_pca = sum(1 for n in top_k_pca if labels_lookup[n] == q_class)
        p_pca = matches_pca / k
        
        paired_diffs.append(p_tb - p_pca)
    
    paired_diffs = np.array(paired_diffs)
    
    # Bootstrap resample the paired differences
    boot_means = []
    for _ in range(n_boot):
        sampled = rng.choice(paired_diffs, size=n_queries, replace=True)
        boot_means.append(np.mean(sampled))
        
    mean_diff = float(np.mean(paired_diffs))
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))
    
    return mean_diff, ci_lower, ci_upper

def compute_ranking_agreement(df_tb, df_pca, k_values):
    """Compute Spearman correlation, Top-K overlap, and Jaccard similarity."""
    queries = df_tb['query'].unique()
    correlations = []
    overlaps = {k: [] for k in k_values}
    jaccards = {k: [] for k in k_values}
    
    for q in queries:
        ranks_tb = df_tb[df_tb['query'] == q].set_index('neighbor')['rank'].sort_index()
        ranks_pca = df_pca[df_pca['query'] == q].set_index('neighbor')['rank'].sort_index()
        
        common_neighbors = ranks_tb.index.intersection(ranks_pca.index)
        if len(common_neighbors) < 3:
            continue
            
        r_tb = ranks_tb.loc[common_neighbors].values
        r_pca = ranks_pca.loc[common_neighbors].values
        
        corr, _ = spearmanr(r_tb, r_pca)
        correlations.append(corr)
        
        # Top-K overlap and Jaccard
        for k in k_values:
            top_k_tb = set(ranks_tb.nsmallest(k).index)
            top_k_pca = set(ranks_pca.nsmallest(k).index)
            intersection = top_k_tb.intersection(top_k_pca)
            union = top_k_tb.union(top_k_pca)
            
            overlaps[k].append(len(intersection) / k)
            jaccards[k].append(len(intersection) / len(union) if len(union) > 0 else 0.0)
        
    return {
        "mean_spearman_rho": float(np.mean(correlations)),
        "std_spearman_rho": float(np.std(correlations)),
        "overlap_at_k": {k: float(np.mean(overlaps[k])) for k in k_values},
        "jaccard_at_k": {k: float(np.mean(jaccards[k])) for k in k_values}
    }

def compute_retrieval_composition(rankings_df, labels_lookup, k):
    """Compute retrieval class composition: counts of (query_class, retrieved_class) pairs."""
    queries = rankings_df['query'].unique()
    
    composition = {}
    for q in queries:
        q_class = labels_lookup[q]
        top_k = rankings_df[rankings_df['query'] == q].head(k)['neighbor'].tolist()
        
        for retrieved_class in set(labels_lookup.values()):
            matches = sum(1 for n in top_k if labels_lookup[n] == retrieved_class)
            key = (q_class, retrieved_class)
            composition[key] = composition.get(key, 0) + matches
            
    return composition

def compute_macro_precision(rankings_df, labels_lookup, k):
    """Compute macro-averaged precision across classes."""
    queries = rankings_df['query'].unique()
    classes = set(labels_lookup.values())
    
    class_precisions = {}
    for c in classes:
        class_queries = [q for q in queries if labels_lookup[q] == c]
        if not class_queries:
            continue
            
        precisions = []
        for q in class_queries:
            top_k = rankings_df[rankings_df['query'] == q].head(k)['neighbor'].tolist()
            matches = sum(1 for n in top_k if labels_lookup[n] == c)
            precisions.append(matches / k)
            
        class_precisions[c] = np.mean(precisions)
        
    return float(np.mean(list(class_precisions.values())))

# ============================================================================
# Main Execution
# ============================================================================
def evaluate_retrieval():
    print("=" * 85)
    print("RETRIEVAL EXPERIMENT: Step 4 — Evaluate Retrieval Performance")
    print("=" * 85)
    print("⚠️  PILOT STUDY: n=20 cases. Confidence intervals may be wide.")
    print("   Results are exploratory. Statistical power is limited.\n")
    
    rng = np.random.default_rng(RANDOM_SEED)
    
    # 1. Load Ground Truth
    print(f"[1/7] Loading ground truth labels from {LABELS_PATH}...")
    if not LABELS_PATH.exists():
        print(f"❌ Labels file not found: {LABELS_PATH}")
        return False
    
    labels_df = pd.read_csv(LABELS_PATH)
    labels_lookup = dict(zip(labels_df['filename'], labels_df[TARGET_LABEL]))
    print(f"  → Loaded {len(labels_df)} labeled cases.")
    print(f"  → Label evaluated: {TARGET_LABEL}")
    print(f"  → Classes: {sorted(labels_df[TARGET_LABEL].unique().tolist())}")
    print(f"  → Class distribution: {dict(labels_df[TARGET_LABEL].value_counts())}")
    
    # 2. Load Rankings & Validate
    print("\n[2/7] Loading and validating rankings...")
    loaded_rankings = {}
    for rep_name, ranking_file in REPRESENTATIONS.items():
        ranking_path = REPORT_DIR / ranking_file
        if not ranking_path.exists():
            print(f"  ⚠️  Skipping {rep_name}: Ranking file not found ({ranking_file})")
            continue
            
        df = pd.read_csv(ranking_path)
        
        # Validate: no missing labels
        missing = set(df['neighbor']) - set(labels_df['filename'])
        if missing:
            print(f"  ❌ ERROR: {len(missing)} files in {rep_name} rankings have no labels.")
            return False
            
        # Validate: no self-matches (Step 3 should have excluded them)
        self_matches = df[df['query'] == df['neighbor']]
        if len(self_matches) > 0:
            print(f"  ❌ ERROR: {len(self_matches)} self-matches detected in {rep_name} rankings.")
            print(f"     Step 3 should have excluded self-matches. Re-run 03_build_retrieval_index.py.")
            return False
            
        loaded_rankings[rep_name] = df
        print(f"  → Loaded {rep_name} ({len(df)} rankings). Verified: no self-matches.")
        
    if len(loaded_rankings) < 2:
        print("❌ Need at least 2 representations to compare.")
        return False
        
    df_tb = loaded_rankings["TRACEBIND (12D)"]
    df_pca = loaded_rankings["PCA (5D, 95% Var)"]
    
    # 3. Compute Metrics
    print("\n[3/7] Computing statistical metrics...")
    results = {}
    all_per_query = []
    
    # Monte Carlo Random Baseline (excluding self-matches)
    print("  → Computing Monte Carlo Random Baseline (excluding self-matches)...")
    random_baseline = {}
    for k in K_VALUES:
        rb = compute_mc_random_baseline(df_tb, labels_lookup, k, rng=rng)
        random_baseline[f"k={k}"] = rb
        
    for rep_name, df in loaded_rankings.items():
        print(f"  → Evaluating {rep_name}...")
        rep_results = {}
        
        for k in K_VALUES:
            # Observed Mean, Permutation P-value, and per-query precisions
            obs_mean, p_val, obs_precisions = permutation_test_rankings(df, labels_lookup, k, rng=rng)
            
            # Per-query metrics (for Recall calculation and saving)
            queries = df['query'].unique()
            pq_metrics = []
            
            # Precompute query-to-neighbors mapping
            query_neighbors = {}
            for q in queries:
                query_neighbors[q] = df[df['query'] == q]['neighbor'].tolist()
            
            for q in queries:
                q_class = labels_lookup[q]
                
                # Exclude query itself from retrievable items (safety check)
                candidate_neighbors = [n for n in query_neighbors[q] if n != q]
                total_possible = sum(1 for n in candidate_neighbors if labels_lookup[n] == q_class)
                
                top_k = query_neighbors[q][:k]
                matches = sum(1 for n in top_k if labels_lookup[n] == q_class)
                
                pq_metrics.append({
                    "query": q,
                    "query_class": q_class,
                    "k": k,
                    "representation": rep_name,
                    "matches": matches,
                    "precision": matches / k,
                    "recall": matches / total_possible if total_possible > 0 else 0.0
                })
            all_per_query.extend(pq_metrics)
            
            mean_p = np.mean([m["precision"] for m in pq_metrics])
            mean_r = np.mean([m["recall"] for m in pq_metrics])
            macro_p = compute_macro_precision(df, labels_lookup, k)
            
            rep_results[f"k={k}"] = {
                "precision_mean": round(float(mean_p), 4),
                "precision_macro": round(float(macro_p), 4),
                "recall_mean": round(float(mean_r), 4),
                "permutation_p_value": round(p_val, 4)
            }
            
        results[rep_name] = rep_results
        
    # 4. Ranking Agreement & Paired Difference CI
    print("\n[4/7] Computing ranking agreement and paired difference confidence intervals...")
    agreement = compute_ranking_agreement(df_tb, df_pca, K_VALUES)
    print(f"  → Mean Spearman correlation: {agreement['mean_spearman_rho']:.4f} (±{agreement['std_spearman_rho']:.4f})")
    for k in K_VALUES:
        print(f"  → Top-{k} overlap: {agreement['overlap_at_k'][k]:.4f}, Jaccard@{k}: {agreement['jaccard_at_k'][k]:.4f}")
    
    diff_results = {}
    for k in K_VALUES:
        mean_diff, ci_lower, ci_upper = bootstrap_paired_difference_ci(df_tb, df_pca, labels_lookup, k, rng=rng)
        diff_results[f"k={k}"] = {
            "mean_paired_difference_tracebind_minus_pca": round(mean_diff, 4),
            "ci_95_lower": round(ci_lower, 4),
            "ci_95_upper": round(ci_upper, 4)
        }
        
        # Interpretation
        if ci_lower > 0:
            interp = "TRACEBIND > PCA (significant)"
        elif ci_upper < 0:
            interp = "PCA > TRACEBIND (significant)"
        else:
            interp = "No significant difference"
            
        print(f"  → Precision@{k} Paired Diff (TB - PCA): {mean_diff:+.4f} [95% CI: {ci_lower:+.4f} to {ci_upper:+.4f}] → {interp}")

    # 5. Retrieval Class Composition
    print("\n[5/7] Computing retrieval class composition...")
    retrieval_composition = {}
    for rep_name, df in loaded_rankings.items():
        for k in K_VALUES:
            cm = compute_retrieval_composition(df, labels_lookup, k)
            retrieval_composition[f"{rep_name}_k={k}"] = {f"{k1}_{k2}": v for (k1, k2), v in cm.items()}
    
    # 6. Save Outputs
    print("\n[6/7] Saving evaluation outputs...")
    summary_data = {
        "metadata": {
            **METADATA,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_label": TARGET_LABEL,
            "pilot_study_warning": "n=20 cases. Results are exploratory. Confidence intervals may be wide."
        },
        "input_files": {
            "labels": str(LABELS_PATH),
            "tracebind_rankings": str(REPORT_DIR / REPRESENTATIONS["TRACEBIND (12D)"]),
            "pca_rankings": str(REPORT_DIR / REPRESENTATIONS["PCA (5D, 95% Var)"])
        },
        "random_baseline_mc": {k: {kk: round(v, 4) for kk, v in vv.items()} for k, vv in random_baseline.items()},
        "ranking_agreement": agreement,
        "paired_difference_confidence_intervals": diff_results,
        "retrieval_class_composition": retrieval_composition,
        "results": results
    }
    
    summary_path = REPORT_DIR / "evaluation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"  → Summary saved to {summary_path}")
    
    pq_df = pd.DataFrame(all_per_query)
    pq_path = REPORT_DIR / "per_query_metrics.csv"
    pq_df.to_csv(pq_path, index=False)
    print(f"  → Per-query metrics saved to {pq_path}")
    
    # 7. Print Comparative Summary
    print("\n[7/7] Generating comparative summary...")
    print("\n" + "=" * 85)
    print(f"EVALUATION SUMMARY (Precision@5 for '{TARGET_LABEL}')")
    print("=" * 85)
    print(f"{'Representation':<25} | {'Mean P@5':<10} | {'Macro P@5':<10} | {'Mean R@5':<10} | {'p-value':<10}")
    print("-" * 85)
    rb_p5 = random_baseline["k=5"]["precision@5_mean"]
    print(f"{'Monte Carlo Random':<25} | {rb_p5:<10.4f} | {'N/A':<10} | {'N/A':<10} | {'N/A':<10}")
    
    for rep_name, metrics in results.items():
        p5 = metrics["k=5"]
        print(f"{rep_name:<25} | {p5['precision_mean']:<10.4f} | {p5['precision_macro']:<10.4f} | {p5['recall_mean']:<10.4f} | {p5['permutation_p_value']:<10.4f}")
    
    print("=" * 85)
    print("✅ Step 4 complete. Objective, statistically rigorous evaluation is finished.")
    print("=" * 85)
    
    return True

if __name__ == "__main__":
    success = evaluate_retrieval()
    if not success:
        sys.exit(1)