\# TRACEBIND-Albatross Reproducibility Audit



\## Pre-Submission Checklist



\### 1. Environment

\- \[x] Python version recorded in RELEASE\_v1.0/versions.txt

\- \[x] All dependency versions recorded

\- \[ ] Virtual environment or requirements.txt created (optional but recommended)



\### 2. Data

\- \[x] 20-case ERA5 cohort accessible at C:\\TRACEBIND-Atmosphere\\phase8\\c2\\raw\\

\- \[x] No data files modified after analysis



\### 3. Code

\- \[x] Frozen operator hash verified: 02732f08923752fa274bb490311929b2fc88cfc3826ebe59caecb4bab881e5cd

\- \[x] All scripts in experiments/ directory are final versions

\- \[x] No TODO comments or debug code remaining



\### 4. Outputs

\- \[x] All JSON reports in outputs/final\_release/

\- \[x] All figures in outputs/final\_release/figures/

\- \[x] Feature CSV saved for supplementary material



\### 5. Manuscript

\- \[ ] Operator hash inserted in Section 2 of Manuscript.md

\- \[ ] All numbers in manuscript match final outputs (e.g., Adj R² = 0.2589, p = 0.719)

\- \[ ] All claims have corresponding evidence

\- \[ ] References complete (TRACEBIND-Atmosphere, ERA5, etc.)



\### 6. Clean Run Test (Optional but Recommended)

\- \[ ] Delete outputs/ directory (keep backup)

\- \[ ] Re-run all experiments from scratch

\- \[ ] Verify all outputs match archived versions

\- \[ ] Confirm no changes to code after final run



\## Audit Date: 2026-07-31

\## Auditor: \[Your Name]

