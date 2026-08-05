"""
TRACEBIND-Albatross: Retrieval Experiment — Step 1
===================================================
Build Descriptor Database from Phase 8 C2 Cohort

Purpose: Extract a rich set of descriptors from each of the 20 ERA5 cases
and save them to a structured database for downstream retrieval experiments.

This is an ENGINEERING VALIDATION step: does the pipeline work end-to-end?
No scientific claims. Just: can we extract descriptors reproducibly?

Descriptor Version: R1.0
"""

import sys
import json
import platform
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
import xarray as xr
from scipy.ndimage import gaussian_filter

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

# ============================================================================
# Configuration
# ============================================================================
DATA_DIR = Path(r"C:\TRACEBIND-Atmosphere\phase8\c2\raw")
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DESCRIPTOR_VERSION = "R1.0"
WINDOW_SIZE = 9  # For local Cφ field
OPERATOR_HASH = "02732f08923752fa274bb490311929b2fc88cfc3826ebe59caecb4bab881e5cd"

# Explicit descriptor column order (for PCA reproducibility)
DESCRIPTOR_COLUMNS = [
    "filename",
    "global_c_phi",
    "max_vorticity",
    "center_vorticity",  # NEW: vorticity at estimated center
    "max_wind_speed",
    "mean_wind_speed",
    "mean_local_c_phi",
    "std_local_c_phi",
    "min_local_c_phi",
    "max_local_c_phi",
    "p25_local_c_phi",
    "p75_local_c_phi",
    "median_center_distance"
]

# Diagnostic metadata (not used for retrieval)
METADATA_COLUMNS = [
    "center_x_km",
    "center_y_km",
    "n_valid_windows",
    "extraction_status",
    "failure_reason"
]

# ============================================================================
# Data Structure
# ============================================================================
@dataclass
class DescriptorRecord:
    """Typed descriptor record for type safety and clarity."""
    filename: str
    global_c_phi: float
    max_vorticity: float
    center_vorticity: float
    max_wind_speed: float
    mean_wind_speed: float
    mean_local_c_phi: float
    std_local_c_phi: float
    min_local_c_phi: float
    max_local_c_phi: float
    p25_local_c_phi: float
    p75_local_c_phi: float
    median_center_distance: float
    center_x_km: float
    center_y_km: float
    n_valid_windows: int
    extraction_status: str = "success"
    failure_reason: Optional[str] = None

# ============================================================================
# Corrected Vorticity Computation (coordinate-aware)
# ============================================================================
def compute_vorticity_corrected(u, v, x_1d, y_1d):
    """Robust vorticity using coordinate arrays (immune to ascending/descending grids)."""
    dvdx = np.gradient(v, x_1d, axis=1)
    dudy = np.gradient(u, y_1d, axis=0)
    return dvdx - dudy

def find_center_corrected(u, v, X, Y):
    """Find max vorticity center with smoothing."""
    u_smooth = gaussian_filter(u, sigma=0.8)
    v_smooth = gaussian_filter(v, sigma=0.8)
    x_1d = X[0, :]
    y_1d = Y[:, 0]
    zeta = compute_vorticity_corrected(u_smooth, v_smooth, x_1d, y_1d)
    idx = np.unravel_index(np.argmax(np.abs(zeta)), zeta.shape)
    return float(X[idx]), float(Y[idx]), float(np.abs(zeta[idx]))

