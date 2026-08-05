\# Proposal A1: Test the Existing TRACEBIND Framework on Atmospheric Layers



\*\*Milestone:\*\* A  

\*\*Status:\*\* Draft / Algorithm Frozen  

\*\*Date:\*\* 2026-07-30  



\## 1. Purpose

To evaluate whether the \*existing, frozen\* TRACEBIND descriptor framework (as defined in `FROZEN\_ALGORITHM.md`) can process 2D atmospheric reanalysis slices and produce stable, reproducible descriptor fields across adjacent pressure levels, without any modification to the underlying mathematics.



\## 2. Inputs

\- \*\*Data Source:\*\* ERA5 Reanalysis (via `data/era5/`).

\- \*\*Variables:\*\* Zonal wind (`u`), Meridional wind (`v`).

\- \*\*Domain:\*\* A bounded historical case study (e.g., a specific 48-hour window over a region with known organized atmospheric flow).

\- \*\*Levels:\*\* At least two adjacent pressure levels (e.g., 850 hPa and 700 hPa).



\## 3. Outputs

\- 2D NumPy arrays of TRACEBIND descriptor values (specifically $C\_\\phi$) for each pressure level.

\- Diagnostic plots: Side-by-side visualizations of the raw atmospheric vector field, the TRACEBIND descriptor field, and a Fourier-phase-scrambled null model field.

\- A quantitative correlation metric (e.g., Pearson/Spearman) between the descriptor fields of adjacent levels.



\## 4. Assumptions

1\. The 2D spatial resolution of ERA5 (\~31km) is sufficient to resolve the gradients required by the frozen TRACEBIND mathematics.

2\. \*\*Coordinate Mapping:\*\* Because the frozen `compute\_phase\_coherence` function defaults to index-based coordinates if `X` and `Y` are not provided, the preprocessing pipeline \*must\* explicitly generate and pass physical coordinate grids to ensure the tangential alignment is computed relative to a physically meaningful atmospheric center.

3\. We are evaluating \*independent\* 2D slices. No 3D vertical interpolation or modification of the 2D math is permitted in this milestone.



\## 5. Complexity \& Constraints

\- \*\*Time Complexity:\*\* $O(N)$ per slice for the spatial gradient and dot-product operations. Must process a 48-hour, 6-hourly sequence in under 2 minutes on standard hardware.

\- \*\*Memory:\*\* Must operate on chunks to avoid loading entire global ERA5 datasets into RAM.



\## 6. Validation Strategy (Sanity Checks)

Before accepting any output, the code must pass these automated checks:

1\. \*\*Null Model Test:\*\* Running the descriptor on a Fourier-phase-scrambled version of the input must yield a $C\_\\phi$ distribution matching the Phase 8 baseline (\~0.79 mean for random noise), validating that the metric behaves as characterized.

2\. \*\*Uniform Flow Test:\*\* Running the descriptor on a uniform, constant-value vector field must return a $C\_\\phi$ near 0.0 (relative to the grid center).

3\. \*\*Reproducibility:\*\* Setting `np.random.seed(42)` and running the pipeline twice must yield bitwise-identical outputs.



\## 7. Critical Co-Reviewer Questions for this Milestone

1\. \*Did we drift?\* Are we just building a visualization pipeline, or are we rigorously comparing the output to a null model?

2\. \*False Positive Risk:\* Could aggressive smoothing or interpolation of ERA5 data artificially inflate the descriptor score? (Mitigation: Use raw, native-grid ERA5 data).

3\. \*False Negative Risk:\* Could a mismatch in coordinate systems break the center-relative calculation? (Mitigation: Explicitly document and test the `X`, `Y` grid generation in preprocessing).

4\. \*If this fails:\* We will learn that the 2D TRACEBIND framework is highly sensitive to the specific vertical sampling or coordinate mapping of reanalysis data, and we will document this limitation before considering any mathematical revisions.

