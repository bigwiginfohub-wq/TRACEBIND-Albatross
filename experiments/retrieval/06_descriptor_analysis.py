"""
TRACEBIND-Albatross: Retrieval Experiment — Step 6
===================================================
Descriptor Structure & Ablation Analysis

Purpose: Understand the intrinsic structure of the TRACEBIND descriptor space
and identify which specific descriptors drive retrieval performance.

Outputs:
- reports/descriptor_analysis.json (comprehensive statistics)
- reports/pca_loadings_top.csv (top contributors per PC)
- reports/descriptor_correlation_clustered.png (hierarchical heatmap)
- reports/pca_scree_plot.png (variance with Kaiser line)
- reports/descriptor_ablation_results.csv (Leave-One-Out importance)
"""

import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.decomposition import PCA
from scipy.cluster import hierarchy

# ============================================================================
# Configuration
# ============================================================================
SCALED_CSV = Path(__file__).parent / "outputs" / "descriptor_matrix_scaled.csv"
RAW_CSV = Path(__file__).parent / "outputs" / "descriptor_database.csv"
LABELS_CSV = Path(__file__).parent / "labels" / "storm_labels_rich.csv"
REPORT_DIR = Path(__file__).parent / "reports"

TARGET_LABEL = "basin"
K = 5

# ============================================================================
# Retrieval Logic (for Ablation)
# ============================================================================
def compute_precision_at_k(X, filenames, labels_lookup, k=5):
    """Compute mean Precision@K, excluding self-matches."""
    n_queries = len(filenames)
    precisions = []
    
    for i, q_file in enumerate(filenames):
        q_class = labels_lookup[q_file]
        distances = np.linalg.norm(X - X[i], axis=1)
        sorted_indices = np.argsort(distances)
        
        matches = 0
        count = 0
        for idx in sorted_indices:
            if idx == i:
                continue
            if labels_lookup[filenames[idx]] == q_class:
                matches += 1
            count += 1
            if count == k:
                break
        precisions.append(matches / k)
        
    return float(np.mean(precisions))

