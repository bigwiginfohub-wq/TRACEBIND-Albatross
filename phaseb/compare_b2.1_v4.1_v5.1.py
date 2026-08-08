"""
TRACEBIND Phase B2.1: Read-Only Post-Freeze Comparison (v4.1 vs v5.1)
======================================================================
Purpose: Scientifically assess the impact of the v5.1 bugfixes 
(cross-year boundaries, searchsorted fix, global IDs) by comparing 
against the preserved v4.1 baseline.
"""

import pandas as pd
import json
from pathlib import Path

PHASEB_DIR = Path(__file__).parent

# ============================================================================
# 1. Load Data
# ============================================================================
print("Loading frozen artifacts...")
v4_sel = pd.read_csv(PHASEB_DIR / "selected_control_ids_v4.1.csv")
v5_sel = pd.read_csv(PHASEB_DIR / "selected_control_ids.csv")

with open(PHASEB_DIR / "control_audit_v4.1.json", 'r') as f:
    v4_audit = json.load(f)
with open(PHASEB_DIR / "control_audit.json", 'r') as f:
    v5_audit = json.load(f)

# Filter for Selected and Standby
v4_selected = v4_sel[v4_sel["Status"] == "Selected"].copy()
v5_selected = v5_sel[v5_sel["Status"] == "Selected"].copy()
v4_standby = v4_sel[v4_sel["Status"] == "Standby"].copy()
v5_standby = v5_sel[v5_sel["Status"] == "Standby"].copy()

# Create robust physical identifiers (Timestamp_Lat_Lon)
def make_phys_id(df):
    return df["Timestamp"] + "_" + df["Latitude"].astype(str) + "_" + df["Longitude"].astype(str)

v4_selected["phys_id"] = make_phys_id(v4_selected)
v5_selected["phys_id"] = make_phys_id(v5_selected)
v4_standby["phys_id"] = make_phys_id(v4_standby)
v5_standby["phys_id"] = make_phys_id(v5_standby)

# ============================================================================
# 2. Internal Integrity Checks
# ============================================================================
print("\n" + "=" * 70)
print("TRACEBIND B2.1: v4.1 vs v5.1 SCIENTIFIC COMPARISON REPORT")
print("=" * 70)

print("\n[1] INTERNAL INTEGRITY")
print("-" * 40)
print(f"v4.1 Selected Count: {len(v4_selected)} (Expected: 150)")
print(f"v5.1 Selected Count: {len(v5_selected)} (Expected: 150)")
print(f"v4.1 Standby Count:  {len(v4_standby)} (Expected: 1200)")
print(f"v5.1 Standby Count:  {len(v5_standby)} (Expected: 1200)")

print(f"\nv4.1 Basin Balance: {v4_selected['Basin'].value_counts().to_dict()}")
print(f"v5.1 Basin Balance: {v5_selected['Basin'].value_counts().to_dict()}")

v4_dup_phys = v4_selected["phys_id"].duplicated().sum()
v5_dup_phys = v5_selected["phys_id"].duplicated().sum()
v4_dup_id = v4_selected["ControlID"].duplicated().sum()
v5_dup_id = v5_selected["ControlID"].duplicated().sum()

print(f"\nv4.1 Physical Duplicates (Selected): {v4_dup_phys}")
print(f"v5.1 Physical Duplicates (Selected): {v5_dup_phys}")
print(f"v4.1 Duplicate ControlIDs (Selected): {v4_dup_id}")
print(f"v5.1 Duplicate ControlIDs (Selected): {v5_dup_id}")

# ============================================================================
# 3. Scientific Overlap Analysis
# ============================================================================
print("\n[2] SCIENTIFIC OVERLAP (SELECTED CONTROLS)")
print("-" * 40)

v4_phys_set = set(v4_selected["phys_id"])
v5_phys_set = set(v5_selected["phys_id"])

overlap = v4_phys_set.intersection(v5_phys_set)
removed = v4_phys_set - v5_phys_set
added = v5_phys_set - v4_phys_set

print(f"Exact Physical Overlap: {len(overlap)} / 150")
print(f"Removed from v4.1 (not in v5.1): {len(removed)}")
print(f"Added in v5.1 (not in v4.1):     {len(added)}")

if len(removed) > 0 or len(added) > 0:
    print("\n[3] BREAKDOWN OF CHANGES")
    print("-" * 40)
    
    # Get details of removed controls
    removed_df = v4_selected[v4_selected["phys_id"].isin(removed)]
    added_df = v5_selected[v5_selected["phys_id"].isin(added)]
    
    print("Strata Affected by Removals (v4.1 -> v5.1):")
    if not removed_df.empty:
        print(removed_df["StratumID"].value_counts().to_dict())
    else:
        print("  None")
        
    print("\nStrata Affected by Additions (v4.1 -> v5.1):")
    if not added_df.empty:
        print(added_df["StratumID"].value_counts().to_dict())
    else:
        print("  None")
        
    print("\nBasin Distribution of Changes:")
    print(f"  Removed by Basin: {removed_df['Basin'].value_counts().to_dict() if not removed_df.empty else {}}")
    print(f"  Added by Basin:   {added_df['Basin'].value_counts().to_dict() if not added_df.empty else {}}")
else:
    print("\n[3] BREAKDOWN OF CHANGES")
    print("-" * 40)
    print("No changes detected. v5.1 is scientifically identical to v4.1.")

# ============================================================================
# 4. Standby Overlap (Secondary Diagnostic)
# ============================================================================
print("\n[4] STANDBY OVERLAP (Secondary Diagnostic)")
print("-" * 40)
v4_std_set = set(v4_standby["phys_id"])
v5_std_set = set(v5_standby["phys_id"])
std_overlap = len(v4_std_set.intersection(v5_std_set))
print(f"Standby Physical Overlap: {std_overlap} / 1200")

# ============================================================================
# 5. Audit Manifest Comparison
# ============================================================================
print("\n[5] AUDIT MANIFEST COMPARISON")
print("-" * 40)
print(f"Candidate Pool Rows (v4.1): {v4_audit['candidate_pool']['row_count']:,}")
print(f"Candidate Pool Rows (v5.1): {v5_audit['candidate_pool']['row_count']:,}")

print(f"\nProtocol SHA256 Match: {v4_audit['freeze_fingerprint']['protocol_sha256'] == v5_audit['freeze_fingerprint']['protocol_sha256']}")
print(f"IBTrACS SHA256 Match:  {v4_audit['data_source_hashes']['ibtracs_sha256'] == v5_audit['data_source_hashes']['ibtracs_sha256']}")
print(f"ERA5 LSM SHA256 Match: {v4_audit['data_source_hashes']['era5_lsm_sha256'] == v5_audit['data_source_hashes']['era5_lsm_sha256']}")

# ============================================================================
# 6. Conclusion
# ============================================================================
print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
if len(overlap) == 150:
    print("✅ v5.1 is SCIENTIFICALLY IDENTICAL to v4.1.")
    print("   The boundary bugfixes and optimizations did not alter the final 150 controls.")
    print("   v5.1 can be safely frozen as the canonical output.")
else:
    print(f"⚠️  v5.1 differs from v4.1 by {150 - len(overlap)} controls.")
    print("   This is EXPECTED due to the cross-year boundary fix.")
    print("   Review the strata breakdown above to confirm changes are isolated to month edges.")
    print("   v5.1 represents the scientifically corrected baseline and should be frozen.")
print("=" * 70)