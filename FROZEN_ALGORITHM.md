\# TRACEBIND: Frozen Algorithm Contract



\*\*Document Purpose:\*\* This document serves as the immutable, canonical reference for the TRACEBIND descriptor mathematics used in empirical validation. No modifications to this logic are permitted during hypothesis testing without a formal version bump and re-validation.



\---



\## 1. Canonical Algorithm Identification

\- \*\*Algorithm Name:\*\* Spatial Tangential Phase Alignment ($C\_\\phi$)

\- \*\*Source File:\*\* `phase7/sandbox/metrics/coherence.py` (Function: `compute\_phase\_coherence`)

\- \*\*Algorithm Version:\*\* Phase 7 Metric Operator (v1.0)

\- \*\*Status:\*\* \*\*FROZEN\*\*

\- \*\*Date Frozen:\*\* 2026-07-30

\- \*\*Used In:\*\* TRACEBIND-Atmosphere Phase 8 C2 Blinded Validation; TRACEBIND-Albatross Milestone A.

\- \*\*Repository Tag:\*\* `\[PENDING: Insert git tag for Phase 8 C2 release]`

\- \*\*Source SHA-256:\*\* `\[PENDING: Insert SHA256 from phase8/operator\_characterization run]`



\---



\## 2. Mathematical Definition

Given a 2D vector field $\\mathbf{V} = (u, v)$ on a grid with coordinates $(X, Y)$ and a defined center point $(x\_c, y\_c)$:



1\. \*\*Relative Coordinates:\*\* 

&#x20;  $X\_c = X - x\_c, \\quad Y\_c = Y - y\_c$

&#x20;  $R = \\sqrt{X\_c^2 + Y\_c^2} + \\epsilon \\quad (\\text{where } \\epsilon = 10^{-12})$



2\. \*\*Tangential Unit Vector ($\\mathbf{e}\_\\theta$):\*\*

&#x20;  $\\mathbf{e}\_\\theta = \\left( \\frac{-Y\_c}{R}, \\frac{X\_c}{R} \\right)$



3\. \*\*Velocity Magnitude:\*\*

&#x20;  $|\\mathbf{V}| = \\sqrt{u^2 + v^2} + \\epsilon$



4\. \*\*Normalized Tangential Alignment:\*\*

&#x20;  $\\text{dot\\\_tangential} = \\frac{u \\cdot e\_{\\theta x} + v \\cdot e\_{\\theta y}}{|\\mathbf{V}|}$



5\. \*\*Global Phase Coherence ($C\_\\phi$):\*\*

&#x20;  $C\_\\phi = \\frac{1}{N\_{\\text{valid}}} \\sum\_{\\text{masked}} \\left| \\text{dot\\\_tangential} \\right|$



\---



\## 3. Preprocessing \& Inputs

\- \*\*Required Inputs:\*\* 

&#x20; - `u`: 2D NumPy array (float64), zonal wind component.

&#x20; - `v`: 2D NumPy array (float64), meridional wind component.

\- \*\*Optional Inputs:\*\*

&#x20; - `X`, `Y`: 2D coordinate grids. \*Critical Assumption:\* If not provided, the algorithm auto-generates index-based grids. For physical atmospheric data (e.g., ERA5), \*\*physical coordinate grids MUST be explicitly passed\*\*, or the `center` must be carefully mapped to array indices.

&#x20; - `center`: Tuple `(xc, yc)`. If `None`, defaults to the geometric midpoint.

&#x20; - `mask`: 2D boolean array defining the valid evaluation domain.



\---



\## 4. Normalization \& Constants

\- \*\*Epsilon ($\\epsilon$):\*\* $10^{-12}$ (prevents division by zero).

\- \*\*Data Type:\*\* All inputs are explicitly cast to `np.float64` upon entry.

\- \*\*Output Range:\*\* $C\_\\phi \\in \[0.0, 1.0]$.



\---



## 5. Explicit Assumptions & Limitations

### 5.1 Center Dependency
This formulation intrinsically assumes a meaningful center of rotation or convergence exists within the domain. It is not translation-invariant.

### 5.2 2D Slice Independence
The algorithm operates strictly on 2D slices. No 3D vertical interpolation is permitted.

### 5.3 Mask Handling
If a mask is provided and contains no `True` values, the function safely returns `0.0`.

---

## 6. Operator Properties (Formal Specification)

### Property P1: Determinism
The operator is fully deterministic. Given identical inputs (u, v, X, Y, center, mask), it produces bitwise-identical outputs.

### Property P2: Numerical Stability
The operator exhibits CV < 0.01% under repeated evaluation with numerical jitter (Milestone A2a).

### Property P3: Null Separation
The operator clearly separates structured rotational flow (Cφ ≈ 1.0) from multiple null models (Cφ ≈ 0.62–0.64) (Milestone A2a).

### Property P4: Center Dependence (CRITICAL)
**The frozen spatial tangential coherence operator is not translation invariant. Its output is explicitly conditioned on the reference center. Therefore, center estimation is part of the preprocessing pipeline rather than part of the descriptor mathematics.**

Empirical characterization (Milestone A2c) shows:
- 0% center offset → Cφ = 1.0000 (perfect)
- 10% center offset → Cφ = 0.9602 (excellent)
- 20% center offset → Cφ = 0.8838 (good)
- 50% center offset → Cφ = 0.6551 (degrades to uniform flow baseline)

**Implication:** Accurate center estimation (within ~10–20% of true feature center) is a **required preprocessing step** for atmospheric applications. The operator gracefully degrades to background shear levels if the center is poorly estimated, preventing false positives but requiring explicit center-finding methodology.

### Property P5: Radial Flow Blindness
The operator yields Cφ = 0.0 for pure radial inflow/outflow, as radial vectors are orthogonal to tangential vectors (Milestone A2b).

### Property P6: Background Shear Baseline
Uniform translation, linear shear, and jet-like flows yield Cφ ≈ 0.648, establishing a baseline for organized non-rotational flow (Milestone A2b).
\---


---

## 6. Regression Test Reference Values (from Milestone A2b)

The following values were generated by the frozen operator on canonical synthetic flows (Milestone A2b). These serve as **regression tests** for future implementations.

Any re-implementation or port of the frozen operator must reproduce these values within a tolerance of ±0.001.

| Flow Type                  | Expected Cφ | Tolerance |
|----------------------------|-------------|-----------|
| Solid-body rotation        | 1.0000      | ±0.001    |
| Lamb-Oseen vortex          | 1.0000      | ±0.001    |
| Rankine vortex             | 1.0000      | ±0.001    |
| Radial source              | 0.0000      | ±0.001    |
| Radial sink                | 0.0000      | ±0.001    |
| Uniform translation        | 0.6479      | ±0.001    |
| Linear shear               | 0.6479      | ±0.001    |
| Bickley jet                | 0.6479      | ±0.001    |
| Sinusoidal wave            | 0.6479      | ±0.001    |
| Meandering jet             | 0.6479      | ±0.001    |
| Double vortex (counter-rot)| 0.5378      | ±0.001    |
| Saddle point               | 0.6935      | ±0.001    |

**Null Model Reference Values (from Milestone A2a):**

| Null Model                 | Mean Cφ     | Std Dev     |
|----------------------------|-------------|-------------|
| Fourier phase scramble     | 0.6235      | 0.0695      |
| Spatial shuffle            | 0.6347      | 0.0030      |
| Vector direction randomize | 0.6364      | 0.0030      |
| Uniform noise              | 0.6370      | 0.0030      |

These values establish the baseline behavior of the frozen operator and must be reproduced by any compliant implementation.

