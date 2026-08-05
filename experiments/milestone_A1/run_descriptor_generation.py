"""
TRACEBIND-Albatross: Milestone A1 - Descriptor Generation
=========================================================
Purpose: Apply the frozen TRACEBIND operator to validated ERA5 data 
         and generate an auditable descriptor field report.
"""

import sys
import json
import numpy as np
import xarray as xr
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.preprocessing.era5_loader import load_era5_wind_field
from src.tracebind.frozen_operators import compute_phase_coherence

def create_synthetic_era5_file(filepath: str):
    """Creates a minimal, valid NetCDF file mimicking ERA5 pressure-level output."""
    lats = np.linspace(45.0, 46.0, 50)  # Larger grid for better resolution
    lons = np.linspace(10.0, 11.0, 50)
    
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    xc, yc = lon_grid.mean(), lat_grid.mean()
    R = np.sqrt((lon_grid - xc)**2 + (lat_grid - yc)**2) + 1e-12
    
    # Synthetic pure rotation field
    u_data = -15.0 * (lat_grid - yc) / R
    v_data = 15.0 * (lon_grid - xc) / R

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

def run_a1_descriptor_generation():
    print("="*60)
    print("MILESTONE A1: DESCRIPTOR GENERATION")
    print("="*60)
    
    temp_file = "temp_synthetic_era5_a1.nc"
    print("\n[1/4] Generating synthetic ERA5 NetCDF file (Pure Rotation)...")
    create_synthetic_era5_file(temp_file)
    
    print("[2/4] Loading validated data via era5_loader...")
    try:
        data = load_era5_wind_field(temp_file, u_var="u", v_var="v")
        print(f"✓ PASS: Loaded shape {data['provenance']['shape']}")
    except Exception as e:
        print(f"❌ FAIL: Loader raised exception: {e}")
        return False

    print("[3/4] Applying FROZEN compute_phase_coherence operator...")
    u = data["u"]
    v = data["v"]
    
    # CRITICAL: Explicitly mesh the 1D physical coordinates into 2D grids
    # This prevents the frozen operator from falling back to index-based coordinates
    X_phys, Y_phys = np.meshgrid(data["x_1d"], data["y_1d"])
    
    try:
        c_phi_result = compute_phase_coherence(
            u=u,
            v=v,
            X=X_phys,
            Y=Y_phys,
            center=None # Let it default to geometric midpoint
        )
        print(f"✓ PASS: Operator executed successfully.")
        print(f"         Resulting C_phi = {c_phi_result:.6f}")
    except Exception as e:
        print(f"❌ FAIL: Frozen operator raised exception: {e}")
        return False

    print("[4/4] Generating auditable provenance report...")
    
    # Validate the result against the known synthetic ground truth
    validation_status = "PASS" if c_phi_result > 0.99 else "FAIL"
    
    report = {
        "milestone": "A1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_provenance": data["provenance"],
        "operator": "compute_phase_coherence (Phase 7 v1.0 Frozen)",
        "configuration": {
            "center": "auto_midpoint",
            "mask": "none",
            "coordinate_type": "explicit_physical_meshgrid"
        },
        "result": {
            "c_phi": c_phi_result,
            "validation_status": validation_status,
            "expected_minimum": 0.99
        }
    }
    
    report_path = Path("experiments/milestone_A1/a1_descriptor_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ PASS: Report saved to {report_path}")

    # Cleanup
    Path(temp_file).unlink()
    
    print("\n" + "="*60)
    if validation_status == "PASS":
        print("✅ MILESTONE A1 VALIDATION SUCCESSFUL")
        print("The frozen operator correctly processes validated loader output.")
        print("Proceed to Milestone A2 (Descriptor Characterization).")
    else:
        print("❌ MILESTONE A1 VALIDATION FAILED")
        print("The frozen operator did not yield expected results on synthetic data.")
        print("Review coordinate mapping and operator implementation.")
    print("="*60)
    
    return validation_status == "PASS"

if __name__ == "__main__":
    success = run_a1_descriptor_generation()
    if not success:
        sys.exit(1)