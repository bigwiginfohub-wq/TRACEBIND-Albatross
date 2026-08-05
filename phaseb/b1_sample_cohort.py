"""
TRACEBIND Phase B1: Cohort Selection (v1.5 - FINAL FROZEN)
==========================================================
Purpose: Execute the pre-registered sampling specification to select EXACTLY 
150 Tropical Cyclones (50 per basin) based on deterministic algorithmic quotas.

INVARIANTS: 
1. Total selected TCs MUST equal EXPECTED_TOTAL.
2. Basin totals MUST equal TARGET_BASIN_TOTAL for NI, SI, and WP.
Under no circumstance is the RNG rerun after Phase B1.
"""

import pandas as pd
import numpy as np
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# ============================================================================
# Configuration & Constants
# ============================================================================
IBTRACS_CSV = Path(r"C:\TRACEBIND-Albatross\experiments\retrieval\labels\ibtracs_ALL.csv")
TIER1_CSV = Path(__file__).parent / "b075_eligible_tier1.csv"
OUTPUT_DIR = Path(__file__).parent

TARGET_BASIN_TOTAL = 50
BASE_STRATA_QUOTA = 16  # 3 strata * 16 = 48. Deficit of 2 distributed per basin.
MAX_FRACTION = 0.40
SEED = 42
SAMPLER_VERSION = "TRACEBIND_B1_SAMPLER_V1.5_FINAL"

# Frozen Environment (Strict Match Required)
FROZEN_VERSIONS = {
    "python": "3.14.4",
    "numpy": "2.4.6",
    "pandas": "3.0.5"
}

# ============================================================================
# Helper Functions
# ============================================================================
def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_protocol_hash():
    protocol_path = OUTPUT_DIR / "PHASE_B1_SAMPLING_PROTOCOL_FINAL.md"
    return compute_sha256(protocol_path) if protocol_path.exists() else "PROTOCOL_FILE_NOT_FOUND"

def get_script_hash():
    return compute_sha256(Path(__file__))

def get_git_hash():
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, cwd=OUTPUT_DIR.parent)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "NOT_GIT_REPOSITORY"

