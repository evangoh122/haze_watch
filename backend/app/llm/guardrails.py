"""Guardrails for the chat layer.

Enforces the data-policy rules from project_profile.md sections 3 and 10 in both
the system prompt (instruction) and the response (validation). The validation is
deliberately conservative: it flags suspicious claim patterns and the service
appends the research disclaimer on every reply regardless.
"""

from __future__ import annotations

import re

DISCLAIMER = (
    "Research prototype. Companies, financial statements, bank exposures and "
    "insurance policies are entirely synthetic and fictional. Hazard scores are "
    "illustrative baselines - not calibrated probabilities, not validated "
    "forecasts, and not probabilities of default."
)

SYSTEM_PROMPT = """\
You are the analyst assistant inside the Geospatial Climate Risk Intelligence \
Platform, an independent research prototype for banks and insurers.

Hard rules - never break these:
1. All companies, financial statements, bank exposures and insurance policies in \
this platform are ENTIRELY SYNTHETIC and fictional. Whenever you mention one, \
state that it is synthetic.
2. Environmental observations (fire hotspots, weather) are real and sourced. Cite \
the dataset name and its treatment (real / real-restricted / synthetic-fixture) \
whenever you use figures from them.
3. Fire hotspot counts are satellite detections. They are NOT confirmed burned \
area, NOT damage estimates, and NOT evidence of fire causation or of any \
company's responsibility.
4. Hazard scores are NOT probabilities of default, NOT calibrated probabilities, \
NOT validated fire forecasts, and NOT insurance loss estimates. Never convert a \
hazard score into a credit rating, PD, LGD, EAD, premium or reserve.
5. Never make claims about real companies, real banks or real insurers, and never \
suggest that a fictional borrower is a real institution's customer.
6. Ground every quantitative answer in the provided dataset context. If the \
context does not contain the answer, say plainly that the data is not loaded - do \
not estimate or invent numbers.
7. Clearly distinguish observed, derived and illustrative figures. When inputs mix \
real and synthetic data, say so explicitly.
8. Concession geometry is licence-restricted. Do not attempt to reconstruct exact \
boundaries, coordinates or ownership records.
9. Do not provide investment, credit, underwriting or legal advice. The platform \
is a research prototype.
"""

# Claim patterns that violate the rules above when they appear in a reply.
_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"actuarially\s+validated", "actuarially validated claim"),
    (r"validated\s+probability\s+of\s+default", "validated PD claim"),
    (r"\bPD\s*(?:=|of)\s*\d", "numeric PD claim"),
    (r"guarantee[sd]?\b", "guarantee claim"),
    (r"\bproves?\b", "proof claim"),
    (r"is\s+responsible\s+for\s+the\s+fire", "causation/responsibility claim"),
    (r"confirmed\s+burned\s+area", "burned-area confirmation claim"),
]


def validate_response(text: str) -> list[str]:
    """Return a list of guardrail flags (empty when the reply looks compliant)."""
    flags: list[str] = []
    lowered = text.lower()
    for pattern, label in _FORBIDDEN_PATTERNS:
        if re.search(pattern, lowered):
            flags.append(label)
    return flags


def build_messages(user_messages: list[dict], context_text: str) -> list[dict]:
    """Assemble the provider message list: system prompt + grounded context + turns."""
    system = SYSTEM_PROMPT
    if context_text:
        system += "\n\n# Current dataset context (ground truth for your answers)\n" + context_text
    return [{"role": "system", "content": system}, *user_messages]
