\# PHASE B3: Descriptor Extraction ($C\_\\phi$) Protocol



\*\*Version:\*\* 1.0  

\*\*Status:\*\* DRAFT (Pending Freeze)  

\*\*Predecessor:\*\* Phase B2.2 (ERA5 Acquisition \& QC)  

\*\*Successor:\*\* Phase B4 (Statistical Analysis \& Hypothesis Testing)



\---



\## 1. Objective

To deterministically and blindly extract the \*\*mean absolute tangential velocity alignment descriptor\*\* ($C\_\\phi$) for the 300 frozen cases. This phase operates strictly as a blind physics engine; no statistical comparison, grouping, or unblinding of TC vs. Control cases is permitted.



\---



\## 2. Input Artifact \& Contract

The sole scientific input for this phase is the frozen B2.2 primary artifact:

\* \*\*Filename:\*\* `b2.2\_era5\_fields.nc`

\* \*\*SHA256:\*\* `872635f3885917b2fba9f06f74d354e25b955d563dca769bb03a22bde085a3c0`

\* \*\*Dimensions:\*\* `(case=300, y=17, x=17)`

\* \*\*Variables:\*\* `u10`, `v10`, `native\_latitude`, `native\_longitude`

\* \*\*Case Metadata:\*\* `case\_id`, `case\_type`, `case\_timestamp`, `requested\_latitude`, `requested\_longitude`, `center\_grid\_latitude`, `center\_grid\_longitude`



\---



\## 3. Mathematical Definition of $C\_\\phi$

For each case $i \\in \\{1 \\dots 300\\}$, $C\_\\phi^{(i)}$ is the mean absolute alignment of the local ERA5 horizontal wind vector with the local tangential direction over the 30–150 km analysis shell.



$$

C\_\\phi^{(i)} = \\frac{1}{N\_i} \\sum\_{p \\in S\_i} \\left| \\frac{\\vec V\_p \\cdot \\hat e\_{\\theta,p}}{|\\vec V\_p|} \\right|

$$



where:

\* $\\vec V\_p = (u\_p, v\_p)$ is the ERA5 horizontal wind vector at native grid point $p$;

\* $S\_i$ is the set of native grid points satisfying $30 \\text{ km} \\le r\_p \\le 150 \\text{ km}$;

\* $N\_i = |S\_i|$;

\* $|\\vec V\_p| = \\sqrt{u\_p^2 + v\_p^2}$;

\* $\\hat e\_{\\theta,p}$ is the local counterclockwise tangential unit vector.



Because both $\\vec V\_p/|\\vec V\_p|$ and $\\hat e\_{\\theta,p}$ are unit vectors, each pointwise absolute projection lies in $\[0, 1]$. Consequently, every valid case must satisfy:



$$

0 \\le C\_\\phi^{(i)} \\le 1

$$



Any computed value outside this interval constitutes a numerical/QC failure.



\### 3.1 Geometric Center \& Coordinate Convention

\* \*\*Operational Center:\*\* The B2.2 artifact does not provide a `minimum\_pressure\_center` field. Therefore, for this executable B3 protocol, the frozen `requested\_latitude` and `requested\_longitude` are used as the sole geometric center for every case. This is an explicit operationalization of the B3 descriptor and is not inferred from `case\_type`. The same center-selection rule is applied identically to every case.

\* \*\*Bearing ($b\_p$):\*\* The initial great-circle bearing from the center $(\\phi\_c, \\lambda\_c)$ to point $p$ $(\\phi\_p, \\lambda\_p)$, measured clockwise from North.

\* \*\*Tangential Basis:\*\* The counterclockwise tangential unit vector is defined as $\\hat e\_{\\theta,p} = (-\\cos b\_p, \\sin b\_p)$.

\* \*\*Tangential Projection:\*\* The signed tangential velocity at $p$ is $V\_{\\theta,p} = \\vec V\_p \\cdot \\hat e\_{\\theta,p} = -u\_p \\cos b\_p + v\_p \\sin b\_p$.



Thus, $C\_\\phi$ is dimensionless and represents mean absolute tangential alignment rather than mean signed tangential velocity.



\---



\## 4. Strict Blindness Constraint

\*\*CRITICAL:\*\* This script must treat all 300 cases as identical physical inputs. 

\* The extraction algorithm shall not use `case\_type` for any numerical calculation, ordering, filtering, weighting, QC threshold, or failure handling.

\* `case\_type` may be copied verbatim into the output solely as metadata required to preserve case identity; it shall not influence the computed $C\_\\phi$.

\* The script shall not output summary statistics, distributions, or comparative metrics between TCs and Controls.



\---



\## 5. Treatment of Missing/Non-Finite Values \& Zero Wind

Although B2.2 QC guaranteed finite values in the shell, B3 must include defensive checks:

\* If any $u\_p$ or $v\_p$ within the 30–150 km shell is non-finite (NaN or Inf), the case fails QC.

\* \*\*Zero Wind:\*\* If $|\\vec V\_p| = 0$ at any shell grid point $p \\in S\_i$, the case fails QC. The original descriptor is defined pointwise through normalized velocity; a zero vector yields an undefined alignment.

\* If the shell contains zero valid grid points, the case fails QC.

\* Failed cases are logged but do not halt the pipeline for the remaining cases.



\---



\## 6. Velocity Transformation

The `u10` and `v10` variables are used directly as the eastward and northward components of the ERA5 horizontal wind vector. No meteorological wind-vector rotation or regridding is performed. The tangential projection is calculated directly from these components using the bearing-defined tangential basis. The vector magnitude $|\\vec V|=\\sqrt{u^2+v^2}$ is calculated only for the normalization required by the definition of $C\_\\phi$.



\---



\## 7. Output Schema

The script shall generate a single, lightweight CSV file: `b3\_descriptors.csv`.

Columns:

\* `case\_id` (String)

\* `case\_type` (String: "TC" or "Control")

\* `case\_timestamp` (String)

\* `C\_phi` (Float: mean absolute tangential alignment, dimensionless)

\* `shell\_grid\_count` (Integer: $N\_i$, number of native grid points used in the mean)

\* `QC\_Status` (String: "PASSED" or "FAILED")



\---



\## 8. Deterministic Ordering, Hashing, and Preflight Checks

\* The output CSV must preserve the exact case ordering of the input NetCDF (`case = 0` to `299`).

\* \*\*Preflight Hash Check:\*\* The extractor shall verify that the SHA256 of the input `b2.2\_era5\_fields.nc` exactly equals the frozen B2.2 hash specified in Section 2 before processing any case. If the hash does not match, extraction shall abort before producing `b3\_descriptors.csv`.

\* The script shall generate a cryptographic audit manifest (`b3\_audit.json`) containing exactly the following fields:

&#x20; \* `input\_artifact\_sha256`

&#x20; \* `protocol\_sha256`

&#x20; \* `script\_sha256`

&#x20; \* `output\_sha256`

&#x20; \* `git\_commit\_hash`

&#x20; \* `execution\_timestamp\_utc`



\---



\## 9. Freeze Criteria

This protocol is considered frozen when:

1\. This document is committed to Git with a `v1.0-phase-b3-protocol` tag.

2\. The extraction script is written to strictly adhere to these rules.

3\. The script is executed, and the audit manifest confirms 300/300 successful extractions with a valid SHA256 chain.

