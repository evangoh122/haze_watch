"""Dataset provenance registry.

Every pipeline run appends a record (source, license, treatment, timestamps, row
count, content checksum) to ``data/metadata/registry.json`` so that any output can
be traced back to its inputs. Treatment must be ``real`` or ``synthetic-fixture``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from . import TOOL_NAME, __version__
from .io import read_json, sha256_file, write_json

REGISTRY_FILENAME = "registry.json"

Treatment = Literal["real", "real-restricted", "synthetic-fixture", "derived-unverified"]


def derive_treatment(*inputs: str | bool | None) -> Treatment:
    """Combine input treatments for a derived dataset.

    Precedence (conservative, first match wins):

    - Any synthetic input (``"synthetic-fixture"`` or ``True`` fixture flag)
      makes the output ``"synthetic-fixture"``.
    - Any licence-restricted input (``"real-restricted"``) keeps the output
      ``"real-restricted"`` - derived data inherits the restriction.
    - Any unknown input (``None`` / unrecognized), or no inputs at all, makes
      the output ``"derived-unverified"`` - never silently ``"real"``.
    - Otherwise the output is ``"real"``.

    This keeps the provenance registry consistent with the run summaries:
    derived outputs must never claim ``real`` when fixture inputs were used.
    """
    values = []
    for value in inputs:
        if isinstance(value, bool):
            values.append("synthetic-fixture" if value else "real")
        else:
            values.append(value)
    if not values:
        return "derived-unverified"
    if any(v == "synthetic-fixture" for v in values):
        return "synthetic-fixture"
    if any(v == "real-restricted" for v in values):
        return "real-restricted"
    if any(v not in ("real",) for v in values):
        return "derived-unverified"
    return "real"


def register_dataset(
    metadata_dir: Path,
    *,
    dataset_id: str,
    name: str,
    source: str,
    license: str,
    treatment: Treatment,
    path: Path,
    row_count: int,
    observation_start: str | None = None,
    observation_end: str | None = None,
    vintage: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Append a provenance record for a written dataset file."""
    entry: dict[str, Any] = {
        "dataset_id": dataset_id,
        "name": name,
        "source": source,
        "license": license,
        "treatment": treatment,
        "path": str(path).replace("\\", "/"),
        "row_count": row_count,
        "observation_start": observation_start,
        "observation_end": observation_end,
        "vintage": vintage,
        "checksum_sha256": sha256_file(path) if path.exists() else None,
        "acquired_at": datetime.now(UTC).isoformat(),
        "generated_by": f"{TOOL_NAME} {__version__}",
        "notes": notes,
    }

    registry_path = metadata_dir / REGISTRY_FILENAME
    registry: list[dict[str, Any]] = []
    if registry_path.exists():
        existing = read_json(registry_path)
        registry = existing if isinstance(existing, list) else existing.get("datasets", [])

    # Replace any previous record for the same dataset_id (latest run wins).
    registry = [e for e in registry if e.get("dataset_id") != dataset_id]
    registry.append(entry)
    write_json(registry, registry_path)
    return entry


def read_registry(metadata_dir: Path) -> list[dict[str, Any]]:
    registry_path = metadata_dir / REGISTRY_FILENAME
    if not registry_path.exists():
        return []
    existing = read_json(registry_path)
    return existing if isinstance(existing, list) else existing.get("datasets", [])
