"""
TRACEBIND-Albatross: ERA5 Data Loader
======================================
Validation Status: [ ] Untested  [ ] Characterized  [ ] Frozen  [ ] Published

Purpose: Load ERA5 NetCDF/GRIB data and extract wind components and physical coordinates.
Design Principle: Single responsibility. Read data correctly. Do not validate physics or 
                  run synthetic algorithm tests here.

CRITICAL ASSUMPTION: Local Cartesian Approximation
--------------------------------------------------
This loader extracts 1D latitude and longitude arrays and treats them as physical Y and X 
coordinates, respectively. This is a valid *local Cartesian approximation* ONLY for bounded, 
regional domains where the curvature of the Earth and the convergence of meridians are 
negligible relative to the domain size. 

For global datasets or very large domains, a proper map projection (e.g., Lambert Conformal) 
must be applied before passing coordinates to the frozen TRACEBIND operator.
"""

import hashlib
import xarray as xr
from pathlib import Path
from typing import Dict, Any

def compute_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of the raw data file for provenance."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()

def load_era5_wind_field(
    filepath: str, 
    u_var: str = "u", 
    v_var: str = "v",
    lat_var: str = "latitude",
    lon_var: str = "longitude"
) -> Dict[str, Any]:
    """
    Loads an ERA5 dataset and extracts wind components and 1D coordinate arrays.
    
    Parameters:
    -----------
    filepath : str
        Path to the NetCDF or GRIB file.
    u_var, v_var : str
        Variable names for zonal and meridional wind. Defaults to "u", "v" (pressure levels).
        Use "u10", "v10" for surface products.
    lat_var, lon_var : str
        Coordinate variable names. Defaults to "latitude", "longitude".
        
    Returns:
    --------
    dict : Contains 'u', 'v', 'x_1d', 'y_1d', and 'provenance' metadata.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    file_sha256 = compute_file_sha256(path)

    # Lazy load with xarray
    ds = xr.open_dataset(path)

    if u_var not in ds or v_var not in ds:
        available_vars = list(ds.data_vars)
        raise ValueError(f"Required variables '{u_var}' and '{v_var}' not found in {path.name}. Available: {available_vars}")
    
    if lat_var not in ds.coords and lat_var not in ds.data_vars:
        available_coords = list(ds.coords)
        raise ValueError(f"Coordinate '{lat_var}' not found. Available: {available_coords}")
        
    if lon_var not in ds.coords and lon_var not in ds.data_vars:
        available_coords = list(ds.coords)
        raise ValueError(f"Coordinate '{lon_var}' not found. Available: {available_coords}")

    # Extract data to numpy arrays for compatibility with the frozen operator
    # (In production, we might keep these as xarray.DataArray for lazy evaluation)
    u = ds[u_var].values.astype("float64")
    v = ds[v_var].values.astype("float64")
    
    lats_1d = ds[lat_var].values.astype("float64")
    lons_1d = ds[lon_var].values.astype("float64")

    # Capture provenance
    provenance = {
        "filename": path.name,
        "sha256": file_sha256,
        "shape": u.shape,
        "u_var": u_var,
        "v_var": v_var,
        "lat_var": lat_var,
        "lon_var": lon_var,
        "lat_is_descending": bool(lats_1d[0] > lats_1d[-1]),
        "xarray_attrs": {
            "u_units": ds[u_var].attrs.get("units", "unknown"),
            "v_units": ds[v_var].attrs.get("units", "unknown"),
        }
    }

    ds.close()

    return {
        "u": u,
        "v": v,
        "x_1d": lons_1d,
        "y_1d": lats_1d,
        "provenance": provenance
    }