# ============================================================================
# Main Execution
# ============================================================================
def analyze_descriptors():
    print("=" * 85)
    print("RETRIEVAL EXPERIMENT: Step 6 — Descriptor Structure & Ablation Analysis")
    print("=" * 85)
    
    # 1. Load Data & Verify Standardization
    print("\n[1/6] Loading data and verifying standardization...")
    if not SCALED_CSV.exists() or not RAW_CSV.exists():
        print("❌ Required CSV files not found.")
        return False
        
    df_scaled = pd.read_csv(SCALED_CSV)
    df_raw = pd.read_csv(RAW_CSV)
    df_labels = pd.read_csv(LABELS_CSV)
    
    filenames = df_scaled['filename'].values
    descriptor_names = [col for col in df_scaled.columns if col != 'filename']
    
    X_scaled = df_scaled[descriptor_names].values.astype('float64')
    X_raw = df_raw[descriptor_names].values.astype('float64')
    labels_lookup = dict(zip(df_labels['filename'], df_labels[TARGET_LABEL]))
    
    # Verify standardization
    means = np.mean(X_scaled, axis=0)
    stds = np.std(X_scaled, axis=0)
    print(f"  → Scaled data mean range: [{means.min():.4f}, {means.max():.4f}] (Expected ~0.0)")
    print(f"  → Scaled data std range : [{stds.min():.4f}, {stds.max():.4f}] (Expected ~1.0)")
    
    # 2. Correlation & Hierarchical Clustering
    print("\n[2/6] Computing descriptor correlations and clustering...")
    corr_matrix = np.corrcoef(X_scaled.T)
    
    # Report correlation thresholds
    thresholds = [0.7, 0.8, 0.9]
    for thresh in thresholds:
        pairs = []
        for i in range(len(descriptor_names)):
            for j in range(i+1, len(descriptor_names)):
                if abs(corr_matrix[i, j]) > thresh:
                    pairs.append(f"{descriptor_names[i]} & {descriptor_names[j]} (r={corr_matrix[i,j]:.2f})")
        print(f"  → Pairs with |r| > {thresh}: {len(pairs)}")
        if pairs:
            for p in pairs[:3]:  # Show top 3
                print(f"     - {p}")
    
    # Clustered Heatmap
    print("  → Generating clustered correlation heatmap...")
    linkage = hierarchy.linkage(corr_matrix, method='average')
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.clustermap(
        pd.DataFrame(corr_matrix, index=descriptor_names, columns=descriptor_names),
        row_linkage=linkage,
        col_linkage=linkage,
        cmap='coolwarm',
        center=0,
        vmin=-1, vmax=1,
        annot=False,  # Avoid clutter
        figsize=(10, 8),
        dendrogram_ratio=0.2,
        cbar_kws={'label': 'Pearson Correlation'}
    )
    plt.suptitle('Hierarchical Clustering of Descriptor Correlations', y=1.02, fontsize=14, fontweight='bold')
    heatmap_path = REPORT_DIR / "descriptor_correlation_clustered.png"
    plt.savefig(heatmap_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  → Clustered heatmap saved to {heatmap_path}")
    
    # 3. PCA Analysis
    print("\n[3/6] Performing PCA analysis...")
    pca_full = PCA()
    X_pca = pca_full.fit_transform(X_scaled)
    
    var_explained = pca_full.explained_variance_ratio_
    cumulative_var = np.cumsum(var_explained)
    eigenvalues = pca_full.explained_variance_
    
    print("  → Variance explained by each PC:")
    for i, (var, cum, eig) in enumerate(zip(var_explained, cumulative_var, eigenvalues)):
        kaiser_marker = " (Kaiser criterion met)" if eig >= 1.0 else ""
        print(f"     PC{i+1}: {var*100:.2f}% (cum: {cum*100:.2f}%, eigenval: {eig:.2f}){kaiser_marker}")
    
    # PCA Loadings: Top 3 per PC
    loadings = pca_full.components_.T
    loadings_df = pd.DataFrame(loadings, index=descriptor_names, columns=[f"PC{i+1}" for i in range(len(var_explained))])
    
    print("\n  → Top 3 descriptors by absolute loading per PC:")
    top_loadings = {}
    for pc_idx in range(min(5, len(var_explained))):
        pc_name = f"PC{pc_idx+1}"
        sorted_loadings = loadings_df[pc_name].abs().sort_values(ascending=False)
        top_3 = sorted_loadings.head(3).index.tolist()
        top_loadings[pc_name] = top_3
        print(f"     {pc_name}: {', '.join(top_3)}")
        
    # Communalities (sum of squared loadings across all PCs)
    communalities = np.sum(loadings**2, axis=1)
    communality_df = pd.DataFrame({'descriptor': descriptor_names, 'communality': np.round(communalities, 4)})
    communality_df = communality_df.sort_values('communality', ascending=False)
    print("\n  → Descriptor Communalities (representation quality):")
    for _, row in communality_df.head(5).iterrows():
        print(f"     {row['descriptor']}: {row['communality']:.4f}")
        
    loadings_path = REPORT_DIR / "pca_loadings_top.csv"
    loadings_df.to_csv(loadings_path)
    
    # Scree Plot with Kaiser Line
    print("  → Generating scree plot...")
    fig, ax1 = plt.subplots(figsize=(10, 6))
    pcs = np.arange(1, len(var_explained) + 1)
    ax1.bar(pcs, var_explained * 100, alpha=0.7, label='Individual Variance')
    ax1.plot(pcs, cumulative_var * 100, 'ro-', linewidth=2, markersize=8, label='Cumulative Variance')
    ax1.axhline(y=95, color='gray', linestyle='--', alpha=0.5, label='95% threshold')
    
    # Kaiser line (eigenvalue = 1)
    # Since data is standardized, total variance = 12. Eigenvalue 1 = 1/12 = 8.33%
    ax1.axhline(y=(1/len(descriptor_names))*100, color='black', linestyle=':', linewidth=2, label='Kaiser criterion (eigenval=1)')
    
    ax1.set_xlabel('Principal Component')
    ax1.set_ylabel('Variance Explained (%)')
    ax1.set_title('PCA Scree Plot with Kaiser Criterion')
    ax1.set_xticks(pcs)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    scree_path = REPORT_DIR / "pca_scree_plot.png"
    plt.savefig(scree_path, dpi=200)
    plt.close()
    print(f"  → Scree plot saved to {scree_path}")
    
    # 4. Descriptor Ablation (Leave-One-Out)
    print("\n[4/6] Running Leave-One-Descriptor-Out (LODO) Ablation...")
    baseline_p5 = compute_precision_at_k(X_scaled, filenames, labels_lookup, k=K)
    print(f"  → Baseline P@{K} (all 12 descriptors): {baseline_p5:.4f}")
    
    ablation_results = []
    for i, desc_name in enumerate(descriptor_names):
        # Drop descriptor i
        X_reduced = np.delete(X_scaled, i, axis=1)
        reduced_p5 = compute_precision_at_k(X_reduced, filenames, labels_lookup, k=K)
        delta = baseline_p5 - reduced_p5
        
        ablation_results.append({
            "descriptor": desc_name,
            "p5_with_all": round(baseline_p5, 4),
            "p5_without": round(reduced_p5, 4),
            "delta_p5": round(delta, 4)
        })
        
    ablation_df = pd.DataFrame(ablation_results)
    ablation_df = ablation_df.sort_values('delta_p5', ascending=False)  # Highest drop = most important
    
    ablation_path = REPORT_DIR / "descriptor_ablation_results.csv"
    ablation_df.to_csv(ablation_path, index=False)
    print(f"  → Ablation results saved to {ablation_path}")
    
    print("\n  → Descriptor Importance (Highest drop in P@5 when removed):")
    for _, row in ablation_df.head(5).iterrows():
        print(f"     {row['descriptor']:<25} ΔP@5 = {row['delta_p5']:+.4f} (P@5 drops to {row['p5_without']:.4f})")
        
    # 5. Save Summary JSON
    print("\n[5/6] Saving comprehensive summary...")
    summary = {
        "n_cases": len(filenames),
        "n_descriptors": len(descriptor_names),
        "baseline_p5": round(baseline_p5, 4),
        "variance_explained": [round(v, 4) for v in var_explained],
        "cumulative_variance": [round(v, 4) for v in cumulative_var],
        "eigenvalues": [round(e, 4) for e in eigenvalues],
        "top_loadings_per_pc": top_loadings,
        "communalities": communality_df.set_index('descriptor')['communality'].to_dict(),
        "ablation_results": ablation_df.to_dict(orient='records')
    }
    
    summary_path = REPORT_DIR / "descriptor_analysis.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  → Summary saved to {summary_path}")
    
    print("\n" + "=" * 85)
    print("✅ Descriptor analysis complete.")
    print("\nKey Insights:")
    print("  1. Hierarchical clustering reveals natural groupings of redundant descriptors.")
    print("  2. PCA communalities show how well each descriptor is represented in the latent space.")
    print("  3. LODO ablation directly identifies which physical measurements drive retrieval.")
    print("=" * 85)
    
    return True

if __name__ == "__main__":
    success = analyze_descriptors()
    if not success:
        sys.exit(1)