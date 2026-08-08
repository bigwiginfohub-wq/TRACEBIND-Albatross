"""
TRACEBIND B3: Final Non-Grouped Integrity Verification
=======================================================
Verifies the cryptographic and structural integrity of the B3 output
WITHOUT performing any TC/Control statistical comparisons.
"""
import pandas as pd
import numpy as np
import xarray as xr
import json
import hashlib
from pathlib import Path

PHASEB_DIR = Path(__file__).parent
NC_PATH = PHASEB_DIR / "b2.2_era5_fields.nc"
CSV_PATH = PHASEB_DIR / "b3_descriptors.csv"
AUDIT_PATH = PHASEB_DIR / "b3_audit.json"

def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

print("=" * 75)
print("TRACEBIND B3: FINAL NON-GROUPED INTEGRITY VERIFICATION")
print("=" * 75)

all_pass = True

# 1. Verify SHA256 Hashes
print("\n[1] CRYPTOGRAPHIC HASH VERIFICATION")
print("-" * 50)
with open(AUDIT_PATH, 'r') as f:
    audit = json.load(f)

nc_hash = compute_sha256(NC_PATH)
csv_hash = compute_sha256(CSV_PATH)

if nc_hash == audit["input_artifact_sha256"]:
    print(f"  ✅ B2.2 NetCDF SHA256 matches audit")
else:
    print(f"  ❌ B2.2 NetCDF SHA256 MISMATCH")
    all_pass = False

if csv_hash == audit["output_sha256"]:
    print(f"  ✅ B3 CSV SHA256 matches audit")
else:
    print(f"  ❌ B3 CSV SHA256 MISMATCH")
    all_pass = False

# 2. Verify Ordering and Uniqueness
print("\n[2] ORDERING & UNIQUENESS VERIFICATION")
print("-" * 50)
df = pd.read_csv(CSV_PATH)

with xr.open_dataset(NC_PATH) as ds:
    nc_ids = ds["case_id"].values.astype(str)

csv_ids = df["case_id"].astype(str).to_numpy()

if np.array_equal(csv_ids, nc_ids):
    print(f"  ✅ CSV case ordering exactly matches NetCDF")
else:
    print(f"  ❌ CSV case ordering MISMATCH")
    all_pass = False

if df["case_id"].is_unique:
    print(f"  ✅ All 300 case IDs are unique")
else:
    print(f"  ❌ Duplicate case IDs found")
    all_pass = False

# 3. Verify Descriptor Bounds and QC
print("\n[3] DESCRIPTOR BOUNDS & QC VERIFICATION")
print("-" * 50)

# Check finite and bounds
finite_check = np.isfinite(df["C_phi"]).all()
bounds_check = ((df["C_phi"] >= 0.0) & (df["C_phi"] <= 1.0)).all()
shell_check = (df["shell_grid_count"] > 0).all()
qc_check = (df["QC_Status"] == "PASSED").all()

if finite_check:
    print(f"  ✅ All C_phi values are finite")
else:
    print(f"  ❌ Non-finite C_phi values found")
    all_pass = False

if bounds_check:
    print(f"  ✅ All C_phi values strictly within [0, 1]")
else:
    print(f"  ❌ C_phi values out of [0, 1] bounds")
    all_pass = False

if shell_check:
    print(f"  ✅ All shell_grid_counts > 0")
else:
    print(f"  ❌ Zero or negative shell counts found")
    all_pass = False

if qc_check:
    print(f"  ✅ All 300 cases have QC_Status = 'PASSED'")
else:
    print(f"  ❌ Some cases failed QC")
    all_pass = False

# 4. Audit Internal Consistency
print("\n[4] AUDIT INTERNAL CONSISTENCY")
print("-" * 50)
if audit["summary_statistics"]["total_cases"] == 300:
    print(f"  ✅ total_cases = 300")
else:
    print(f"  ❌ total_cases mismatch")
    all_pass = False

if audit["summary_statistics"]["passed"] == 300 and audit["summary_statistics"]["failed"] == 0:
    print(f"  ✅ passed = 300, failed = 0")
else:
    print(f"  ❌ pass/fail counts mismatch")
    all_pass = False

print("\n" + "=" * 75)
if all_pass:
    print("✅ B3 INTEGRITY FULLY VERIFIED. READY FOR GIT FREEZE.")
    print("   No TC/Control statistical comparisons were performed.")
else:
    print("❌ B3 INTEGRITY CHECK FAILED. Review above.")
print("=" * 75)