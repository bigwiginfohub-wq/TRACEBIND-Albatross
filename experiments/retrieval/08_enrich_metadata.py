"""
TRACEBIND-Albatross: Retrieval Experiment — Step 8 (Final Phase A)
===================================================================
Metadata Enrichment Utility

Purpose: Enrich the dataset with comprehensive meteorological metadata 
(e.g., from IBTrACS) to enable multi-label retrieval evaluation.
This script is designed to be reused unchanged in Phase B.

Inputs:
- labels/storm_labels_rich.csv (Current baseline)
- labels/ibtracs_metadata.csv (Optional: External catalog export)

Outputs:
- labels/storm_labels_comprehensive.csv
"""

import pandas as pd
from pathlib import Path

LABELS_DIR = Path(__file__).parent / "labels"
CURRENT_LABELS = LABELS_DIR / "storm_labels_rich.csv"
EXTERNAL_METADATA = LABELS_DIR / "ibtracs_metadata.csv"
OUTPUT_LABELS = LABELS_DIR / "storm_labels_comprehensive.csv"

def enrich_metadata():
    print("=" * 85)
    print("PHASE A: Step 8 — Metadata Enrichment Utility")
    print("=" * 85)
    
    if not CURRENT_LABELS.exists():
        print(f"❌ Current labels not found: {CURRENT_LABELS}")
        return False
        
    df_current = pd.read_csv(CURRENT_LABELS)
    print(f"  → Loaded {len(df_current)} baseline cases.")
    
    # Attempt merge
    if EXTERNAL_METADATA.exists():
        print(f"  → Found external metadata. Attempting merge...")
        df_external = pd.read_csv(EXTERNAL_METADATA)
        merge_key = 'original_case_id'
        if merge_key in df_current.columns and merge_key in df_external.columns:
            df_enriched = pd.merge(df_current, df_external, on=merge_key, how='left')
            print("  → Merge successful.")
        else:
            print("  ⚠️  Merge key not found. Generating template for manual completion.")
            df_enriched = df_current.copy()
    else:
        print("  ⚠️  External metadata not found. Generating template for manual completion.")
        print("  💡 Tip: Search IBTrACS for the storm names and fill the missing columns.")
        df_enriched = df_current.copy()
        
    # Enforce comprehensive schema
    target_columns = [
        'filename', 'original_case_id', 'storm_name', 
        'basin', 'season', 'month',
        'max_wind_kt', 'min_pressure_hpa', 'max_category',
        'duration_hours', 'landfall_yn'
    ]
    
    for col in target_columns:
        if col not in df_enriched.columns:
            df_enriched[col] = None
            
    # Reorder
    existing_cols = [c for c in target_columns if c in df_enriched.columns]
    other_cols = [c for c in df_enriched.columns if c not in target_columns]
    df_enriched = df_enriched[existing_cols + other_cols]
    
    df_enriched.to_csv(OUTPUT_LABELS, index=False)
    print(f"  ✅ Saved comprehensive metadata to: {OUTPUT_LABELS}")
    
    missing = df_enriched[target_columns].isna().sum().sum()
    if missing > 0:
        print(f"\n⚠️  {missing} missing values detected in target columns.")
        print("Please fill these manually or provide ibtracs_metadata.csv, then re-run.")
    else:
        print("\n✅ All target metadata columns are fully populated!")
        
    print("=" * 85)
    return True

if __name__ == "__main__":
    enrich_metadata()