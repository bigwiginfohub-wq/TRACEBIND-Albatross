"""
TRACEBIND-Albatross: Retrieval Experiment — Step 2
===================================================
Build PCA Database from Descriptor Database

Purpose: Load the frozen descriptor database (Step 1), standardize features,
compute PCA (retaining 95% variance), and save the trained model for future 
projection of new cases.

This script does NOT perform retrieval. It only builds the representation space.

Inputs:
- outputs/descriptor_database.csv (from Step 1)

Outputs:
- outputs/descriptor_matrix_scaled.csv (debugging/inspection)
- outputs/pca_coordinates.csv (per-case PCA coordinates)
- outputs/pca_summary.json (explained variance, loadings, normalization metadata)
- models/scaler.pkl (fitted StandardScaler)
- models/pca.pkl (fitted PCA model)
- outputs/variance_explained.png (diagnostic plot)
"""

import sys
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# ============================================================================
# Configuration
# ============================================================================
INPUT_CSV = Path(__file__).parent / "outputs" / "descriptor_database.csv"
OUTPUT_DIR = Path(__file__).parent / "outputs"
MODEL_DIR = Path(__file__).parent / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Retrieval descriptors only (excludes filename and metadata)
RETRIEVAL_DESCRIPTORS = [
    "global_c_phi",
    "max_vorticity",
    "center_vorticity",
    "max_wind_speed",
    "mean_wind_speed",
    "mean_local_c_phi",
    "std_local_c_phi",
    "min_local_c_phi",
    "max_local_c_phi",
    "p25_local_c_phi",
    "p75_local_c_phi",
    "median_center_distance"
]

