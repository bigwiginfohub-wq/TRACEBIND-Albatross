\# Retrieval Experiment — Frozen Components



\## Step 1: Descriptor Database — FROZEN

\- \*\*Version:\*\* R1.0

\- \*\*Script:\*\* `01\_build\_descriptor\_database.py`

\- \*\*Output:\*\* `outputs/descriptor\_database.csv`, `outputs/descriptor\_database.json`

\- \*\*Operator Hash:\*\* `02732f08923752fa274bb490311929b2fc88cfc3826ebe59caecb4bab881e5cd`

\- \*\*Date Frozen:\*\* 2026-07-31



\### Descriptor Schema (12 retrieval features + metadata)

\*\*Retrieval descriptors:\*\*

\- global\_c\_phi

\- max\_vorticity

\- center\_vorticity

\- max\_wind\_speed

\- mean\_wind\_speed

\- mean\_local\_c\_phi

\- std\_local\_c\_phi

\- min\_local\_c\_phi

\- max\_local\_c\_phi

\- p25\_local\_c\_phi

\- p75\_local\_c\_phi

\- median\_center\_distance



\*\*Metadata (excluded from retrieval):\*\*

\- filename

\- center\_x\_km

\- center\_y\_km

\- n\_valid\_windows

\- extraction\_status

\- failure\_reason



\### Freeze Policy

No descriptor additions, removals, or modifications unless a verified bug is discovered.

Any change requires a new version tag (e.g., R1.1, R2.0) and re-running Step 1.

