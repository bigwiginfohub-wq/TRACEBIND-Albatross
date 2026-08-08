"""
TRACEBIND Phase B2.1: Final Provenance and Field-Level Audit
=============================================================

Purpose:
1. Verify v4.1 and v5.1 contain exactly the same scientific records,
   independent of ControlID and row ordering.
2. Verify every non-ControlID field for Selected and Standby records.
3. Verify ControlID uniqueness in v5.1.
4. Cryptographically verify that the SHA256 recorded in control_audit.json
   matches b2.1_select_controls_v5.1.py currently on disk.
5. Verify the audit manifest's recorded source hashes and candidate count
   are internally present.

READ-ONLY:
This script does not modify any Phase B2.1 artifact.
"""

import pandas as pd
import json
import hashlib
from pathlib import Path
import sys

PHASEB_DIR = Path(__file__).parent

V4_FILE = PHASEB_DIR / "selected_control_ids_v4.1.csv"
V5_FILE = PHASEB_DIR / "selected_control_ids.csv"
SCRIPT_FILE = PHASEB_DIR / "b2.1_select_controls_v5.1.py"
AUDIT_FILE = PHASEB_DIR / "control_audit.json"

EXPECTED_SELECTED = 150
EXPECTED_STANDBY = 1200

print("=" * 75)
print("TRACEBIND B2.1: FINAL PROVENANCE & FIELD-LEVEL AUDIT")
print("=" * 75)

# ============================================================================
# Helper
# ============================================================================

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_records(df, status):
    """
    Return records in deterministic order using every field except ControlID.
    This makes comparison independent of CSV row ordering.
    """
    x = df[df["Status"] == status].drop(columns=["ControlID"]).copy()

    # Convert values to stable strings for comparison.
    for col in x.columns:
        x[col] = x[col].astype(str)

    return x.sort_values(
        by=list(x.columns),
        kind="mergesort"
    ).reset_index(drop=True)


# ============================================================================
# Load artifacts
# ============================================================================

print("\nLoading frozen artifacts...")

required_files = [V4_FILE, V5_FILE, SCRIPT_FILE, AUDIT_FILE]

for path in required_files:
    if not path.exists():
        print(f"❌ MISSING REQUIRED FILE: {path}")
        sys.exit(1)

v4 = pd.read_csv(V4_FILE)
v5 = pd.read_csv(V5_FILE)

with open(AUDIT_FILE, "r", encoding="utf-8") as f:
    audit = json.load(f)

# ============================================================================
# 1. Basic structural checks
# ============================================================================

print("\n[1] BASIC STRUCTURAL INTEGRITY")
print("-" * 45)

v4_selected = v4[v4["Status"] == "Selected"]
v5_selected = v5[v5["Status"] == "Selected"]

v4_standby = v4[v4["Status"] == "Standby"]
v5_standby = v5[v5["Status"] == "Standby"]

print(f"v4.1 Selected: {len(v4_selected)}")
print(f"v5.1 Selected: {len(v5_selected)}")
print(f"v4.1 Standby:  {len(v4_standby)}")
print(f"v5.1 Standby:  {len(v5_standby)}")

failures = []

if len(v4_selected) != EXPECTED_SELECTED:
    failures.append("v4.1 selected count")
if len(v5_selected) != EXPECTED_SELECTED:
    failures.append("v5.1 selected count")
if len(v4_standby) != EXPECTED_STANDBY:
    failures.append("v4.1 standby count")
if len(v5_standby) != EXPECTED_STANDBY:
    failures.append("v5.1 standby count")

if not failures:
    print("✅ Selected/standby counts exactly match expected values.")
else:
    print("❌ Count failure:", failures)

# ============================================================================
# 2. Field-level comparison
# ============================================================================

print("\n[2] FIELD-LEVEL SCIENTIFIC COMPARISON")
print("-" * 45)

if "ControlID" not in v4.columns or "ControlID" not in v5.columns:
    print("❌ ControlID column missing.")
    sys.exit(1)

scientific_columns = [
    "Basin",
    "Month",
    "LMC",
    "Timestamp",
    "Latitude",
    "Longitude",
    "RandomRank",
    "StratumID",
    "Status",
]

missing_v4 = [c for c in scientific_columns if c not in v4.columns]
missing_v5 = [c for c in scientific_columns if c not in v5.columns]

if missing_v4 or missing_v5:
    print(f"❌ Missing columns.")
    print(f"   v4.1: {missing_v4}")
    print(f"   v5.1: {missing_v5}")
    sys.exit(1)

all_fields_match = True

for status in ["Selected", "Standby"]:
    a = canonical_records(v4, status)
    b = canonical_records(v5, status)

    if a.equals(b):
        print(f"✅ {status}: EXACT MATCH across all non-ControlID fields.")
    else:
        print(f"❌ {status}: MISMATCH DETECTED.")
        all_fields_match = False

        # Identify differing rows where possible.
        merged = a.merge(
            b,
            how="outer",
            indicator=True
        )

        only_v4 = merged[merged["_merge"] == "left_only"]
        only_v5 = merged[merged["_merge"] == "right_only"]

        print(f"   Records only in v4.1: {len(only_v4)}")
        print(f"   Records only in v5.1: {len(only_v5)}")

