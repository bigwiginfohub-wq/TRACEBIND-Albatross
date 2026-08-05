\# TRACEBIND-Albatross Data Sources



To ensure full reproducibility while keeping the repository lightweight, raw data files are not included in this repository. They can be obtained from their official, authoritative sources:



\## 1. IBTrACS v04r01 (Tropical Cyclone Tracks)

\- \*\*Source:\*\* NOAA National Centers for Environmental Information (NCEI)

\- \*\*File:\*\* `ibtracs.ALL.v04r01.csv`

\- \*\*Direct Download Link:\*\* \[https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ALL.v04r01.csv](https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ALL.v04r01.csv)

\- \*\*Placement:\*\* Save this file to `experiments/retrieval/labels/ibtracs\_ALL.csv`



\## 2. ERA5 Reanalysis Data

\- \*\*Source:\*\* ECMWF Climate Data Store (CDS)

\- \*\*Variables:\*\* 10m u-component of wind, 10m v-component of wind, land-sea mask

\- \*\*Acquisition:\*\* Handled programmatically via the scripts in the `phaseb/` directory using the `cdsapi` Python package.

