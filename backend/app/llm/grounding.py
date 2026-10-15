"""Grounding: turns pipeline outputs into the context block for the chat layer.

Reads the provenance registry and processed datasets written by ``haze-pipelines``
so that answers cite real pipeline state instead of model priors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GroundedContext:
    text: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] | None = None
    registry: list[dict[str, Any]] = field(default_factory=list)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _top_detection_rows(exposure_parquet: Path, limit: int = 5) -> list[str]:
    try:
        import pandas as pd

        df = pd.read_parquet(exposure_parquet)
        top = df.sort_values("hotspot_count_in_polygon_30d", ascending=False).head(limit)
        return [
            (
                f"- {row.polygon_id}: detections_in_polygon_30d="
                f"{int(row.hotspot_count_in_polygon_30d)}, detections_near_30d="
                f"{int(row.hotspot_count_near_30d)}, area_ha={row.area_ha:.0f}"
            )
            for row in top.itertuples()
        ]
    except Exception:  # noqa: BLE001 - any read failure means "no context rows"; never crash the chat layer
        return []


def build_context(data_dir: Path) -> GroundedContext:
    """Build the grounding block from whatever the pipeline has produced."""
    data_dir = Path(data_dir)
    registry_path = data_dir / "metadata" / "registry.json"
    summary_path = data_dir / "processed" / "exposure.summary.json"
    exposure_parquet = data_dir / "processed" / "exposure.parquet"

    registry_raw = _read_json(registry_path) or []
    registry = registry_raw if isinstance(registry_raw, list) else registry_raw.get("datasets", [])
    summary = _read_json(summary_path)

    lines: list[str] = []
    sources: list[dict[str, Any]] = []

    if registry:
        lines.append("## Dataset registry (provenance ledger)")
        for entry in registry:
            lines.append(
                f"- {entry.get('dataset_id')}: treatment={entry.get('treatment')}, "
                f"rows={entry.get('row_count')}, license={entry.get('license')}, "
                f"source={entry.get('source')}"
            )
            sources.append(
                {
                    "dataset_id": entry.get("dataset_id"),
                    "source": entry.get("source"),
                    "treatment": entry.get("treatment"),
                    "license": entry.get("license"),
                }
            )
    else:
        lines.append(
            f"## Dataset registry\n- NO DATASETS REGISTERED (expected at {registry_path}). "
            "Tell the user to run the ingestion pipeline first."
        )

    if summary:
        lines.append("\n## Exposure summary (exposure.summary.json)")
        for key in (
            "as_of",
            "polygons",
            "hotspots_considered",
            "polygons_with_detections",
            "buffer_km",
            "polygon_treatment",
            "hotspot_treatment",
        ):
            if key in summary:
                lines.append(f"- {key}={summary[key]}")
        if summary.get("warning"):
            lines.append(f"- WARNING: {summary['warning']}")
        if summary.get("caveat"):
            lines.append(f"- caveat: {summary['caveat']}")

    top_rows = _top_detection_rows(exposure_parquet)
    if top_rows:
        lines.append("\n## Polygons by detections (top 5 from exposure.parquet)")
        lines.extend(top_rows)

    text = "\n".join(lines)
    return GroundedContext(text=text, sources=sources, summary=summary, registry=registry)
