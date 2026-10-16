"""Ask DeepSeek (or any OpenAI-compatible LLM) to review code changes.

Usage:
    LLM_API_KEY=sk-... uv run --package haze-watch-backend \
        python scripts/deepseek_review.py frontend/src/lib/stressTest.ts

Reads the listed files, sends them with a strict review prompt (correctness,
data-policy compliance, test gaps), and prints the findings. The model's output
is advisory - apply only what holds up against the codebase.

Requires LLM_BASE_URL + LLM_API_KEY (see .env.example / docs/llm.md).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REVIEW_PROMPT = """\
You are reviewing code in a geospatial climate-risk research prototype.
Project rules: all companies/financial data must be labeled synthetic; hazard
scores are never PDs; hotspot counts are not burned area or causation; no claims
about real companies; every quantitative output must be traceable to a formula.

Review the code below and report ONLY:
1. Correctness bugs (wrong math, edge cases, silent failures)
2. Violations of the project rules above
3. Missing test coverage for risky logic
Be specific (file: what breaks). If nothing is wrong, say so briefly.
"""


def main(argv: list[str]) -> int:
    base_url = os.environ.get("LLM_BASE_URL", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    if not base_url or not api_key:
        print("DeepSeek review NOT RUN: LLM_BASE_URL / LLM_API_KEY are not set.")
        print("Set them in .env (see .env.example) and re-run this command.")
        return 2

    paths = [Path(p) for p in argv]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f"no such files: {missing}")
        return 1

    bundle = "\n\n".join(
        f"### FILE: {p}\n```\n{p.read_text(encoding='utf-8')}\n```" for p in paths
    )

    import httpx

    response = httpx.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": REVIEW_PROMPT},
                {"role": "user", "content": bundle},
            ],
            "max_tokens": 1500,
            "temperature": 0.0,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    reply = response.json()["choices"][0]["message"]["content"]
    print(f"=== DeepSeek ({model}) review ===")
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
