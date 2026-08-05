"""
TRACEBIND-Albatross: Milestone A2b - Operator Response Library
==============================================================
Validation Status: [ ] Untested  [ ] Characterized  [ ] Frozen  [ ] Published

Purpose: Generate a canonical fingerprint library of the frozen operator's
response to well-understood flow types. This answers:
  "What exactly does the operator measure?"

This library becomes a permanent reference for interpreting real ERA5 results.
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

OUTPUT_DIR = Path("outputs/milestone_A2b")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def build_grid(nx=100, ny=100, span=100.0):
    x = np.linspace(-span/2, span/2, nx)
    y = np.linspace(-span/2, span/2, ny)
    return np.meshgrid(x, y)

# ============================================================================
# Canonical Flow Library
# ============================================================================
def flow_uniform(X, Y, **kw):
    """Uniform eastward translation."""
    return np.full_like(X, 10.0), np.zeros_like(Y)

def flow_solid_body_rotation(X, Y, **kw):
    """Solid-body rotation (v_theta = omega * r)."""
    R = np.sqrt(X**2 + Y**2) + 1e-12
    omega = 0.1
    v_theta = omega * R
    return -v_theta * Y / R, v_theta * X / R

def flow_lamb_oseen(X, Y, r0=15.0, gamma=1e5, **kw):
    R = np.sqrt(X**2 + Y**2) + 1e-12
    v_theta = (gamma / (2 * np.pi * R)) * (1.0 - np.exp(-((R / r0) ** 2)))
    return -v_theta * Y / R, v_theta * X / R

def flow_rankine(X, Y, r0=15.0, gamma=1e5, **kw):
    """Rankine vortex (solid body inside r0, potential outside)."""
    R = np.sqrt(X**2 + Y**2) + 1e-12
    v_theta = np.where(R < r0, gamma * R / (2 * np.pi * r0**2), gamma / (2 * np.pi * R))
    return -v_theta * Y / R, v_theta * X / R

def flow_source(X, Y, strength=1e5, **kw):
    """Pure radial source (outflow)."""
    R = np.sqrt(X**2 + Y**2) + 1e-12
    v_r = strength / (2 * np.pi * R)
    return v_r * X / R, v_r * Y / R

def flow_sink(X, Y, strength=1e5, **kw):
    """Pure radial sink (inflow)."""
    R = np.sqrt(X**2 + Y**2) + 1e-12
    v_r = -strength / (2 * np.pi * R)
    return v_r * X / R, v_r * Y / R

def flow_saddle(X, Y, strain=0.1, **kw):
    """Hyperbolic stagnation point (saddle)."""
    return strain * X, -strain * Y

def flow_linear_shear(X, Y, shear=0.05, **kw):
    """Linear horizontal shear (u = shear * y)."""
    return shear * Y, np.zeros_like(X)

def flow_jet(X, Y, U_max=20.0, width=15.0, **kw):
    """Bickley jet (sech^2 profile)."""
    return U_max / np.cosh(Y / width)**2, np.zeros_like(X)

def flow_sinusoidal_wave(X, Y, amplitude=10.0, kx=0.1, ky=0.0, **kw):
    """Sinusoidal wave field (scalar-like, converted to gradient flow)."""
    phi = amplitude * np.sin(kx * X + ky * Y)
    # Gradient flow
    u = -amplitude * kx * np.cos(kx * X + ky * Y)
    v = -amplitude * ky * np.cos(kx * X + ky * Y)
    return u, v

def flow_double_vortex(X, Y, **kw):
    """Two counter-rotating vortices (von Karman street-like)."""
    sep = 30.0
    r0 = 10.0
    gamma = 5e4
    R1 = np.sqrt((X + sep/2)**2 + Y**2) + 1e-12
    R2 = np.sqrt((X - sep/2)**2 + Y**2) + 1e-12
    vt1 = (gamma / (2 * np.pi * R1)) * (1.0 - np.exp(-((R1 / r0) ** 2)))
    vt2 = (gamma / (2 * np.pi * R2)) * (1.0 - np.exp(-((R2 / r0) ** 2)))
    # Vortex 1: CCW at (-sep/2, 0); Vortex 2: CW at (+sep/2, 0)
    u1, v1 = -vt1 * Y / R1, vt1 * (X + sep/2) / R1
    u2, v2 = vt2 * Y / R2, -vt2 * (X - sep/2) / R2
    return u1 + u2, v1 + v2

def flow_meandering_jet(X, Y, **kw):
    """Jet with sinusoidal meander."""
    U_base = 15.0
    width = 12.0
    meander_amp = 8.0
    meander_k = 0.08
    y_center = meander_amp * np.sin(meander_k * X)
    return U_base / np.cosh((Y - y_center) / width)**2, np.zeros_like(X)

# ============================================================================
# Library Execution
# ============================================================================
FLOW_LIBRARY = {
    "uniform_translation":       flow_uniform,
    "solid_body_rotation":       flow_solid_body_rotation,
    "lamb_oseen_vortex":         flow_lamb_oseen,
    "rankine_vortex":            flow_rankine,
    "radial_source":             flow_source,
    "radial_sink":               flow_sink,
    "saddle_point":              flow_saddle,
    "linear_shear":              flow_linear_shear,
    "bickley_jet":               flow_jet,
    "sinusoidal_wave":           flow_sinusoidal_wave,
    "double_vortex_counter_rot": flow_double_vortex,
    "meandering_jet":            flow_meandering_jet,
}

def run_response_library():
    print("=" * 75)
    print("MILESTONE A2b: OPERATOR RESPONSE LIBRARY")
    print("=" * 75)
    
    X, Y = build_grid(nx=100, ny=100, span=100.0)
    
    library = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "grid": {"nx": 100, "ny": 100, "span": 100.0},
        "flows": {}
    }
    
    print(f"\nEvaluating {len(FLOW_LIBRARY)} canonical flows...\n")
    print(f"{'Flow Name':<35} | {'C_phi':>8}")
    print("-" * 50)
    
    fig, axes = plt.subplots(3, 4, figsize=(16, 12))
    axes = axes.flatten()
    
    for idx, (name, func) in enumerate(FLOW_LIBRARY.items()):
        u, v = func(X, Y)
        c_phi = compute_phase_coherence(u, v, X=X, Y=Y)
        library["flows"][name] = {"c_phi": round(c_phi, 6)}
        print(f"{name:<35} | {c_phi:>8.4f}")
        
        # Visualization
        ax = axes[idx]
        speed = np.sqrt(u**2 + v**2)
        im = ax.pcolormesh(X, Y, speed, cmap='viridis', shading='auto')
        ax.quiver(X[::5, ::5], Y[::5, ::5], u[::5, ::5], v[::5, ::5], 
                  color='white', scale=500, alpha=0.6)
        ax.set_title(f"{name}\nC_phi = {c_phi:.3f}", fontsize=9)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.suptitle("TRACEBIND-Albatross A2b: Operator Response Library", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "response_library_grid.png", dpi=150)
    plt.close()
    
    # Save library
    lib_path = Path("experiments/milestone_A2b/response_library.json")
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lib_path, "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2)
    
    # Interpretive summary
    print("\n" + "=" * 75)
    print("INTERPRETIVE SUMMARY")
    print("=" * 75)
    
    sorted_flows = sorted(library["flows"].items(), key=lambda x: x[1]["c_phi"], reverse=True)
    print("\nRanking by C_phi (highest to lowest):")
    for rank, (name, data) in enumerate(sorted_flows, 1):
        print(f"  {rank:2d}. {name:<35} C_phi = {data['c_phi']:.4f}")
    
    print("\n" + "=" * 75)
    print("✅ MILESTONE A2b COMPLETE")
    print("Response library saved. This is the fingerprint reference for Milestone B.")
    print("=" * 75)
    
    return True

if __name__ == "__main__":
    run_response_library()