"""
TRACEBIND-Albatross: Milestone A0 - Data Instrument Validation
==============================================================
Purpose: Verify that the ERA5 loader correctly ingests data, maps coordinates, 
         and captures provenance without embedding physics validation in the loader itself.
"""

import sys
import numpy as np
import xarray as xr
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.preprocessing.era5_loader import load_era5_wind_field

def create_synthetic_era5_file(filepath: str):
    """Creates a minimal, valid NetCDF file mimicking ERA5 pressure-level output."""
    # 10x10 grid, local Cartesian approximation valid here
    lats = np.linspace(45.0, 46.0, 10)  # Descending or ascending, xarray handles it
    lons = np.linspace(10.0, 11.0, 10)
    
    # Synthetic pure rotation field for testing
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    xc, yc = lon_grid.mean(), lat_grid.mean()
    R = np.sqrt((lon_grid - xc)**2 + (lat_grid - yc)**2) + 1e-12
    
    u_data = -10.0 * (lat_grid - yc) / R
    v_data = 10.0 * (lon_grid - xc) / R

    ds = xr.Dataset(
        data_vars={
            "u": (["latitude", "longitude"], u_data, {"units": "m s**-1"}),
            "v": (["latitude", "longitude"], v_data, {"units": "m s**-1"}),
        },
        coords={
            "latitude": lats,
            "longitude": lons,
        }
    )
    ds.to_netcdf(filepath)
    return filepath

def run_a0_validation():
    print("="*60)
    print("MILESTONE A0: DATA INSTRUMENT VALIDATION")
    print("="*60)
    
    temp_file = "temp_synthetic_era5.nc"
    print("\n[1/4] Generating synthetic ERA5 NetCDF file...")
    create_synthetic_era5_file(temp_file)
    
    print("[2/4] Loading data via era5_loader...")
    try:
        data = load_era5_wind_field(temp_file, u_var="u", v_var="v")
        print("✓ PASS: Loader successfully ingested file.")
    except Exception as e:
        print(f"❌ FAIL: Loader raised exception: {e}")
        return False

    print("[3/4] Verifying provenance capture...")
    prov = data["provenance"]
    if "sha256" not in prov or len(prov["sha256"]) != 64:
        print("❌ FAIL: SHA-256 provenance missing or malformed.")
        return False
    print(f"✓ PASS: Provenance captured (SHA-256: {prov['sha256'][:16]}...)")
    print(f"         Variables: u='{prov['u_var']}', v='{prov['v_var']}'")
    print(f"         Shape: {prov['shape']}")

    print("[4/4] Running synthetic operator characterization (Pure Rotation)...")
    # We simulate the frozen operator's logic here to validate the coordinate mapping
    u = data["u"]
    v = data["v"]
    x = data["x_1d"]
    y = data["y_1d"]
    
    nx, ny = u.shape
    X, Y = np.meshgrid(x, y)
    xc, yc = X.mean(), Y.mean()
    Xc = X - xc
    Yc = Y - yc
    R = np.sqrt(Xc**2 + Yc**2) + 1e-12
    
    e_theta_x = -Yc / R
    e_theta_y = Xc / R
    speed = np.sqrt(u**2 + v**2) + 1e-12
    
    dot_tangential = (u * e_theta_x + v * e_theta_y) / speed
    c_phi = float(np.mean(np.abs(dot_tangential)))
    
    # For pure rotation, C_phi should be ~1.0
    if c_phi < 0.99:
        print(f"❌ FAIL: Pure rotation yielded low C_phi ({c_phi:.4f}). Coordinate mapping is flawed.")
        return False
    print(f"✓ PASS: Pure rotation test (C_phi = {c_phi:.4f}, expected > 0.99)")

    # Cleanup
    Path(temp_file).unlink()
    
    print("\n" + "="*60)
    print("✅ MILESTONE A0 VALIDATION SUCCESSFUL")
    print("The data instrument is trusted. Proceed to Milestone A1.")
    print("="*60)
    return True

if __name__ == "__main__":
    success = run_a0_validation()
    if not success:
        sys.exit(1)