# ============================================================================
# 3. ControlID integrity
# ============================================================================

print("\n[3] CONTROLID INTEGRITY")
print("-" * 45)

selected_ids = v5_selected["ControlID"]

duplicate_ids = selected_ids[selected_ids.duplicated()]

print(f"v5.1 Selected ControlIDs: {len(selected_ids)}")
print(f"v5.1 Duplicate ControlIDs: {len(duplicate_ids)}")

if len(duplicate_ids) == 0:
    print("✅ v5.1 ControlIDs are globally unique among selected controls.")
else:
    print("❌ v5.1 contains duplicate selected ControlIDs.")
    failures.append("v5.1 ControlID uniqueness")

# ============================================================================
# 4. Physical uniqueness
# ============================================================================

print("\n[4] PHYSICAL UNIQUENESS")
print("-" * 45)

physical_columns = ["Timestamp", "Latitude", "Longitude"]

duplicates_v5 = v5_selected[
    v5_selected.duplicated(subset=physical_columns, keep=False)
]

print(f"v5.1 duplicate physical records: {len(duplicates_v5)}")

if len(duplicates_v5) == 0:
    print("✅ All 150 selected controls have unique physical locations/timestamps.")
else:
    print("❌ Duplicate physical records detected.")
    failures.append("physical uniqueness")

# ============================================================================
# 5. Basin balance
# ============================================================================

print("\n[5] BASIN BALANCE")
print("-" * 45)

v5_basin_counts = v5_selected["Basin"].value_counts().to_dict()

print(f"v5.1 basin counts: {v5_basin_counts}")

if v5_basin_counts == {"NI": 50, "SI": 50, "WP": 50}:
    print("✅ Exact 50/50/50 basin balance.")
else:
    print("❌ Basin balance mismatch.")
    failures.append("basin balance")

# ============================================================================
# 6. Cryptographic provenance
# ============================================================================

print("\n[6] CRYPTOGRAPHIC PROVENANCE")
print("-" * 45)

disk_script_hash = sha256_file(SCRIPT_FILE)

manifest_script_hash = audit["freeze_fingerprint"]["script_sha256"]

print(f"Script on disk:  {disk_script_hash}")
print(f"Manifest script: {manifest_script_hash}")

if disk_script_hash == manifest_script_hash:
    print("✅ Script SHA256 matches audit manifest.")
else:
    print("❌ SCRIPT PROVENANCE FAILURE.")
    failures.append("script SHA256")

# ============================================================================
# 7. Manifest consistency
# ============================================================================

print("\n[7] AUDIT MANIFEST CONSISTENCY")
print("-" * 45)

candidate_rows = audit["candidate_pool"]["row_count"]
selected_manifest = audit["summary_statistics"]["total_selected_controls"]
standby_manifest = audit["summary_statistics"]["total_standby_controls"]

print(f"Manifest candidate rows: {candidate_rows:,}")
print(f"Manifest selected:       {selected_manifest}")
print(f"Manifest standby:        {standby_manifest}")

if selected_manifest == EXPECTED_SELECTED:
    print("✅ Manifest selected count = 150.")
else:
    print("❌ Manifest selected count mismatch.")
    failures.append("manifest selected count")

if standby_manifest == EXPECTED_STANDBY:
    print("✅ Manifest standby count = 1200.")
else:
    print("❌ Manifest standby count mismatch.")
    failures.append("manifest standby count")

# ============================================================================
# 8. Source-data provenance
# ============================================================================

print("\n[8] SOURCE-DATA PROVENANCE")
print("-" * 45)

source_hashes = audit["data_source_hashes"]

print(f"IBTrACS SHA256: {source_hashes['ibtracs_sha256']}")
print(f"ERA5 LSM SHA256: {source_hashes['era5_lsm_sha256']}")

print("✅ Source hashes successfully recovered from frozen audit manifest.")

# ============================================================================
# 9. FINAL CONCLUSION
# ============================================================================

print("\n" + "=" * 75)
print("FINAL AUDIT CONCLUSION")
print("=" * 75)

if all_fields_match and not failures:
    print("✅ FINAL AUDIT PASSED")
    print()
    print("v4.1 and v5.1 contain exactly the same Selected and Standby")
    print("scientific records across all non-ControlID fields, independent")
    print("of CSV row ordering.")
    print()
    print("v5.1 additionally provides globally unique ControlIDs.")
    print()
    print("The v5.1 sampler script SHA256 exactly matches the hash recorded")
    print("in control_audit.json.")
    print()
    print("Phase B2.1 v5.1 is READY FOR GIT FREEZE.")
else:
    print("❌ FINAL AUDIT FAILED")
    print()
    print("Failures detected:")
    for failure in failures:
        print(f"  - {failure}")
    print()
    print("DO NOT Git-freeze Phase B2.1 until the failures are resolved.")

print("=" * 75)