# Data Layout

| Directory | Contents | Committed? |
|---|---|---|
| `raw/firms/` | NASA FIRMS hotspot downloads (real) | No |
| `raw/weather/` | ERA5 / Open-Meteo observations (real) | No |
| `raw/landcover/` | Copernicus land cover / vegetation (real) | No |
| `raw/peatland/` | Peatland / soil datasets (real) | No |
| `raw/concessions/` | Published concession polygons (real, restricted display) | No |
| `interim/` | Intermediate processing artifacts | No |
| `processed/` | Normalized GeoParquet/Parquet modelling inputs | No |
| `synthetic/` | Generated synthetic commercial/financial data | No (regenerable) |
| `metadata/` | `datasets.yaml` provenance and licensing register | Yes |

Rules:

- Datasets are excluded from git (see root `.gitkeep` placeholders); regenerate with
  `make ingest-firms` etc. and record every acquisition in `metadata/datasets.yaml`.
- Everything under `synthetic/` must be labeled synthetic in the files themselves and
  regenerable from `synthetic/generate.py` with a fixed seed.
- Raw concession geometry must never be exposed publicly in unaggregated form.
