"""
Generate IBTrACS metadata for the 10 pilot cyclones using verified SIDs.
This ensures 100% accurate matching and full provenance.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

IBTRACS_CSV = Path(__file__).parent / "ibtracs_ALL.csv"
OUTPUT_METADATA = Path(__file__).parent / "ibtracs_metadata.csv"

# Verified mapping from diagnostic output
TARGET_STORMS = {
    "TC_2023_MOCHA": "2023129N08091",
    "TC_2020_AMPHAN": "2020136N10088",
    "TC_2019_FANI": "2019116N02090",
    "TC_2008_NARGIS": "2008117N11090",
    "TC_2021_TAUKTAE": "2021133N10071",
    "TC_2021_YAAS": "2021143N15090",
    "TC_2019_KYARR": "2019296N15066",
    "TC_2014_HUDHUD": "2014279N11096",
    "TC_2013_PHAILIN": "2013281N12098",
    "TC_2019_BULBUL": "2019302N11118",
}

def generate_metadata():
    print("=" * 85)
    print("Generating Verified IBTrACS Metadata")
    print("=" * 85)
    
    print("\n[1/3] Loading IBTrACS data...")
    df = pd.read_csv(IBTRACS_CSV, low_memory=False)
    print(f"  → Loaded {len(df):,} total records.")
    
    records = []
    
    print("\n[2/3] Extracting data for verified SIDs...")
    for case_id, sid in TARGET_STORMS.items():
        storm_data = df[df['SID'] == sid]
        
        if len(storm_data) == 0:
            print(f"  ⚠️  SID {sid} not found!")
            continue
            
        name = storm_data['NAME'].iloc[0]
        
        # Safely convert to numeric, coercing spaces to NaN
        winds = pd.to_numeric(storm_data['WMO_WIND'], errors='coerce')
        max_wind = winds.max()
        
        pres = pd.to_numeric(storm_data['WMO_PRES'], errors='coerce')
        min_pres = pres.min()
        
        cat = pd.to_numeric(storm_data['USA_SSHS'], errors='coerce')
        max_cat = cat.max()
        
        times = pd.to_datetime(storm_data['ISO_TIME'], errors='coerce')
        duration = (times.max() - times.min()).total_seconds() / 3600
        
        # Landfall check: DIST2LAND <= 0 means it hit land
        if 'DIST2LAND' in storm_data.columns:
            dist2land = pd.to_numeric(storm_data['DIST2LAND'], errors='coerce')
            landfall_yn = 'Y' if (dist2land <= 0).any() else 'N'
        else:
            landfall_yn = 'N' # Fallback
            
        records.append({
            'original_case_id': case_id,
            'storm_name': name,
            'ibtracs_id': sid,
            'max_wind_kt': round(max_wind, 1) if pd.notna(max_wind) else np.nan,
            'min_pressure_hpa': round(min_pres, 1) if pd.notna(min_pres) else np.nan,
            'max_category': int(max_cat) if pd.notna(max_cat) else np.nan,
            'duration_hours': round(duration, 1) if pd.notna(duration) else np.nan,
            'landfall_yn': landfall_yn,
            'source_agency': 'WMO (IBTrACS)',
            'retrieval_date': datetime.now().strftime('%Y-%m-%d')
        })
        print(f"  ✓ {case_id:<18} | {name:<15} | Wind: {max_wind:>3.0f}kt | Pres: {min_pres:>4.0f}hPa | Cat: {max_cat} | Landfall: {landfall_yn}")
        
    # Add controls (not in IBTrACS, but needed for schema consistency)
    control_storms = [
        "CTRL_2023_IND_01", "CTRL_2023_IND_02", "CTRL_2022_MON_LOW1", "CTRL_2022_MON_LOW2",
        "CTRL_2021_TROUGH1", "CTRL_2021_DEP_01", "CTRL_2020_SHEAR_01", "CTRL_2020_SURGE_01",
        "CTRL_2019_TROUGH2", "CTRL_2018_LOW_03"
    ]
    for ctrl_id in control_storms:
        records.append({
            'original_case_id': ctrl_id,
            'storm_name': ctrl_id,
            'ibtracs_id': 'NA',
            'max_wind_kt': np.nan, 'min_pressure_hpa': np.nan, 'max_category': np.nan,
            'duration_hours': np.nan, 'landfall_yn': 'NA', 'source_agency': 'NA',
            'retrieval_date': datetime.now().strftime('%Y-%m-%d')
        })
        
    df_out = pd.DataFrame(records)
    df_out.to_csv(OUTPUT_METADATA, index=False)
    
    print(f"\n[3/3] ✅ Saved verified metadata to: {OUTPUT_METADATA}")
    print("=" * 85)

if __name__ == "__main__":
    generate_metadata()