# ============================================================================
# Main Execution
# ============================================================================
def run_sampling():
    print("=" * 85)
    print(f"PHASE B1: Cohort Selection ({SAMPLER_VERSION})")
    print("=" * 85)
    
    # 0. Environment Verification (Strict Match)
    print("\n[0/8] Verifying computational environment...")
    current_versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__
    }
    for pkg, frozen_ver in FROZEN_VERSIONS.items():
        current_ver = current_versions[pkg]
        if current_ver != frozen_ver:
            raise RuntimeError(f"CRITICAL: Environment mismatch for {pkg}. Current: {current_ver}, Frozen: {frozen_ver}. Aborting.")
        print(f"  → {pkg.capitalize()}: {current_ver} (Frozen: {frozen_ver}) [✓]")

    # 1. Load Data
    print("\n[1/8] Loading eligible Tier 1 pool...")
    df = pd.read_csv(TIER1_CSV)
    print(f"  → Loaded {len(df)} eligible storms.")
    
    rng = np.random.default_rng(SEED)
    
    # 2. Algorithmic Sampling (Strict 50-per-Basin Logic)
    print("\n[2/8] Computing algorithmic quotas (Strict 50-per-Basin Invariant)...")
    
    basins = ['NI', 'SI', 'WP']
    intensities = ['Weak (<64kt)', 'Moderate (64-95kt)', 'Intense (>=96kt)']
    EXPECTED_TOTAL = TARGET_BASIN_TOTAL * len(basins)
    
    strata_info = {}
    sampling_plan = {}
    basin_totals = {}
    
    for basin in basins:
        basin_df = df[df['BASIN'] == basin]
        basin_provisional_total = 0
        
        # Step A: Base Quota & Max Cap per stratum
        for intensity in intensities:
            stratum_df = basin_df[basin_df['intensity_class'] == intensity]
            available = len(stratum_df)
            
            if available == 0:
                max_sample = 0
            elif available < 10:
                max_sample = available
            else:
                max_sample = int(np.floor(available * MAX_FRACTION))
                
            provisional = min(BASE_STRATA_QUOTA, max_sample)
            
            strata_info[(basin, intensity)] = {
                'df': stratum_df,
                'available': available,
                'max_sample': max_sample,
                'provisional': provisional,
                'final': provisional
            }
            sampling_plan[(basin, intensity)] = provisional
            basin_provisional_total += provisional

        # Step B: Proportional Redistribution WITHIN this basin
        deficit = TARGET_BASIN_TOTAL - basin_provisional_total
        
        if deficit > 0:
            uncapped = {k: v for k, v in strata_info.items() if k[0] == basin and v['final'] < v['max_sample']}
            total_remaining_capacity = sum(v['max_sample'] - v['final'] for v in uncapped.values())
            
            if total_remaining_capacity > 0:
                shares = {}
                remainders = {}
                for key, data in uncapped.items():
                    capacity = data['max_sample'] - data['final']
                    exact_share = deficit * (capacity / total_remaining_capacity)
                    shares[key] = int(np.floor(exact_share))
                    remainders[key] = exact_share - shares[key]
                
                distributed = sum(shares.values())
                remainder_deficit = deficit - distributed
                
                # Safe distribution loop (prevents IndexError)
                sorted_remainders = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
                remainder_idx = 0
                while remainder_deficit > 0:
                    key = sorted_remainders[remainder_idx % len(sorted_remainders)][0]
                    shares[key] += 1
                    remainder_deficit -= 1
                    remainder_idx += 1
                    
                for key, extra in shares.items():
                    strata_info[key]['final'] += extra
                    sampling_plan[key] += extra

        # Step C: Basin Invariant Check
        final_basin_total = sum(sampling_plan[(basin, i)] for i in intensities)
        basin_totals[basin] = final_basin_total
        
        if final_basin_total != TARGET_BASIN_TOTAL:
            raise RuntimeError(f"CRITICAL: Basin {basin} total is {final_basin_total}, expected {TARGET_BASIN_TOTAL}. 40% cap may be too restrictive for this basin.")

    print(f"  ✓ Basin totals computed: NI={basin_totals['NI']}, SI={basin_totals['SI']}, WP={basin_totals['WP']}, TOTAL={sum(basin_totals.values())}")

    # Step D: Generate Excluded Report & Sampling Plan
    excluded_report = []
    sampling_plan_records = []
    
    for basin in basins:
        for intensity in intensities:
            info = strata_info[(basin, intensity)]
            reason = "None"
            if info['available'] == 0:
                reason = "Zero available in pool"
            elif info['final'] < info['available']:
                reason = f"Capped at {MAX_FRACTION*100:.0f}% or target quota"
                
            excluded_report.append({
                'Basin': basin,
                'Intensity': intensity,
                'Available': info['available'],
                'Cap': info['max_sample'],
                'Selected': info['final'],
                'Reason': reason,
                'SamplingFraction': f"{info['final']}/{info['available']}" if info['available'] > 0 else "0/0",
                'SamplingFractionNumeric': info['final'] / info['available'] if info['available'] > 0 else 0.0
            })
            
            sampling_plan_records.append({
                'Basin': basin,
                'Intensity': intensity,
                'Available': info['available'],
                'Cap': info['max_sample'],
                'Selected': info['final']
            })

    # 3. Deterministic Randomization & Selection
    print("\n[3/8] Executing deterministic randomization and selection...")
    
    randomized_order_records = []
    selected_records = []
    
    for (basin, intensity), target_n in sampling_plan.items():
        stratum_df = strata_info[(basin, intensity)]['df']
        available = strata_info[(basin, intensity)]['available']
        
        if len(stratum_df) == 0:
            continue
            
        shuffled_sids = stratum_df['SID'].tolist()
        rng.shuffle(shuffled_sids)
        
        for rank, sid in enumerate(shuffled_sids, start=1):
            randomized_order_records.append({
                'Basin': basin,
                'Intensity': intensity,
                'RandomRank': rank,
                'SID': sid,
                'Status': 'Selected' if rank <= target_n else 'Standby (Replacement)'
            })
            
        selected_sids = shuffled_sids[:target_n]
        for rank, sid in enumerate(selected_sids, start=1):
            row = stratum_df[stratum_df['SID'] == sid].iloc[0]
            selected_records.append({
                'Type': 'TC',
                'SID': sid,
                'Basin': basin,
                'Intensity': intensity,
                'SEASON': row['SEASON'],
                'NAME': row['NAME'],
                'RandomRank': rank,
                'SamplingFraction': f"{target_n}/{available}",
                'SamplingFractionNumeric': target_n / available
            })

    # 4. Save Deliverables
    print("\n[4/8] Saving deliverables...")
    
    rand_order_df = pd.DataFrame(randomized_order_records)
    rand_order_path = OUTPUT_DIR / "randomized_order.csv"
    rand_order_df.to_csv(rand_order_path, index=False)
    
    selected_df = pd.DataFrame(selected_records)
    selected_path = OUTPUT_DIR / "selected_cohort_ids.csv"
    selected_df.to_csv(selected_path, index=False)
    
    excluded_df = pd.DataFrame(excluded_report)
    excluded_path = OUTPUT_DIR / "excluded_strata_report.csv"
    excluded_df.to_csv(excluded_path, index=False)
    
    plan_df = pd.DataFrame(sampling_plan_records)
    plan_path = OUTPUT_DIR / "sampling_plan.csv"
    plan_df.to_csv(plan_path, index=False)
    
    # 5. Generate Audit Manifest
    print("\n[5/8] Generating cryptographic audit manifest...")
    
    audit_data = {
        "sampler_version": SAMPLER_VERSION,
        "sampler_sha256": get_script_hash(),
        "protocol_version": "1.0",
        "protocol_sha256": get_protocol_hash(),
        "git_commit_hash": get_git_hash(),
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "software_versions": current_versions,
        "frozen_versions": FROZEN_VERSIONS,
        "source_data": {"filename": IBTRACS_CSV.name, "sha256": compute_sha256(IBTRACS_CSV)},
        "input_data": {"filename": TIER1_CSV.name, "sha256": compute_sha256(TIER1_CSV)},
        "output_data": {"filename": selected_path.name, "sha256": compute_sha256(selected_path)},
        "sampling_summary": {
            "total_selected_tcs": len(selected_df),
            "basin_totals": basin_totals,
            "stratum_quotas": {f"{k[0]}_{k[1]}": v for k, v in sampling_plan.items()}
        }
    }
    
    audit_path = OUTPUT_DIR / "sampling_audit.json"
    with open(audit_path, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2)
        
    # 6. Generate Dataset Manifest
    print("\n[6/8] Generating dataset manifest (Provenance Chain)...")
    
    manifest_data = {
        "manifest_version": "1.0",
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "parent_stage": "B0.75 Population Characterization",
        "parent_input_hash": compute_sha256(TIER1_CSV),
        "current_stage": "B1 Cohort Selection",
        "cohort_hash": compute_sha256(selected_path),
        "audit_hash": compute_sha256(audit_path),
        "total_selected": len(selected_df),
        "basin_counts": selected_df['Basin'].value_counts().to_dict(),
        "intensity_counts": selected_df['Intensity'].value_counts().to_dict(),
        "random_seed": SEED,
        "software_versions": current_versions
    }
    
    manifest_path = OUTPUT_DIR / "dataset_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2)
        
    # 7. Final Invariant Checks
    print("\n[7/8] Running final invariant checks...")
    
    assert len(rand_order_df) == len(df), "Randomized order must contain every eligible SID exactly once."
    for (b, i), count in rand_order_df.groupby(['Basin', 'Intensity']).size().items():
        input_count = len(df[(df['BASIN'] == b) & (df['intensity_class'] == i)])
        assert count == input_count, f"Mismatch in stratum {b}/{i}: Order has {count}, Input has {input_count}"
    print("  ✓ Randomized order contains every eligible SID exactly once.")
    
    assert selected_df["SID"].is_unique, "CRITICAL: Duplicate SIDs detected in selected cohort!"
    assert len(selected_df) == selected_df["SID"].nunique(), "CRITICAL: SID count mismatch!"
    print("  ✓ Selected cohort contains unique SIDs only.")
    
    assert len(selected_df) == EXPECTED_TOTAL, f"CRITICAL: Total selected is {len(selected_df)}, expected {EXPECTED_TOTAL}"
    print(f"  ✓ Total selected TCs = {EXPECTED_TOTAL}")
    
    actual_basins = selected_df['Basin'].value_counts().to_dict()
    expected_basins = {b: TARGET_BASIN_TOTAL for b in basins}
    assert actual_basins == expected_basins, f"CRITICAL: Basin mismatch! Actual: {actual_basins}, Expected: {expected_basins}"
    print(f"  ✓ Basin balance enforced: NI={TARGET_BASIN_TOTAL}, SI={TARGET_BASIN_TOTAL}, WP={TARGET_BASIN_TOTAL}")

    # 8. Summary
    print("\n[8/8] Phase B1 Sampling Complete!")
    print("-" * 85)
    print(f"  → Sampling Plan saved to: {plan_path.name}")
    print(f"  → Randomized Order saved to: {rand_order_path.name}")
    print(f"  → Selected Cohort saved to: {selected_path.name}")
    print(f"  → Excluded Report saved to: {excluded_path.name}")
    print(f"  → Audit Manifest saved to: {audit_path.name}")
    print(f"  → Dataset Manifest saved to: {manifest_path.name}")
    print("=" * 85)
    print("✅ Phase B1 Cohort Selection is now FROZEN.")
    print("   Under no circumstance is the RNG rerun. Use RandomRank for replacements.")
    print("   Proceed to Phase B2: ERA5 Acquisition.")
    print("=" * 85)

if __name__ == "__main__":
    run_sampling()