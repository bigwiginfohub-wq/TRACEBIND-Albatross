"""
TRACEBIND-Albatross: Milestone A2c - Translation Sensitivity Analysis
=====================================================================
Validation Status: [ ] Untested  [ ] Characterized  [ ] Frozen  [ ] Published

Purpose: Quantify the frozen operator's sensitivity to incorrect center placement.

Because the frozen Cφ operator is center-referenced, we must understand how
robust it is when the assumed center deviates from the true vortex center.

This is critical for atmospheric applications where cyclone centers are
estimated (e.g., from MSLP minimum or vorticity maximum) rather than known exactly.

Experimental Design:
  - Generate a perfect Lamb-Oseen vortex centered at (0, 0).
  - Evaluate Cφ with the operator's center offset by 0%, 10%, 20%, ..., 50% 
    of the domain width.
  - Record the degradation curve.
"""

import sys
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.tracebind.frozen_operators import compute_phase_coherence

OUTPUT_DIR = Path("outputs/milestone_A2c")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def lamb_oseen_vortex(X, Y, cx=0.0, cy=0.0, r0=15.0, gamma=1e5):
    """Generates a Lamb-Oseen vortex centered at (cx, cy)."""
    R = np.sqrt((X - cx)**2 + (Y - cy)**2) + 1e-12
    v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
    u = -v_theta * (Y - cy) / R
    v = v_theta * (X - cx) / R
    return u, v

def run_translation_sensitivity():
    print("=" * 75)
    print("MILESTONE A2c: TRANSLATION SENSITIVITY ANALYSIS")
    print("=" * 75)
    
    # Grid setup: 100x100, spanning -50 to +50
    nx, ny = 100, 100
    x = np.linspace(-50.0, 50.0, nx)
    y = np.linspace(-50.0, 50.0, ny)
    X, Y = np.meshgrid(x, y)
    
    # Generate a perfect vortex centered at (0, 0)
    u, v = lamb_oseen_vortex(X, Y, cx=0.0, cy=0.0, r0=15.0, gamma=1e5)
    
    # Domain width for offset calculation
    domain_width = 100.0  # from -50 to +50
    
    # Test center offsets: 0%, 10%, 20%, ..., 50% of domain width
    offset_percentages = [0, 10, 20, 30, 40, 50]
    
    results = {
        "milestone": "A2c",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "vortex_center": (0.0, 0.0),
        "domain_width": domain_width,
        "translation_sensitivity": []
    }
    
    print("\nEvaluating Cφ with center offset from true vortex center...\n")
    print(f"{'Offset (%)':<12} | {'Offset (units)':<15} | {'Cφ':>8}")
    print("-" * 45)
    
    for pct in offset_percentages:
        offset_units = (pct / 100.0) * domain_width
        
        # Evaluate with the operator's center offset by (offset_units, 0)
        # This simulates an error in center estimation
        operator_center = (offset_units, 0.0)
        
        c_phi = compute_phase_coherence(u, v, X=X, Y=Y, center=operator_center)
        
        results["translation_sensitivity"].append({
            "offset_percentage": pct,
            "offset_units": offset_units,
            "c_phi": round(c_phi, 6)
        })
        
        print(f"{pct:<12} | {offset_units:<15.2f} | {c_phi:>8.4f}")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(8, 5))
    offsets = [entry["offset_percentage"] for entry in results["translation_sensitivity"]]
    cphis = [entry["c_phi"] for entry in results["translation_sensitivity"]]
    
    ax.plot(offsets, cphis, 'o-', linewidth=2, markersize=8, color='#d62728')
    ax.set_xlabel("Center Offset (% of Domain Width)")
    ax.set_ylabel("Cφ")
    ax.set_title("A2c: Translation Sensitivity (Robustness to Center Estimation Error)")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.1)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "translation_sensitivity.png", dpi=200)
    plt.close()
    
    # Save JSON
    report_path = Path("experiments/milestone_A2c/translation_sensitivity_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Interpretation
    print("\n" + "=" * 75)
    print("INTERPRETATION")
    print("=" * 75)
    
    # Calculate degradation rate
    c_phi_0 = results["translation_sensitivity"][0]["c_phi"]
    c_phi_50 = results["translation_sensitivity"][-1]["c_phi"]
    degradation = c_phi_0 - c_phi_50
    
    print(f"\nBaseline Cφ (0% offset): {c_phi_0:.4f}")
    print(f"Cφ at 50% offset:        {c_phi_50:.4f}")
    print(f"Total degradation:       {degradation:.4f}")
    
    if degradation < 0.1:
        print("\n✅ ROBUST: The operator is highly robust to center estimation errors.")
        print("   This is a strength for atmospheric applications.")
    elif degradation < 0.3:
        print("\n⚠️  MODERATE: The operator shows moderate sensitivity to center errors.")
        print("   Accurate center estimation is important but not critical.")
    else:
        print("\n❌ SENSITIVE: The operator is highly sensitive to center placement.")
        print("   Center estimation becomes a critical preprocessing step.")
    
    print("=" * 75)
    
    return True

if __name__ == "__main__":
    run_translation_sensitivity()