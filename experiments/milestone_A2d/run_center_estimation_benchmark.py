"""
TRACEBIND-Albatross: Milestone A2d - Center Estimation Benchmark
================================================================
Validation Status: [ ] Untested  [ ] Characterized  [ ] Frozen  [ ] Published

Purpose: Benchmark candidate center-estimation strategies on synthetic flows
where the true center is known. This formalizes the preprocessing contract
required by Operator Property P4 (Center Dependence).

Center Estimation Strategies:
  1. Geometric center (grid midpoint)
  2. Maximum vorticity (argmax of |curl|)
  3. Maximum speed (argmax of |V|)
  4. Center of mass (speed-weighted centroid)

Output: A ranked recommendation of which estimator is most accurate for
different flow types, forming the basis for the preprocessing contract.
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

OUTPUT_DIR = Path("outputs/milestone_A2d")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Synthetic Flow Generators (with known true centers)
# ============================================================================
def build_grid(nx=100, ny=100, span=100.0):
    x = np.linspace(-span/2, span/2, nx)
    y = np.linspace(-span/2, span/2, ny)
    return np.meshgrid(x, y)

def flow_single_vortex(X, Y, cx=0.0, cy=0.0, r0=15.0, gamma=1e5):
    """Single Lamb-Oseen vortex with known center (cx, cy)."""
    R = np.sqrt((X - cx)**2 + (Y - cy)**2) + 1e-12
    v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
    u = -v_theta * (Y - cy) / R
    v = v_theta * (X - cx) / R
    return u, v, (cx, cy)

def flow_off_center_vortex(X, Y):
    """Vortex centered at (20, -15) to test off-center estimation."""
    return flow_single_vortex(X, Y, cx=20.0, cy=-15.0, r0=12.0, gamma=8e4)

def flow_double_vortex(X, Y):
    """Two counter-rotating vortices. True center is ambiguous."""
    sep = 30.0
    r0 = 10.0
    gamma = 5e4
    
    # Vortex 1: CCW at (-sep/2, 0)
    R1 = np.sqrt((X + sep/2)**2 + Y**2) + 1e-12
    vt1 = (gamma / (2 * np.pi * R1)) * (1.0 - np.exp(-((R1 / r0) ** 2)))
    u1, v1 = -vt1 * Y / R1, vt1 * (X + sep/2) / R1
    
    # Vortex 2: CW at (+sep/2, 0)
    R2 = np.sqrt((X - sep/2)**2 + Y**2) + 1e-12
    vt2 = (gamma / (2 * np.pi * R2)) * (1.0 - np.exp(-((R2 / r0) ** 2)))
    u2, v2 = vt2 * Y / R2, -vt2 * (X - sep/2) / R2
    
    u = u1 + u2
    v = v1 + v2
    
    # True center is ambiguous; we'll use the geometric midpoint as reference
    return u, v, (0.0, 0.0)

def flow_jet_with_vortex(X, Y):
    """Background jet with embedded vortex. True center is the vortex center."""
    # Jet
    U_jet = 20.0 / np.cosh(Y / 15.0)**2
    V_jet = np.zeros_like(Y)
    
    # Embedded vortex at (10, 0)
    cx, cy = 10.0, 0.0
    R = np.sqrt((X - cx)**2 + (Y - cy)**2) + 1e-12
    r0, gamma = 12.0, 6e4
    v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
    U_vort = -v_theta * (Y - cy) / R
    V_vort = v_theta * (X - cx) / R
    
    u = U_jet + U_vort
    v = V_jet + V_vort
    
    return u, v, (cx, cy)

# ============================================================================
# Center Estimation Strategies
# ============================================================================
def estimate_geometric_center(X, Y, u, v):
    """Strategy 1: Grid midpoint."""
    return (float(X.mean()), float(Y.mean()))

def estimate_max_vorticity_center(X, Y, u, v):
    """Strategy 2: Location of maximum absolute vorticity."""
    dx = X[0, 1] - X[0, 0]
    dy = Y[1, 0] - Y[0, 0]
    
    # Compute vorticity (dv/dx - du/dy)
    dvdx = np.gradient(v, dx, axis=1)
    dudy = np.gradient(u, dy, axis=0)
    vorticity = dvdx - dudy
    
    # Find location of maximum absolute vorticity
    idx = np.unravel_index(np.argmax(np.abs(vorticity)), vorticity.shape)
    return (float(X[idx]), float(Y[idx]))

def estimate_max_speed_center(X, Y, u, v):
    """Strategy 3: Location of maximum wind speed."""
    speed = np.sqrt(u**2 + v**2)
    idx = np.unravel_index(np.argmax(speed), speed.shape)
    return (float(X[idx]), float(Y[idx]))

def estimate_center_of_mass(X, Y, u, v):
    """Strategy 4: Speed-weighted centroid."""
    speed = np.sqrt(u**2 + v**2)
    total_speed = np.sum(speed)
    if total_speed < 1e-9:
        return (float(X.mean()), float(Y.mean()))
    
    cx = np.sum(X * speed) / total_speed
    cy = np.sum(Y * speed) / total_speed
    return (float(cx), float(cy))

# ============================================================================
# Benchmark Execution
# ============================================================================
FLOW_LIBRARY = {
    "single_vortex_centered": lambda X, Y: flow_single_vortex(X, Y, cx=0.0, cy=0.0),
    "single_vortex_off_center": flow_off_center_vortex,
    "double_vortex_counter_rot": flow_double_vortex,
    "jet_with_embedded_vortex": flow_jet_with_vortex,
}

ESTIMATORS = {
    "geometric_center": estimate_geometric_center,
    "max_vorticity": estimate_max_vorticity_center,
    "max_speed": estimate_max_speed_center,
    "center_of_mass": estimate_center_of_mass,
}

def run_benchmark():
    print("=" * 80)
    print("MILESTONE A2d: CENTER ESTIMATION BENCHMARK")
    print("=" * 80)
    
    X, Y = build_grid(nx=100, ny=100, span=100.0)
    
    results = {
        "milestone": "A2d",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "benchmarks": {}
    }
    
    for flow_name, flow_func in FLOW_LIBRARY.items():
        print(f"\n{'='*80}")
        print(f"Flow Type: {flow_name}")
        print(f"{'='*80}")
        
        u, v, true_center = flow_func(X, Y)
        print(f"True center: {true_center}")
        
        # Compute Cφ with true center (baseline)
        c_phi_true = compute_phase_coherence(u, v, X=X, Y=Y, center=true_center)
        print(f"Cφ with true center: {c_phi_true:.4f}")
        
        flow_results = {
            "true_center": true_center,
            "c_phi_true_center": round(c_phi_true, 6),
            "estimators": {}
        }
        
        # Test each estimator
        for est_name, est_func in ESTIMATORS.items():
            est_center = est_func(X, Y, u, v)
            c_phi_est = compute_phase_coherence(u, v, X=X, Y=Y, center=est_center)
            
            # Compute distance from true center
            dist = np.sqrt((est_center[0] - true_center[0])**2 + (est_center[1] - true_center[1])**2)
            
            flow_results["estimators"][est_name] = {
                "estimated_center": est_center,
                "distance_from_true": round(dist, 4),
                "c_phi": round(c_phi_est, 6),
                "c_phi_degradation": round(c_phi_true - c_phi_est, 6)
            }
            
            print(f"  → {est_name:25s}: center={est_center}, dist={dist:.2f}, Cφ={c_phi_est:.4f} (Δ={c_phi_true - c_phi_est:.4f})")
        
        results["benchmarks"][flow_name] = flow_results
    
    # Summary and recommendation
    print("\n" + "=" * 80)
    print("SUMMARY AND RECOMMENDATION")
    print("=" * 80)
    
    # Compute average performance across all flows
    estimator_scores = {name: [] for name in ESTIMATORS}
    for flow_name, flow_data in results["benchmarks"].items():
        for est_name, est_data in flow_data["estimators"].items():
            estimator_scores[est_name].append(est_data["c_phi"])
    
    print("\nAverage Cφ across all flow types (higher is better):")
    for est_name, scores in estimator_scores.items():
        avg = np.mean(scores)
        print(f"  {est_name:25s}: {avg:.4f}")
    
    best_estimator = max(estimator_scores, key=lambda k: np.mean(estimator_scores[k]))
    print(f"\n✅ RECOMMENDED ESTIMATOR: {best_estimator}")
    print(f"   (Average Cφ = {np.mean(estimator_scores[best_estimator]):.4f})")
    
    # Save JSON
    report_path = Path("experiments/milestone_A2d/center_estimation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Report saved to {report_path}")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    run_benchmark()