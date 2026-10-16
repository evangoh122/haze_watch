"""Fetch pipeline history from the Hugging Face dataset for local use.

Lets the analyst chat layer (and any agent) reference the durable history store
without a local pipeline run: downloads one run from ``runs/<run_id>/`` and
unpacks it into ``data/hf_history/`` with the same layout as the local ``data/``
directory (``processed/``, ``metadata/``, ``MANIFEST.json``) so
``LLM_DATA_DIR`` grounding works unchanged.

Usage:
    uv run python scripts/fetch_history_from_hf.py                    # latest run
    uv run python scripts/fetch_history_from_hf.py --run 20261016T120000Z
    uv run python scripts/fetch_history_from_hf.py --dest data/hf_history

The chat layer grounds on ``LLM_DATA_DIR``; point it at ``data/hf_history`` to
answer from historical runs.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _available_runs(files: list[str]) -> list[str]:
    return sorted({p.split("/")[1] for p in files if p.startswith("runs/") and p.count("/") >= 2})


def fetch_history(dataset: str, dest: Path, run: str = "latest") -> dict:
    from huggingface_hub import HfApi, snapshot_download

    api = HfApi()
    run_ids = _available_runs(api.list_repo_files(dataset, repo_type="dataset"))
    if not run_ids:
        raise SystemExit(
            f"no runs/<run_id>/ entries in dataset {dataset} - nothing to fetch "
            "(legacy flat layout predates run history; re-export first)"
        )
    run_id = run_ids[-1] if run == "latest" else run
    if run_id not in run_ids:
        raise SystemExit(f"unknown run {run!r}; available: {run_ids}")

    local = Path(
        snapshot_download(
            repo_id=dataset,
            repo_type="dataset",
            local_dir=str(dest),
            allow_patterns=[f"runs/{run_id}/*"],
        )
    )
    run_dir = local / "runs" / run_id
    if not run_dir.is_dir():
        raise SystemExit(f"run {run_id} did not download to {run_dir}")

    # Unpack the run into dest with data/-style layout (processed/, metadata/).
    dest.mkdir(parents=True, exist_ok=True)
    for item in run_dir.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    shutil.rmtree(local / "runs")

    manifest_path = dest / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    registry_path = dest / "metadata" / "registry.json"
    registry = (
        json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
    )
    if isinstance(registry, dict):
        registry = registry.get("datasets", [])

    print(f"history fetched: run {run_id} -> {dest}")
    for entry in registry:
        print(
            f"  {entry.get('dataset_id')}: treatment={entry.get('treatment')}, "
            f"rows={entry.get('row_count')}"
        )
    if manifest.get("excluded_not_allowlisted"):
        print(f"  note: excluded upstream (not allowlisted): {manifest['excluded_not_allowlisted']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="egoh33/haze-watch-historical")
    parser.add_argument("--dest", default=str(REPO_ROOT / "data" / "hf_history"))
    parser.add_argument(
        "--run",
        default="latest",
        help="run id under runs/ to fetch, or 'latest' (default)",
    )
    args = parser.parse_args()
    fetch_history(args.dataset, Path(args.dest), args.run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
