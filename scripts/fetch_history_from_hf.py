"""Fetch pipeline history from the Hugging Face dataset for local use.

Lets the analyst chat layer (and any agent) reference the durable history store
without a local pipeline run: downloads the dataset snapshot into
``data/hf_history/`` and reports what the provenance ledger says about it.

Usage:
    uv run python scripts/fetch_history_from_hf.py
    uv run python scripts/fetch_history_from_hf.py --dataset egoh33/haze-watch-historical

The chat layer grounds on ``LLM_DATA_DIR``; point it at ``data/hf_history`` (or
copy the fetched files into ``data/processed``) to answer from historical runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def fetch_history(dataset: str, dest: Path) -> dict:
    from huggingface_hub import snapshot_download

    local = snapshot_download(repo_id=dataset, repo_type="dataset", local_dir=str(dest))
    manifest_path = Path(local) / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    registry_path = Path(local) / "registry.json"
    registry = (
        json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
    )
    print(f"history fetched -> {local}")
    for entry in registry:
        print(
            f"  {entry.get('dataset_id')}: treatment={entry.get('treatment')}, "
            f"rows={entry.get('row_count')}"
        )
    if manifest.get("excluded_real_restricted"):
        print(f"  note: restricted geometry excluded upstream: {manifest['excluded_real_restricted']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="egoh33/haze-watch-historical")
    parser.add_argument("--dest", default=str(REPO_ROOT / "data" / "hf_history"))
    args = parser.parse_args()
    fetch_history(args.dataset, Path(args.dest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