# ============================================================================
# Main Execution
# ============================================================================
def build_pca_database():
    print("=" * 85)
    print("RETRIEVAL EXPERIMENT: Step 2 — Build PCA Database")
    print("=" * 85)
    
    # 1. Load descriptor database
    print(f"\n[1/6] Loading descriptor database from {INPUT_CSV}...")
    if not INPUT_CSV.exists():
        print(f"❌ Input file not found: {INPUT_CSV}")
        print("   Run 01_build_descriptor_database.py first.")
        return False
    
    df = pd.read_csv(INPUT_CSV)
    print(f"  → Loaded {len(df)} cases.")
    
    # Filter to successful extractions only
    if "extraction_status" in df.columns:
        df = df[df["extraction_status"] == "success"].copy()
        print(f"  → {len(df)} cases with successful extraction status.")
    
    # 2. Select retrieval descriptors
    print("\n[2/6] Selecting retrieval descriptors...")
    missing_cols = [c for c in RETRIEVAL_DESCRIPTORS if c not in df.columns]
    if missing_cols:
        print(f"❌ Missing descriptor columns: {missing_cols}")
        return False
    
    X = df[RETRIEVAL_DESCRIPTORS].values.astype('float64')
    filenames = df["filename"].values
    
    # Check for NaNs
    if np.isnan(X).any():
        print("❌ NaN values detected in descriptor matrix.")
        print("   Check descriptor_database.csv for failed extractions.")
        return False
    
    print(f"  → Descriptor matrix shape: {X.shape}")
    print(f"  → Features: {RETRIEVAL_DESCRIPTORS}")
    
    # 3. Standardize features
    print("\n[3/6] Standardizing features (StandardScaler)...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Save scaled matrix for debugging/inspection
    scaled_df = pd.DataFrame(X_scaled, columns=RETRIEVAL_DESCRIPTORS)
    scaled_df.insert(0, "filename", filenames)
    scaled_path = OUTPUT_DIR / "descriptor_matrix_scaled.csv"
    scaled_df.to_csv(scaled_path, index=False)
    print(f"  → Scaled descriptor matrix saved to {scaled_path}")
    
    # Save scaler
    scaler_path = MODEL_DIR / "scaler.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"  → Scaler saved to {scaler_path}")
    
    # 4. Compute PCA (retain 95% of variance)
    print("\n[4/6] Computing PCA (retaining 95% variance)...")
    pca = PCA(n_components=0.95)
    X_pca = pca.fit_transform(X_scaled)
    n_retained = pca.n_components_
    print(f"  → Retained {n_retained} out of {X.shape[1]} components to explain 95% variance.")
    
    # Save PCA model
    pca_path = MODEL_DIR / "pca.pkl"
    with open(pca_path, "wb") as f:
        pickle.dump(pca, f)
    print(f"  → PCA model saved to {pca_path}")
    
    # 5. Save outputs
    print("\n[5/6] Saving outputs and metadata...")
    
    # PCA coordinates
    pca_df = pd.DataFrame(X_pca, columns=[f"PC{i+1}" for i in range(n_retained)])
    pca_df.insert(0, "filename", filenames)
    coords_path = OUTPUT_DIR / "pca_coordinates.csv"
    pca_df.to_csv(coords_path, index=False)
    print(f"  → PCA coordinates saved to {coords_path}")
    
    # PCA summary (JSON) - human readable metadata
    model_summary = {
        "n_cases": len(filenames),
        "n_input_features": X.shape[1],
        "n_components_retained": int(n_retained),
        "variance_threshold": 0.95,
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "cumulative_explained_variance": np.cumsum(pca.explained_variance_ratio_).tolist(),
        "eigenvalues": pca.explained_variance_.tolist(),
        "feature_means": scaler.mean_.tolist(),
        "feature_stds": scaler.scale_.tolist(),
        "feature_names": RETRIEVAL_DESCRIPTORS,
        "loadings": {
            f"PC{i+1}": pca.components_[i].tolist()
            for i in range(n_retained)
        }
    }
    
    summary_path = OUTPUT_DIR / "pca_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(model_summary, f, indent=2)
    print(f"  → PCA summary saved to {summary_path}")
    
    # Variance explained plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    components = np.arange(1, n_retained + 1)
    ax1.bar(components, pca.explained_variance_ratio_, color='#1f77b4', alpha=0.8)
    ax1.set_xlabel("Principal Component")
    ax1.set_ylabel("Explained Variance Ratio")
    ax1.set_title("Per-Component Variance Explained")
    ax1.set_xticks(components)
    ax1.grid(axis='y', alpha=0.3)
    
    cumulative = np.cumsum(pca.explained_variance_ratio_)
    ax2.plot(components, cumulative, 'o-', color='#d62728', linewidth=2, markersize=8)
    ax2.axhline(0.95, color='gray', linestyle='--', alpha=0.7, label='95% threshold')
    ax2.set_xlabel("Number of Components")
    ax2.set_ylabel("Cumulative Explained Variance")
    ax2.set_title("Cumulative Variance Explained")
    ax2.set_xticks(components)
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plot_path = OUTPUT_DIR / "variance_explained.png"
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"  → Variance plot saved to {plot_path}")
    
    # 6. Reload Verification (Crucial for proving the model is usable)
    print("\n[6/6] Verifying saved models (Reload Test)...")
    with open(scaler_path, "rb") as f:
        scaler_test = pickle.load(f)
    with open(pca_path, "rb") as f:
        pca_test = pickle.load(f)
    
    # Reproject the original data using the loaded models
    X_test = pca_test.transform(scaler_test.transform(X))
    
    # Check if it matches the originally computed X_pca
    if np.allclose(X_pca, X_test, atol=1e-6):
        print("  ✅ Reload verification PASSED. Coordinates match within 1e-6 tolerance.")
    else:
        print("  ❌ Reload verification FAILED. Saved models do not reproduce coordinates.")
        return False
    
    # Summary report
    print("\n" + "=" * 85)
    print("PCA SUMMARY")
    print("=" * 85)
    print(f"  Cases:                 {len(filenames)}")
    print(f"  Input features:        {X.shape[1]}")
    print(f"  Components retained:   {n_retained} (95% variance threshold)")
    print(f"  PC1 variance:          {pca.explained_variance_ratio_[0]*100:.2f}%")
    print(f"  PC1+PC2 variance:      {sum(pca.explained_variance_ratio_[:2])*100:.2f}%")
    print(f"  PC1+PC2+PC3 variance:  {sum(pca.explained_variance_ratio_[:3])*100:.2f}%")
    
    print("\nTop 3 features by PC1 loading magnitude:")
    pc1_loadings = pca.components_[0]
    abs_loadings = np.abs(pc1_loadings)
    top3_idx = np.argsort(abs_loadings)[-3:][::-1]
    for idx in top3_idx:
        print(f"  - {RETRIEVAL_DESCRIPTORS[idx]:<25} loading = {pc1_loadings[idx]:+.4f}")
    
    print("=" * 85)
    print("✅ Step 2 complete. PCA representation space is verified and ready.")
    print("   Next: 03_build_tracebind_index.py")
    print("=" * 85)
    
    return True

if __name__ == "__main__":
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
    except ImportError:
        print("❌ Missing dependencies. Please run: pip install scikit-learn")
        sys.exit(1)
    
    success = build_pca_database()
    if not success:
        sys.exit(1)