# ============================================================================
# Descriptor Extraction
# ============================================================================
def extract_descriptors(filepath) -> DescriptorRecord:
    """Extract a rich set of descriptors from one ERA5 case."""
    try:
        ds = xr.open_dataset(filepath)
        u10 = ds['u10'].squeeze().values.astype('float64')
        v10 = ds['v10'].squeeze().values.astype('float64')
        lat = ds['latitude'].values.astype('float64')
        lon = ds['longitude'].values.astype('float64')
        ds.close()
    except Exception as e:
        return DescriptorRecord(
            filename=filepath.name,
            global_c_phi=np.nan,
            max_vorticity=np.nan,
            center_vorticity=np.nan,
            max_wind_speed=np.nan,
            mean_wind_speed=np.nan,
            mean_local_c_phi=np.nan,
            std_local_c_phi=np.nan,
            min_local_c_phi=np.nan,
            max_local_c_phi=np.nan,
            p25_local_c_phi=np.nan,
            p75_local_c_phi=np.nan,
            median_center_distance=np.nan,
            center_x_km=np.nan,
            center_y_km=np.nan,
            n_valid_windows=0,
            extraction_status="failed",
            failure_reason=str(e)
        )
    
    # Local Cartesian conversion
    lat_rad = np.radians(lat)
    dy = (lat - np.mean(lat)) * 111.0
    dx = (lon - np.mean(lon)) * 111.0 * np.cos(np.mean(lat_rad))
    X_km, Y_km = np.meshgrid(dx, dy)
    x_1d = X_km[0, :]
    y_1d = Y_km[:, 0]
    
    # --- Global Descriptors ---
    
    # 1. Vorticity field
    u_smooth = gaussian_filter(u10, sigma=0.8)
    v_smooth = gaussian_filter(v10, sigma=0.8)
    zeta = compute_vorticity_corrected(u_smooth, v_smooth, x_1d, y_1d)
    max_vort = float(np.max(np.abs(zeta)))
    
    # 2. Global Cφ and center
    cor_cx, cor_cy, center_vort = find_center_corrected(u10, v10, X_km, Y_km)
    global_c_phi = compute_phase_coherence(u10, v10, X=X_km, Y=Y_km, center=(cor_cx, cor_cy))
    
    # 3. Wind speed statistics
    wind_speed = np.sqrt(u10**2 + v10**2)
    max_wind_speed = float(np.max(wind_speed))
    mean_wind_speed = float(np.mean(wind_speed))
    
    # --- Local Descriptors (via sliding window) ---
    half_w = WINDOW_SIZE // 2
    ny, nx = u10.shape
    window_data = []
    
    for i in range(half_w, ny - half_w):
        for j in range(half_w, nx - half_w):
            u_win = u10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            v_win = v10[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            x_win = X_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            y_win = Y_km[i-half_w:i+half_w+1, j-half_w:j+half_w+1]
            
            # Local Cφ (referenced to window midpoint)
            c_phi = compute_phase_coherence(u_win, v_win, X=x_win, Y=y_win, center=None)
            
            # Local max vorticity for filtering
            u_w_smooth = gaussian_filter(u_win, sigma=0.8)
            v_w_smooth = gaussian_filter(v_win, sigma=0.8)
            zeta_w = compute_vorticity_corrected(u_w_smooth, v_w_smooth, x_win[0,:], y_win[:,0])
            max_zeta = float(np.max(np.abs(zeta_w)))
            
            # Distance to global center
            loc_i, loc_j = np.unravel_index(np.argmax(np.abs(zeta_w)), zeta_w.shape)
            abs_i = (i - half_w) + loc_i
            abs_j = (j - half_w) + loc_j
            dist = np.sqrt((X_km[abs_i, abs_j] - cor_cx)**2 + (Y_km[abs_i, abs_j] - cor_cy)**2)
            
            window_data.append({
                "c_phi": c_phi,
                "max_zeta": max_zeta,
                "dist": dist
            })
    
    # Filter: Keep strongest 80% of windows by vorticity
    window_data.sort(key=lambda w: w["max_zeta"], reverse=True)
    n_keep = int(len(window_data) * 0.80)
    valid_windows = window_data[:n_keep]
    
    local_c_phis = [w["c_phi"] for w in valid_windows]
    distances = [w["dist"] for w in valid_windows]
    
    # Local Cφ statistics
    mean_local_c_phi = float(np.mean(local_c_phis))
    std_local_c_phi = float(np.std(local_c_phis))
    min_local_c_phi = float(np.min(local_c_phis))
    max_local_c_phi = float(np.max(local_c_phis))
    p25_local_c_phi = float(np.percentile(local_c_phis, 25))
    p75_local_c_phi = float(np.percentile(local_c_phis, 75))
    
    # Median center distance
    median_center_distance = float(np.median(distances))
    
    # --- Compile descriptor record ---
    return DescriptorRecord(
        filename=filepath.name,
        global_c_phi=global_c_phi,
        max_vorticity=max_vort,
        center_vorticity=center_vort,
        max_wind_speed=max_wind_speed,
        mean_wind_speed=mean_wind_speed,
        mean_local_c_phi=mean_local_c_phi,
        std_local_c_phi=std_local_c_phi,
        min_local_c_phi=min_local_c_phi,
        max_local_c_phi=max_local_c_phi,
        p25_local_c_phi=p25_local_c_phi,
        p75_local_c_phi=p75_local_c_phi,
        median_center_distance=median_center_distance,
        center_x_km=cor_cx,
        center_y_km=cor_cy,
        n_valid_windows=len(valid_windows)
    )

# ============================================================================
# Main Execution
# ============================================================================
def build_descriptor_database():
    print("=" * 85)
    print("RETRIEVAL EXPERIMENT: Step 1 — Build Descriptor Database")
    print(f"Descriptor Version: {DESCRIPTOR_VERSION}")
    print("=" * 85)
    print("Extracting descriptors from 20-case Phase 8 C2 cohort...\n")
    
    nc_files = sorted(DATA_DIR.glob("*.nc"))
    print(f"Found {len(nc_files)} files.\n")
    
    records = []
    for i, filepath in enumerate(nc_files, 1):
        print(f"[{i}/{len(nc_files)}] {filepath.name}...", end=" ")
        record = extract_descriptors(filepath)
        records.append(record)
        
        if record.extraction_status == "success":
            print(f"OK (Global Cφ={record.global_c_phi:.4f})")
        else:
            print(f"FAILED ({record.failure_reason})")
    
    # Convert to DataFrame with explicit column order
    df = pd.DataFrame([asdict(r) for r in records])[DESCRIPTOR_COLUMNS + METADATA_COLUMNS]
    
    # Save to CSV (feature table)
    csv_path = OUTPUT_DIR / "descriptor_database.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✅ Descriptor database saved to {csv_path}")
    
    # Save to JSON (full provenance)
    environment_info = {
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "xarray_version": xr.__version__,
        "scipy_version": __import__('scipy').__version__,
        "pandas_version": pd.__version__
    }
    
    report = {
        "experiment": "retrieval_step1",
        "descriptor_version": DESCRIPTOR_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_cases": len(records),
        "n_successful": sum(1 for r in records if r.extraction_status == "success"),
        "n_failed": sum(1 for r in records if r.extraction_status == "failed"),
        "window_size": WINDOW_SIZE,
        "operator_hash": OPERATOR_HASH,
        "environment": environment_info,
        "descriptor_columns": DESCRIPTOR_COLUMNS,
        "metadata_columns": METADATA_COLUMNS,
        "descriptors": [asdict(r) for r in records]
    }
    
    json_path = OUTPUT_DIR / "descriptor_database.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"✅ Provenance report saved to {json_path}")
    
    # Summary statistics (only successful extractions)
    successful_df = df[df["extraction_status"] == "success"]
    if len(successful_df) > 0:
        print("\n" + "=" * 85)
        print("SUMMARY STATISTICS (Successful Extractions Only)")
        print("=" * 85)
        print(successful_df[DESCRIPTOR_COLUMNS[1:7]].describe().round(4))
        print("=" * 85)
    
    # Report any failures
    failed_records = [r for r in records if r.extraction_status == "failed"]
    if failed_records:
        print(f"\n⚠️  {len(failed_records)} extraction(s) failed:")
        for r in failed_records:
            print(f"  - {r.filename}: {r.failure_reason}")

if __name__ == "__main__":
    build_descriptor_database()