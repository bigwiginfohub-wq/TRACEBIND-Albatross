"""
TRACEBIND B4: Final Integrity Verification
===========================================
Inspects the machine-readable outputs of the B4 analysis engine
to verify consistency, schema compliance, and logical coherence.
"""
import pandas as pd
import numpy as np
import json
import hashlib
from pathlib import Path

PHASEB_DIR = Path(__file__).parent
RESULTS_PATH = PHASEB_DIR / "b4_statistical_results.json"
AUDIT_PATH = PHASEB_DIR / "b4_audit.json"
INPUT_CSV = PHASEB_DIR / "b3_descriptors.csv"

def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

print("=" * 85)
print("TRACEBIND B4: INTEGRITY VERIFICATION")
print("=" * 85)

all_pass = True

# 1. Load Artifacts
with open(RESULTS_PATH, 'r') as f: results = json.load(f)
with open(AUDIT_PATH, 'r') as f: audit = json.load(f)

# 2. Cryptographic Chain
print("\n[1] CRYPTOGRAPHIC CHAIN")
if compute_sha256(INPUT_CSV) == audit["input_artifact_sha256"]:
    print("  ✅ B3 Input CSV hash matches audit")
else:
    print("  ❌ B3 Input CSV hash MISMATCH"); all_pass = False

if compute_sha256(RESULTS_PATH) == audit["output_sha256"]:
    print("  ✅ B4 Results JSON hash matches audit")
else:
    print("  ❌ B4 Results JSON hash MISMATCH"); all_pass = False

# 3. Schema & Software Environment
print("\n[2] SCHEMA & ENVIRONMENT")
if "software_environment" in audit and "scipy" in audit["software_environment"]:
    print(f"  ✅ Software environment recorded (SciPy {audit['software_environment']['scipy']})")
else:
    print("  ❌ Software environment missing"); all_pass = False

if "directional_expectation" in results:
    print("  ✅ Directional expectation metadata present")
else:
    print("  ❌ Directional expectation missing"); all_pass = False

# 4. Statistical Coherence Checks
print("\n[3] STATISTICAL COHERENCE")
# P-values in [0, 1]
mw_p = results["primary_analysis"]["p_value"]
t_p = results["sensitivity_analysis"]["p_value"]
if 0 <= mw_p <= 1 and 0 <= t_p <= 1:
    print(f"  ✅ P-values valid (MW: {mw_p:.2e}, Welch: {t_p:.2e})")
else:
    print("  ❌ Invalid p-values"); all_pass = False

# AUC and CI in [0, 1]
auc = results["discrimination"]["value"]
ci_l = results["discrimination"]["ci_lower_95"]
ci_u = results["discrimination"]["ci_upper_95"]
if 0 <= ci_l <= auc <= ci_u <= 1:
    print(f"  ✅ AUC and 95% CI valid and ordered ({auc:.4f} [{ci_l:.4f}, {ci_u:.4f}])")
else:
    print("  ❌ Invalid AUC or CI bounds"); all_pass = False

# Cliff's Delta consistency with AUC
cd = results["primary_effect_size"]["value"]
expected_auc_from_cd = (1 + cd) / 2
if abs(auc - expected_auc_from_cd) < 0.01:
    print(f"  ✅ Cliff's delta ({cd:.4f}) is mathematically consistent with AUC ({auc:.4f})")
else:
    print("  ❌ Cliff's delta and AUC are inconsistent"); all_pass = False

# Directional consistency
obs_sign = results["directional_expectation"]["observed_cliffs_delta_sign"]
obs_auc = results["directional_expectation"]["observed_auc_direction"]
if (cd > 0 and obs_sign == "positive" and obs_auc == "above_0.5") or \
   (cd < 0 and obs_sign == "negative" and obs_auc == "below_0.5"):
    print("  ✅ Directional metadata is logically consistent")
else:
    print("  ❌ Directional metadata is inconsistent"); all_pass = False

print("\n" + "=" * 85)
if all_pass:
    print("✅ B4 INTEGRITY FULLY VERIFIED. READY FOR GIT FREEZE.")
else:
    print("❌ B4 INTEGRITY CHECK FAILED. Review above.")
print("=" * 85)