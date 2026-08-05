\# TRACEBIND-Albatross: Preprocessing Contract



This document defines the mandatory preprocessing steps that must be applied to raw atmospheric data \*before\* it is passed to the frozen TRACEBIND operators.



Adherence to this contract is required for reproducibility. Deviations must be explicitly documented and justified.



\---



\## Rule 1: Coordinate System

Data must be provided on a regular 2D grid. If the native data is in latitude/longitude, it must be treated under the \*\*Local Cartesian Approximation\*\* (valid for regional domains < \~500km). For global or large-scale domains, a proper map projection (e.g., Lambert Conformal) must be applied, and the resulting physical (X, Y) coordinates must be passed to the operator.



\---



\## Rule 2: Center Estimation



Per \*\*Operator Property P4 (Center Dependence)\*\*, the frozen Cφ operator requires an explicit reference center. The choice of center estimator determines \*what scientific question\* the descriptor answers.



\### Default Center Estimator: Maximum Absolute Vorticity

\*\*Applicable to:\*\* Datasets expected to contain a \*\*dominant coherent vortex\*\* (e.g., single cyclones, tropical cyclone eyes, isolated mesoscale vortices).



\*\*Method:\*\*

1\. Compute relative vorticity: ζ = ∂v/∂x − ∂u/∂y

2\. Find the grid index (i, j) that maximizes |ζ|

3\. Use the physical coordinates (X\_{i,j}, Y\_{i,j}) as the `center` parameter



\*\*Justification:\*\* Milestone A2d benchmarking demonstrated that for single-center rotational flows, max\_vorticity locates the true vortex center with sub-grid accuracy (avg. distance < 1.0 unit), yielding Cφ within 0.001 of the true-center baseline.



\### Critical Limitation

\*\*For multiple-vortex systems, complex interacting vortices, or non-rotational flows, this estimator intentionally locks onto the dominant rotational feature and therefore characterizes that feature rather than the entire flow.\*\*

### Rule 2.1: Operational Limit – Noise Sensitivity

Milestone A2e quantified the robustness of the canonical `max_vorticity` center estimator under additive Gaussian noise.

Observed operating envelope:

| Noise Level | Mean Center Error | Mean Cφ |
|-------------|------------------:|---------:|
| 0%          | 0.71 units        | 0.9995 |
| 5%          | 3.01 units        | 0.9933 |
| 10%         | 3.79 units        | 0.9876 |
| 20%         | 31.69 units       | 0.8076 |

The benchmark demonstrates a sharp transition between 10% and 20% noise.

#### Safe Operating Envelope
The estimator is considered reliable when:
- Estimated noise level is approximately ≤10% of the field standard deviation.
- Center error remains below approximately 5 grid units.
- Expected Cφ degradation remains below approximately 0.02.

#### Failure Mode
For sufficiently noisy velocity fields (approximately ≥20% in the A2e benchmark), maximum-vorticity estimation may become unstable. In this regime, the algorithm may preferentially identify high-frequency noise gradients rather than the physical vortex core, producing large center errors and substantial degradation of Cφ.

This failure is a preprocessing limitation rather than a limitation of the frozen Cφ operator itself. Notably, the operator **fails gracefully**: as center error becomes large, Cφ asymptotically approaches the intrinsic background null-response level (~0.64) rather than becoming numerically unstable.

#### Recommended Mitigation
When data are expected to contain substantial high-frequency noise (for example, raw observations or coarse-resolution products), a mild spatial smoothing filter (typically a 3×3 or 5×5 Gaussian filter) **should** be applied before computing vorticity for center estimation.

The smoothing operation is used **only** for estimating the reference center. After the center has been identified, the frozen TRACEBIND operator shall be evaluated using the original, unsmoothed velocity fields. This preserves the mathematical integrity of the frozen descriptor while improving the robustness of the preprocessing stage.

### Real-Data Robustness (Milestone C Empirical Finding)
While synthetic benchmarks showed high sensitivity to center displacement, application to real ERA5 atmospheric fields demonstrates that realistic estimation errors (1–3 grid cells, ~30–80 km) produce bounded, non-catastrophic changes in Global $C_\phi$ ($\Delta C_\phi < 0.07$). The broad spatial extent of real atmospheric circulation naturally averages minor displacement errors, making this preprocessing contract highly robust for operational use.


Empirical evidence (A2d, double\_vortex case):

\- Geometric center → Cφ = 0.5378 (measures "whole system" coherence)

\- Max vorticity → Cφ = 0.6479 (measures "strongest vortex" coherence)



These are \*\*different scientific quantities\*\*, both physically valid. The choice must be explicit and documented.



\### Alternative Estimators (see CENTER\_ESTIMATION\_TAXONOMY.md)

\- \*\*Geometric center:\*\* For jet streams, frontal shear, or when no dominant vortex exists

\- \*\*Local window center:\*\* For regional analysis within a larger domain

\- \*\*Multi-center analysis:\*\* For systems with multiple comparable vortices (future derived procedure)

\- \*\*User-supplied:\*\* For controlled experiments with known centers



\### Mandatory Provenance

The selected center-estimation method \*\*must always be recorded\*\* in the output provenance, including:

\- Method name (e.g., "max\_vorticity", "geometric\_center")

\- Estimated center coordinates (x\_c, y\_c)

\- Maximum |ζ| value at the estimated center

\- Justification for method selection



\---



\## Rule 3: Variable Naming

The loader must explicitly map ERA5 variables to the operator's expected inputs:

\- Zonal wind: `u` (or `u10` for surface)

\- Meridional wind: `v` (or `v10` for surface)

\- Coordinates: `latitude`, `longitude` (or projected `x`, `y`)



\---



\## Rule 4: Provenance Capture

Every preprocessing run must record:

\- Input file SHA-256 hash

\- Grid dimensions and physical bounds

\- Estimated center coordinates (x\_c, y\_c)

\- Center estimation method used

\- Maximum absolute vorticity value at the estimated center

\- Timestamp and software versions



This ensures that any future researcher can exactly reproduce the center estimation and resulting Cφ score.

