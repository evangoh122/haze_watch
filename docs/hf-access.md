# Hugging Face access (for reviewers)

How an external reviewer (e.g. DeepSeek) can gain read access to the Haze Watch
Hugging Face artifacts to verify export/governance claims at the remote level —
the standing review caveat has been "I cannot see the HF remote".

## What is on Hugging Face

| Thing | URL | Visibility |
|---|---|---|
| History dataset | `https://huggingface.co/datasets/egoh33/haze-watch-historical` | **private** (owner: `egoh33`) |
| App Space | `https://huggingface.co/spaces/egoh33/haze-watch` | public since 2026-10-16 (no secrets set; deterministic fallback) |

The dataset holds the pipeline history export (processed outputs + provenance
`registry.json` + `MANIFEST.json`). The manifest's `geometry_note` and
`excluded_not_allowlisted` fields document exactly what leaves the machine and
what never does (`plantation_polygons.parquet`, real-restricted concession
geometry). The evangoh.com site Space `egoh33/Auditable-Filing-QA` is unrelated
to this review.

## Getting access — choose one

### Option A — read collaborator (recommended for reviewers)

1. Reviewer: create a free account at `huggingface.co/join` and send the HF
   username to the project owner.
2. Owner (`egoh33`): dataset repo → **Settings → Manage access → Add
   collaborator** → grant **read** role.

### Option B — fine-grained read-only token

1. Owner: **Settings → Access Tokens → New fine-grained token** → repositories:
   `egoh33/haze-watch-historical` only → permission **Read**.
2. Hand it to the reviewer through a secret channel. Never paste tokens into
   chat transcripts, PRs, issues, or committed files. Revoke after the review.

Both routes give read-only access. Nothing in this review requires write access.

## Authenticating on the reviewer machine

```powershell
# PowerShell (session-only)
$env:HF_TOKEN = "hf_..."
```

```bash
# bash / CI
export HF_TOKEN=hf_...
```

or interactively: `huggingface-cli login`. `huggingface_hub` is declared in the
root `pyproject.toml` dev group, so `uv sync` installs it.

## Verifying the remote (copy-paste)

```python
from huggingface_hub import HfApi, hf_hub_download
import json
import pandas as pd

api = HfApi()
files = sorted(api.list_repo_files("egoh33/haze-watch-historical", repo_type="dataset"))
print(files)
run_ids = sorted({p.split("/")[1] for p in files if p.startswith("runs/") and p.count("/") >= 2})
run_id = run_ids[-1]  # latest run; each run is runs/<run_id>/{processed,metadata,MANIFEST.json}
print("latest run:", run_id)

d = pd.read_parquet(hf_hub_download("egoh33/haze-watch-historical", f"runs/{run_id}/processed/exposure.parquet", repo_type="dataset"))
print(d.columns.tolist())
# Second-pass hardening: no exact area recovery, no full-precision distances
assert "centroid_lon" not in d.columns and "centroid_lat" not in d.columns
assert "area_ha" not in d.columns
assert "detection_density_per_1000ha" not in d.columns   # count/density*1000 recovered exact area
assert "nearest_hotspot_km_30d" not in d.columns          # raw name = full precision; _r is rounded
assert "nearest_hotspot_km_r" in d.columns

m = json.load(open(hf_hub_download("egoh33/haze-watch-historical", f"runs/{run_id}/MANIFEST.json", repo_type="dataset"), encoding="utf-8"))
print(m["geometry_note"])
print(m["excluded_not_allowlisted"])
print("OK: remote matches the reduced-export claim")
```

Expected `runs/<run_id>/processed/exposure.parquet` columns (2026-10-16):

```
polygon_id, boundary_type, hotspot_count_in_polygon_30d, hotspot_count_near_30d,
caveat, centroid_lon_r (1 dp ~11 km), centroid_lat_r, nearest_hotspot_km_r
(whole km), area_ha_bucket (500 ha bins, min 500)
```

## If the reviewer environment has no network

- `data/hf_export/` is the exact local mirror of what was uploaded (each run
  under `data/hf_export/runs/<run_id>/`); `uv run python
  scripts/export_history_to_hf.py` rebuilds the current run (dry run, no
  upload) and prints the manifest summary.
- Maintainer-side remote verification was run 2026-10-16 (runs/ layout):
  `exposure.parquet` columns match the list above, `detection_density_per_1000ha`
  absent, `nearest_hotspot_km_30d` (raw) absent, `plantation_polygons.parquet`
  not in the remote file list.

## Agent runtime access (same credentials)

`scripts/fetch_history_from_hf.py` pulls the history into `data/hf_history/`,
and the analyst chat agent grounds on it via `LLM_DATA_DIR=data/hf_history`.
Because the dataset is private, any cold-cache machine (CI, a fresh box) needs
`HF_TOKEN` in the environment for the fetch — or the dataset can later be made
public via the export script's opt-in `--public` flag.
