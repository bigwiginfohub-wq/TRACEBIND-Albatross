"""
TRACEBIND Phase B0.5: Dataset Census
=====================================
Purpose: Characterize the available tropical cyclone population in IBTrACS 
to inform the Phase B1 sampling strategy. 
NO descriptor extraction. NO ERA5 downloads.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
# Point to the existing IBTrACS file from Phase A to avoid duplication
IBTRACS_CSV = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\ibtracs_ALL.csv")
OUTPUT_CENSUS = Path(__file__).parent / "b05_storm_census.csv"

# Target Basins (IBTrACS codes)
# NI = North Indian, SI = South Indian, WP = Western North Pacific
TARGET_BASINS = ['NI', 'SI', 'WP']

def run_census():
    print("=" * 85)
    print("PHASE B0.5: IBTrACS Population Census")
    print("=" * 85)
    
    # 1. Load Data
    print("\n[1/4] Loading IBTrACS catalog...")
    if not IBTRACS_CSV.exists():
        print(f"❌ Error: IBTrACS file not found at {IBTRACS_CSV}")
        return
        
    df = pd.read_csv(IBTRACS_CSV, low_memory=False, dtype={'SEASON': str})
    print(f"  → Loaded {len(df):,} total global records.")
    
    # 2. Filter Target Basins
    print("\n[2/4] Filtering target basins (NI, SI, WP)...")
    df_target = df[df['BASIN'].isin(TARGET_BASINS)].copy()
    print(f"  → {len(df_target):,} records found in target basins.")
    
    # Clean messy numeric columns (spaces to NaN)
    for col in ['WMO_WIND', 'WMO_PRES', 'USA_SSHS']:
        if col in df_target.columns:
            df_target[col] = pd.to_numeric(df_target[col], errors='coerce')
            
    # 3. Aggregate to Storm Level
    print("\n[3/4] Aggregating to storm-level statistics...")
    storm_stats = df_target.groupby(['SID', 'BASIN', 'SEASON', 'NAME']).agg(
        max_wind_kt=('WMO_WIND', 'max'),
        min_pressure_hpa=('WMO_PRES', 'min'),
        max_category=('USA_SSHS', 'max'),
        record_count=('ISO_TIME', 'count'), # Proxy for data completeness/duration
        first_time=('ISO_TIME', 'min'),
        last_time=('ISO_TIME', 'max')
    ).reset_index()
    
    # Define Intensity Classes strictly by WMO Wind Speed
    def classify_intensity(wind):
        if pd.isna(wind): return 'Unknown'
        if wind < 64: return 'Weak (<64kt)'
        elif wind < 96: return 'Moderate (64-95kt)'
        else: return 'Intense (>=96kt)'
        
    storm_stats['intensity_class'] = storm_stats['max_wind_kt'].apply(classify_intensity)
    
    # Save the full census for B1 sampling
    storm_stats.to_csv(OUTPUT_CENSUS, index=False)
    print(f"  → Saved full storm-level census to: {OUTPUT_CENSUS}")
    
    # 4. Generate Summary Report
    print("\n[4/4] Generating Population Summary...")
    print("-" * 85)
    
    # Summary by Basin and Intensity
    summary = storm_stats.groupby(['BASIN', 'intensity_class']).size().unstack(fill_value=0)
    summary['TOTAL'] = summary.sum(axis=1)
    
    print("\nAVAILABLE STORMS BY BASIN AND INTENSITY CLASS:")
    print(summary.to_string())
    
    # Summary by Decade
    storm_stats['DECADE'] = storm_stats['SEASON'].apply(lambda x: str(int(x) // 10 * 10) + 's' if str(x).isdigit() else 'Unknown')
    decade_summary = storm_stats.groupby(['BASIN', 'DECADE']).size().unstack(fill_value=0)
    
    print("\nAVAILABLE STORMS BY BASIN AND DECADE:")
    print(decade_summary.to_string())
    
    # Metadata Completeness
    print("\nMETADATA COMPLETENESS (Target Basins):")
    print(f"  → Storms with valid Max Wind: {storm_stats['max_wind_kt'].notna().sum()} / {len(storm_stats)}")
    print(f"  → Storms with valid Min Pressure: {storm_stats['min_pressure_hpa'].notna().sum()} / {len(storm_stats)}")
    print(f"  → Storms with valid Category: {storm_stats['max_category'].notna().sum()} / {len(storm_stats)}")
    
    print("\n" + "=" * 85)
    print("✅ Census Complete. Review the summary above to finalize Phase B1 sampling.")
    print("=" * 85)

if __name__ == "__main__":
    run_census()