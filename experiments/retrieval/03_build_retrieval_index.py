"""
TRACEBIND-Albatross: Retrieval Experiment — Step 3
===================================================
Build Retrieval Index

Purpose: Load a vector representation, compute a pairwise distance matrix, 
and generate nearest-neighbor rankings for every query case.

This script is STRICTLY REPRESENTATION-AGNOSTIC. It knows only:
- filenames
- feature vectors
- distance metric

It does NOT evaluate retrieval quality. It only produces the index and 
rankings for downstream evaluation and visual inspection.

Inputs:
- Vector database CSV (must have 'filename' column + numeric feature columns)
- Distance metric (default: "euclidean")

Outputs:
- models/distance_matrix_{metric}.npy (exact pairwise distances)
- reports/rankings_{metric}.csv (complete ranking matrix)
- reports/sample_rankings_{metric}.txt (human-readable sample)
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from sklearn.metrics import pairwise_distances

# ============================================================================
# Configuration
# ============================================================================
OUTPUT_DIR = Path(__file__).parent / "outputs"
MODEL_DIR = Path(__file__).parent / "models"
REPORT_DIR = Path(__file__).parent / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Main Execution
# ============================================================================
def build_retrieval_index(vector_csv_path: Path, metric: str = "euclidean"):
    print("=" * 85)
    print("RETRIEVAL EXPERIMENT: Step 3 — Build Retrieval Index")
    print("=" * 85)
    
    representation_name = vector_csv_path.stem
    print(f"\nRepresentation: {representation_name}")
    print(f"Distance Metric: {metric}")
    print(f"Input: {vector_csv_path}")
    
    # 1. Load vector database
    print(f"\n[1/5] Loading vector database...")
    if not vector_csv_path.exists():
        print(f"❌ Input file not found: {vector_csv_path}")
        return False
    
    df = pd.read_csv(vector_csv_path)
    print(f"  → Loaded {len(df)} cases.")
    
    if "filename" not in df.columns:
        print("❌ CSV must have a 'filename' column.")
        return False
    
    filenames = df["filename"].values
    feature_cols = [c for c in df.columns if c != "filename"]
    X = df[feature_cols].values.astype('float64')
    
    print(f"  → Feature matrix shape: {X.shape}")
    
    if np.isnan(X).any():
        print("❌ NaN values detected in feature matrix.")
        return False
    
    # 2. Compute pairwise distance matrix
    print(f"\n[2/5] Computing pairwise '{metric}' distances...")
    # Using pairwise_distances to allow configurable metrics (euclidean, cosine, manhattan, etc.)
    distance_matrix = pairwise_distances(X, metric=metric)
    print(f"  → Distance matrix shape: {distance_matrix.shape}")
    
    # Save distance matrix as NumPy array for exact reproducibility and future metric testing
    dist_path = MODEL_DIR / f"distance_matrix_{representation_name}_{metric}.npy"
    np.save(dist_path, distance_matrix)
    print(f"  → Distance matrix saved to {dist_path}")
    
    # 3. Rank neighbors for each query
    print(f"\n[3/5] Ranking nearest neighbors for each query case...")
    rankings = []
    
    for i, query_filename in enumerate(filenames):
        distances = distance_matrix[i]
        
        # Create (filename, distance) pairs, excluding self-match (distance == 0)
        neighbors = []
        for j, neighbor_filename in enumerate(filenames):
            if i != j:
                neighbors.append({
                    "query": query_filename,
                    "neighbor": neighbor_filename,
                    "distance": float(distances[j]),
                    "rank": 0
                })
        
        # Sort by distance (ascending)
        neighbors.sort(key=lambda x: x["distance"])
        
        # Assign ranks
        for rank, neighbor in enumerate(neighbors, start=1):
            neighbor["rank"] = rank
            rankings.append(neighbor)
    
    # 4. Save outputs
    print(f"\n[4/5] Saving ranking outputs...")
    
    rankings_df = pd.DataFrame(rankings)
    rankings_path = REPORT_DIR / f"rankings_{representation_name}_{metric}.csv"
    rankings_df.to_csv(rankings_path, index=False)
    print(f"  → Complete ranking matrix saved to {rankings_path}")
    
    # Save sample rankings (first 5 queries, top 10 neighbors each)
    sample_path = REPORT_DIR / f"sample_rankings_{representation_name}_{metric}.txt"
    with open(sample_path, "w", encoding="utf-8") as f:
        f.write(f"Retrieval Index - Sample Rankings\n")
        f.write(f"Representation: {representation_name}\n")
        f.write(f"Distance Metric: {metric}\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("=" * 85 + "\n\n")
        
        for i, query_filename in enumerate(filenames[:5]):
            f.write(f"Query {i+1}: {query_filename}\n")
            f.write("-" * 85 + "\n")
            
            query_rankings = rankings_df[rankings_df["query"] == query_filename].head(10)
            for _, row in query_rankings.iterrows():
                f.write(f"  Rank {row['rank']:2d}: {row['neighbor']:<30} distance = {row['distance']:.4f}\n")
            f.write("\n")
    
    print(f"  → Sample rankings saved to {sample_path}")
    
    # 5. Summary statistics
    print("\n[5/5] Generating summary statistics...")
    all_distances = rankings_df["distance"].values
    
    print("\n" + "=" * 85)
    print("RETRIEVAL INDEX SUMMARY")
    print("=" * 85)
    print(f"  Representation:        {representation_name}")
    print(f"  Cases:                 {len(filenames)}")
    print(f"  Dimensions:            {X.shape[1]}")
    print(f"  Distance metric:       {metric}")
    print(f"  Total rankings:        {len(rankings)}")
    print(f"\n  Distance statistics:")
    print(f"    Min (non-zero):      {all_distances[all_distances > 0].min():.4f}")
    print(f"    Mean:                {all_distances.mean():.4f}")
    print(f"    Median:              {np.median(all_distances):.4f}")
    print(f"    Max:                 {all_distances.max():.4f}")
    print("=" * 85)
    print("✅ Step 3 complete. Retrieval index is ready for inspection.")
    print(f"   Review: {sample_path}")
    print("=" * 85)
    
    return True

# ============================================================================
# Command-line interface
# ============================================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build retrieval index for a vector representation.")
    parser.add_argument("vector_csv", type=Path, help="Path to vector database CSV")
    parser.add_argument("--metric", type=str, default="euclidean", 
                        help="Distance metric (default: euclidean, options: cosine, manhattan, etc.)")
    
    args = parser.parse_args()
    
    try:
        from sklearn.metrics import pairwise_distances
    except ImportError:
        print("❌ Missing dependencies. Please run: pip install scikit-learn")
        sys.exit(1)
    
    success = build_retrieval_index(args.vector_csv, metric=args.metric)
    if not success:
        sys.exit(1)