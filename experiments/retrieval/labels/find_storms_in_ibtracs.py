"""
Find North Indian Ocean cyclones by year and intensity.
Handles messy IBTrACS data (empty strings, spaces) safely.
"""
import pandas as pd
import numpy as np
from pathlib import Path

IBTRACS_CSV = Path(__file__).parent / "ibtracs_ALL.csv"

print("Loading IBTrACS data (this may take a moment)...")
# Force SEASON to string to avoid int/str matching issues
df = pd.read_csv(IBTRACS_CSV, low_memory=False, dtype={'SEASON': str})

# Filter for North Indian Ocean
df_ni = df[df['BASIN'] == 'NI'].copy()
print(f"Found {len(df_ni):,} North Indian Ocean records.")

# Target years as strings
target_years = ['2008', '2013', '2014', '2019', '2020', '2021', '2023']

print(f"\nSearching for major cyclones in years: {target_years}")
print("=" * 130)

for year in sorted(target_years):
    df_year = df_ni[df_ni['SEASON'] == year].copy()
    
    if len(df_year) == 0:
        continue
        
    unique_sids = df_year['SID'].unique()
    
    print(f"\n{year}: Found {len(unique_sids)} distinct storms")
    print("-" * 130)
    
    for sid in unique_sids[:15]:  # Show up to 15 storms per year
        storm_data = df_year[df_year['SID'] == sid]
        
        # Handle name safely
        name = storm_data['NAME'].iloc[0] if 'NAME' in storm_data.columns else "UNKNOWN"
        if pd.isna(name) or str(name).strip() == '':
            name = "UNNAMED"
            
        # Safely convert to numeric, coercing spaces/strings to NaN
        if 'WMO_WIND' in storm_data.columns:
            winds = pd.to_numeric(storm_data['WMO_WIND'], errors='coerce')
            max_wind = winds.max()
        else:
            max_wind = np.nan
            
        if 'WMO_PRES' in storm_data.columns:
            pres = pd.to_numeric(storm_data['WMO_PRES'], errors='coerce')
            min_pres = pres.min()
        else:
            min_pres = np.nan
            
        # Calculate duration
        times = pd.to_datetime(storm_data['ISO_TIME'], errors='coerce')
        if times.notna().any():
            duration = (times.max() - times.min()).total_seconds() / 3600
        else:
            duration = np.nan
            
        # Format safely for printing
        wind_str = f"{max_wind:>3.0f}" if pd.notna(max_wind) else " N/A"
        pres_str = f"{min_pres:>4.0f}" if pd.notna(min_pres) else " N/A"
        dur_str = f"{duration:>6.1f}" if pd.notna(duration) else " N/A"
        
        print(f"  SID: {sid:<16} | Name: {str(name):<15} | Max Wind: {wind_str}kt | Min Pres: {pres_str}hPa | Duration: {dur_str}h")