"""Guard: no raw, processed or synthetic data may ever be tracked by git.

Real concession geometry (e.g. BNPB/GFW downloads) is licence-restricted and must
never be committed (docs/data-sources-and-licensing.md). Only documentation and
the provenance ledger under data/metadata/ are allowed.

The same applies to private research data (real company linkage + hand-sourced
financials) under ``private/``: only the schema template may be tracked.

Scans ALL paths (any depth, tracked AND untracked-but-not-ignored), so a stray
``pipelines/data/...`` ledger cannot evade it and a repo with no commits is still
checked. Run locally (``make test``) and in CI. Exits 1 when a restricted file
would enter the repository.
"""

from __future__ import annotations

import subprocess

# Root-anchored exceptions: provenance/docs may be committed.
ALLOWED_PREFIXES = ("data/metadata/", "frontend/src/data/")
ALLOWED_EXACT = {"data/README.md"}

# Private research data (real company linkage + hand-sourced financials) must never
# be tracked either; only the schema template is allowed to be committed.
PRIVATE_ALLOWED = {"private/companies/_template.yaml"}


def _is_private_data(path: str) -> bool:
    return (
        path.startswith("private/companies/") and path not in PRIVATE_ALLOWED
    ) or path.startswith("private/out/")


def _is_allowed(path: str) -> bool:
    return (
        path in ALLOWED_EXACT
        or path.startswith(ALLOWED_PREFIXES)  # code-contained synthetic demo data
        or path.endswith(".gitkeep")
    )


def _is_data_path(path: str) -> bool:
    return any(segment == "data" for segment in path.split("/"))


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"guard skipped: git ls-files failed ({result.stderr.strip()})")
        return 0

    paths = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    forbidden = sorted(
        p
        for p in paths
        if (_is_data_path(p) and not _is_allowed(p)) or _is_private_data(p)
    )

    if forbidden:
        print("GUARD FAILED - restricted data files would enter git:")
        for path in forbidden:
            print(f"  - {path}")
        print("Untrack them (git rm --cached) and keep the files gitignored.")
        return 1

    checked = sum(1 for p in paths if _is_data_path(p))
    print(f"data guard OK: {checked} allowed data file(s) seen, no restricted data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
