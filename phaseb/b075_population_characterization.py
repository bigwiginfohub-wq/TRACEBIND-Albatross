"""
TRACEBIND Phase B0.75: Population Characterization (CONSORT Pipeline)
======================================================================
Purpose: Apply the CONSORT-style filtering pipeline defined in the 
PHASE_B1_SAMPLING_PROTOCOL.md to characterize the eligible population.
Unit of analysis: ONE STORM (SID), not individual track records.
NO ERA5 downloads. NO descriptor extraction.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
IBTRACS_CSV = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\ibtracs_ALL.csv")
OUTPUT_DIR = Path(__file__).parent

# Protocol Constants
TARGET_BASINS = ['NI', 'SI', 'WP']
TEMPORAL_CUTOFF = 1980
WEAK_MAX = 64
MODERATE_MAX = 96

def classify_intensity(wind):
    if pd.isna(wind): return 'Unknown'
    if wind < WEAK_MAX: return 'Weak (<64kt)'
    elif wind < MODERATE_MAX: return 'Moderate (64-95kt)'
    else: return 'Intense (>=96kt)'

def run_characterization():
    print("=" * 85)
    print("PHASE B0.75: Population Characterization (Storm-Level CONSORT)")
    print("=" * 85)
    
    # 0. Load and Aggregate to Storm Level
    print("\n[0/5] Loading IBTrACS catalog and aggregating to storm level...")
    df_raw = pd.read_csv(IBTRACS_CSV, low_memory=False, dtype={'SEASON': str})
    
    # Clean messy numeric columns before aggregation
    df_raw['WMO_WIND'] = pd.to_numeric(df_raw['WMO_WIND'], errors='coerce')
    df_raw['WMO_PRES'] = pd.to_numeric(df_raw['WMO_PRES'], errors='coerce')
    
    # Aggregate: One row per unique storm (SID)
    storms = df_raw.groupby(['SID', 'BASIN', 'SEASON', 'NAME']).agg(
        max_wind_kt=('WMO_WIND', 'max'),
        min_pressure_hpa=('WMO_PRES', 'min'),
        first_time=('ISO_TIME', 'min')
    ).reset_index()
    
    storms['SEASON_INT'] = pd.to_numeric(storms['SEASON'], errors='coerce')
    storms['exclusion_reason'] = 'None' # Track why storms are excluded
    
    print(f"  → Total unique storms in global catalog: {len(storms):,}")
    
    # --- CONSORT PIPELINE ---
    
    # Gate 1: Target Basins
    print("\n[1/5] Applying Gate 1: Target Basins (NI, SI, WP)...")
    mask_basin = storms['BASIN'].isin(TARGET_BASINS)
    storms.loc[~mask_basin, 'exclusion_reason'] = 'Not in target basins'
    storms_g1 = storms[mask_basin].copy()
    excluded_g1 = (~mask_basin).sum()
    print(f"  → Remaining: {len(storms_g1):,} | Excluded: {excluded_g1:,}")
    
    # Gate 2: Temporal Cutoff
    print("\n[2/5] Applying Gate 2: Temporal Cutoff (SEASON >= 1980)...")
    mask_temp = storms_g1['SEASON_INT'] >= TEMPORAL_CUTOFF
    storms_g1.loc[~mask_temp, 'exclusion_reason'] = 'Pre-1980 (Temporal Cutoff)'
    storms_g2 = storms_g1[mask_temp].copy()
    excluded_g2 = (~mask_temp).sum()
    print(f"  → Remaining: {len(storms_g2):,} | Excluded: {excluded_g2:,}")
    
    # Gate 3: Tier 1 Metadata (Valid Wind)
    print("\n[3/5] Applying Gate 3: Tier 1 Core Metadata (Valid WMO Wind > 0)...")
    mask_wind = storms_g2['max_wind_kt'].notna() & (storms_g2['max_wind_kt'] > 0)
    storms_g2.loc[~mask_wind, 'exclusion_reason'] = 'Missing/Invalid Wind Metadata'
    tier1_pool = storms_g2[mask_wind].copy()
    excluded_g3 = (~mask_wind).sum()
    print(f"  → Tier 1 Eligible Pool: {len(tier1_pool):,} | Excluded: {excluded_g3:,}")
    
    # ADD INTENSITY CLASS HERE SO TIER 2 INHERITS IT
    tier1_pool['intensity_class'] = tier1_pool['max_wind_kt'].apply(classify_intensity)

    # Gate 4: Tier 2 Extended Metadata (Valid Pressure)
    print("\n[4/5] Applying Gate 4: Tier 2 Extended Metadata (Valid WMO Pressure < 1050)...")
    mask_pres = tier1_pool['min_pressure_hpa'].notna() & (tier1_pool['min_pressure_hpa'] < 1050)
    tier1_pool.loc[~mask_pres, 'exclusion_reason'] = 'Missing/Invalid Pressure Metadata'
    tier2_pool = tier1_pool[mask_pres].copy()
    excluded_g4 = (~mask_pres).sum()
    print(f"  → Tier 2 Eligible Pool: {len(tier2_pool):,} | Excluded: {excluded_g4:,}")
    
    # --- CHARACTERIZATION & REPORTING ---
    
    print("\n[5/5] Generating CONSORT Flow and Stratum Characterization...")
    
    # 1. CONSORT Flow Diagram
    print("\n" + "=" * 85)
    print("CONSORT FLOW DIAGRAM (Tropical Cyclones)")
    print("=" * 85)
    print(f"  Global Unique Storms ................................ {len(storms):,}")
    print(f"    [-] Excluded: Not in target basins (NI, SI, WP) ... -{excluded_g1:,}")
    print(f"  Gate 1: Target Basins ............................... {len(storms_g1):,}")
    print(f"    [-] Excluded: Pre-1980 (Temporal Cutoff) .......... -{excluded_g2:,}")
    print(f"  Gate 2: Temporal Cutoff (>= 1980) ................... {len(storms_g2):,}")
    print(f"    [-] Excluded: Missing/Invalid Wind Metadata ....... -{excluded_g3:,}")
    print(f"  Gate 3: TIER 1 ELIGIBLE POOL (Valid Wind) ........... {len(tier1_pool):,}")
    print(f"    [-] Excluded: Missing/Invalid Pressure Metadata ... -{excluded_g4:,}")
    print(f"  Gate 4: TIER 2 ELIGIBLE POOL (Wind + Pressure) ...... {len(tier2_pool):,}")
    
    # 2. Tier 1 Stratification (Basin x Intensity)
    print("\nTIER 1 ELIGIBLE POOL BREAKDOWN (Basin x Intensity):")
    summary_t1 = tier1_pool.groupby(['BASIN', 'intensity_class']).size().unstack(fill_value=0)
    summary_t1['TOTAL'] = summary_t1.sum(axis=1)
    print(summary_t1.to_string())
    
    # 3. Tier 1 Decade Distribution
    tier1_pool['DECADE'] = tier1_pool['SEASON'].apply(lambda x: str(int(x) // 10 * 10) + 's' if str(x).isdigit() else 'Unknown')
    print("\nTIER 1 ELIGIBLE POOL BREAKDOWN (Basin x Decade):")
    decade_summary = tier1_pool.groupby(['BASIN', 'DECADE']).size().unstack(fill_value=0)
    print(decade_summary.to_string())
    
    # --- SAVE DELIVERABLES ---
    
    # Save Eligible Pools
    cols_to_save = ['SID', 'BASIN', 'SEASON', 'NAME', 'max_wind_kt', 'min_pressure_hpa', 'intensity_class']
    tier1_pool[cols_to_save].to_csv(OUTPUT_DIR / "b075_eligible_tier1.csv", index=False)
    tier2_pool[cols_to_save].to_csv(OUTPUT_DIR / "b075_eligible_tier2.csv", index=False)
    
    # Save Exclusion Log (Crucial for reproducibility)
    excluded_storms = storms[storms['exclusion_reason'] != 'None']
    excluded_storms[['SID', 'BASIN', 'SEASON', 'NAME', 'exclusion_reason']].to_csv(
        OUTPUT_DIR / "b075_exclusion_log.csv", index=False
    )
    
    print(f"\n  → Saved Tier 1 eligible pool to: b075_eligible_tier1.csv")
    print(f"  → Saved Tier 2 eligible pool to: b075_eligible_tier2.csv")
    print(f"  → Saved exclusion log to: b075_exclusion_log.csv")
    
    print("\n" + "=" * 85)
    print("✅ Population Characterization Complete.")
    print("Review the CONSORT flow and stratum sizes above to finalize Phase B1 sampling.")
    print("=" * 85)

if __name__ == "__main__":
    run_characterization()