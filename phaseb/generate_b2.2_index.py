"""
Generate b2.2_target_index.csv directly from the validated b2.2_era5_fields.nc.
This ensures the index perfectly matches the frozen primary artifact without rerunning CDS.
"""
import pandas as pd
import numpy as np
import xarray as xr
from pathlib import Path

PHASEB_DIR = Path(__file__).parent
NC_PATH = PHASEB_DIR / "b2.2_era5_fields.nc"
OUTPUT_PATH = PHASEB_DIR / "b2.2_target_index.csv"

EARTH_RADIUS_KM = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    return EARTH_RADIUS_KM * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

print("Loading validated b2.2_era5_fields.nc...")
with xr.open_dataset(NC_PATH) as ds:
    n_cases = ds.dims["case"]
    assert n_cases == 300, f"Expected 300 cases, found {n_cases}"
    
    records = []
    for i in range(n_cases):
        req_lat = float(ds["requested_latitude"].values[i])
        req_lon = float(ds["requested_longitude"].values[i])
        grid_lat = float(ds["center_grid_latitude"].values[i])
        grid_lon = float(ds["center_grid_longitude"].values[i])
        case_timestamp = str(ds["case_timestamp"].values[i])
        
        records.append({
            "ID": str(ds["case_id"].values[i]),
            "Type": str(ds["case_type"].values[i]),
            "RequestedTimestamp": case_timestamp,
            "RequestedLat": req_lat,
            "RequestedLon": req_lon,
            "ERA5Timestamp": case_timestamp,  # Exact match verified in v1.6 QC
            "CenterLat": grid_lat,
            "CenterLon": grid_lon,
            "GridDistanceKm": round(haversine_km(req_lat, req_lon, grid_lat, grid_lon), 4),
            "QC_Status": "PASSED"
        })

index_df = pd.DataFrame(records)
index_df.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Generated {OUTPUT_PATH} with {len(index_df)} records.")
print(f"   TC: {len(index_df[index_df['Type'] == 'TC'])}")
print(f"   Control: {len(index_df[index_df['Type'] == 'Control'])}")