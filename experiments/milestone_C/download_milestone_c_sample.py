"""
TRACEBIND-Albatross: Download Targeted ERA5 Sample for Milestone C
==================================================================
Purpose: Download a single, real-world ERA5 case that includes both
         10m winds AND mean sea level pressure (msl) for H2 correlation testing.
         
Target: Based on c2_uuid_49511e7b.nc
Date: 2023-05-15 12:00:00 UTC
Domain: Lat 13.75 to 23.50, Lon 80.00 to 90.00 (Bay of Bengal / Cyclone Mocha region)
"""

import cdsapi
import os
from pathlib import Path

# Output directory
output_dir = Path(r"C:\TRACEBIND-Albatross\data\raw")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "milestone_c_sample_mocha_20230515.nc"

print("=" * 70)
print("DOWNLOADING TARGETED ERA5 SAMPLE FOR MILESTONE C")
print("=" * 70)
print(f"Target File: {output_file.name}")
print("Variables: 10m U wind, 10m V wind, Mean Sea Level Pressure")
print("Date: 2023-05-15, Time: 12:00")
print("Area: [North=23.5, West=80.0, South=13.75, East=90.0]")
print("=" * 70)

if output_file.exists():
    print("\n✅ File already exists. Skipping download.")
else:
    print("\n⏳ Contacting CDS API... (This may take 1-2 minutes)")
    try:
        c = cdsapi.Client()
        c.retrieve(
            'reanalysis-era5-single-levels',
            {
                'product_type': 'reanalysis',
                'format': 'netcdf',
                'variable': [
                    '10m_u_component_of_wind',
                    '10m_v_component_of_wind',
                    'mean_sea_level_pressure',
                ],
                'year': '2023',
                'month': '05',
                'day': '15',
                'time': '12:00',
                'area': [23.5, 80.0, 13.75, 90.0],  # [North, West, South, East]
            },
            str(output_file)
        )
        print(f"\n✅ SUCCESS: Saved to {output_file}")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        print("Please ensure your CDS API key is correctly configured in ~/.cdsapirc")

print("=" * 70)