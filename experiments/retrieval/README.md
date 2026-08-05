\# TRACEBIND Retrieval Experiment



An information-retrieval pipeline for atmospheric analogs based on TRACEBIND descriptors.



\## Pipeline



| Step | Script | Purpose | Status |

|------|--------|---------|--------|

| 1 | `01\_build\_descriptor\_database.py` | Extract descriptors from ERA5 cases | ✅ Frozen (R1.0) |

| 2 | `02\_build\_pca\_database.py` | Build PCA representation space | ▶️ In progress |

| 3 | `03\_build\_tracebind\_index.py` | Build retrieval index (nearest neighbors) | ⏳ Pending |

| 4 | `04\_compare\_against\_baseline.py` | Evaluate against PCA baseline | ⏳ Pending |



\## Directory Layout



retrieval/

├── README.md # This file

├── FROZEN.md # Frozen component registry

├── 01\_build\_descriptor\_database.py

├── 02\_build\_pca\_database.py

├── 03\_build\_tracebind\_index.py

├── 04\_compare\_against\_baseline.py

├── outputs/ # Intermediate data (CSV, JSON)

├── models/ # Trained models (scaler.pkl, pca.pkl)

└── reports/ # Evaluation summaries





\## Engineering vs. Science



\- \*\*Phase A (this pilot):\*\* 20-case cohort. Engineering validation only. Does the pipeline run?

\- \*\*Phase B (future):\*\* 100–200+ cases. Scientific evaluation. Does TRACEBIND retrieve meaningful analogs better than PCA?



No scientific claims are made from Phase A outputs.

