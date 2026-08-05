"""
TRACEBIND-Albatross: Milestone C - Final Cohort Correlation (CORRECTED & FILTERED)
==================================================================================
Purpose: Final evaluation of the Two-Scale Interpretation hypothesis using 
the definitively corrected vorticity calculation and the 80% top-vorticity 
window filter.
"""

import sys
import json
import numpy as np
import scipy.stats as stats
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_DIR = Path("outputs/milestone_C")

def run_final_correlation():
    print("=" * 80)
    print("MILESTONE C: FINAL COHORT CORRELATION (CORRECTED & FILTERED)")
    print("=" * 80)
    
    # Load the definitive data from the legacy vs corrected run
    report_path = OUTPUT_DIR / "legacy_vs_corrected_report.json"
    with open(report_path, "r") as f:
        data = json.load(f)
    
    cases = data["cases"]
    
    print("\nExtracting definitive Corrected C_phi and Top 80% Median Distances...\n")
    print(f"{'File':<25} | {'Corrected Cφ':<12} | {'Top 80% Median Dist (km)'}")
    print("-" * 75)
    
    global_cphis = []
    median_dists = []
    
    for c in cases:
        global_cphis.append(c["corrected_c_phi"])
        median_dists.append(c["sensitivity_top80_median_km"])
        print(f"{c['filename']:<25} | {c['corrected_c_phi']:<12.4f} | {c['sensitivity_top80_median_km']:.1f}")
        
    # Compute Correlation
    pearson_r, pearson_p = stats.pearsonr(global_cphis, median_dists)
    spearman_rho, spearman_p = stats.spearmanr(global_cphis, median_dists)
    
    print("\n" + "=" * 80)
    print("FINAL CORRELATION: Corrected Global Cφ vs. Top 80% Median Center Distance")
    print("=" * 80)
    print(f"Pearson  r = {pearson_r:7.4f}  (p = {pearson_p:.4e})")
    print(f"Spearman ρ = {spearman_rho:7.4f}  (p = {spearman_p:.4e})")
    print("=" * 80)
    
    if abs(pearson_r) < 0.3:
        print("\n✅ CONCLUSION: No meaningful linear relationship exists.")
        print("   The hypothesis that 'Global Cφ is driven by median center alignment' is FALSIFIED.")
    elif pearson_r < -0.5:
        print("\n⚠️  CONCLUSION: A moderate negative relationship exists.")
        print("   The hypothesis is partially supported, but other factors are likely dominant.")
    else:
        print("\n⚠️  CONCLUSION: An unexpected relationship exists. Further investigation required.")
        
    print("=" * 80)

if __name__ == "__main__":
    run_final_correlation()