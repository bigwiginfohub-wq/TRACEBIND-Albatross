"""
Extract valid_time from all ERA5 files to derive Month and Season labels.
Note: A single timestamp cannot determine lifecycle stage. We derive only Month and Season.
"""
import xarray as xr
import pandas as pd
from pathlib import Path

DATA_DIR = Path(r"C:\TRACEBIND-Atmosphere\phase8\c2\raw")
OUTPUT_PATH = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\storm_labels_with_time.csv")
RICH_LABELS_PATH = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\storm_labels_rich.csv")

# Load the existing rich labels to get the baseline metadata
existing_labels = pd.read_csv(RICH_LABELS_PATH)

records = []
for filepath in sorted(DATA_DIR.glob("*.nc")):
    filename = filepath.name
    try:
        ds = xr.open_dataset(filepath)
        
        # Safely parse the native datetime64 value
        dt = pd.to_datetime(ds["valid_time"].values[0])
        
        month = dt.strftime("%B") # e.g., "May"
        year = dt.year
        
        # Seasons defined according to North Indian Ocean climatology.
        if dt.month in [11, 12, 1, 2, 3]:
            season = "Post_Monsoon_Winter"
        elif dt.month in [4, 5]:
            season = "Pre_Monsoon"
        elif dt.month in [6, 7, 8, 9]:
            season = "Monsoon"
        elif dt.month == 10:
            season = "Post_Monsoon"
        else:
            season = "Unknown"
            
        ds.close()
        
        # Merge with existing labels
        existing_row = existing_labels[existing_labels['filename'] == filename].iloc[0]
        
        records.append({
            "filename": filename,
            "case_type": existing_row['case_type'],
            "basin": existing_row['basin'],
            "original_case_id": existing_row['original_case_id'],
            "year": year,
            "month": month,
            "season": season
        })
    except Exception as e:
        print(f"Error processing {filename}: {e}")

df = pd.DataFrame(records)
df.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Saved enriched labels to {OUTPUT_PATH}")
print("\nDerived Labels:")
print(df[['filename', 'month', 'season']].to_string(index=False))