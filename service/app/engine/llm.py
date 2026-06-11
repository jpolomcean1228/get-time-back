"""The LLM estimator.

First-pass cold-start estimates from Claude. Used only when ANTHROPIC_API_KEY
is set; on any failure (no key, no package, bad response) it transparently
falls back to the rules estimator so the service never hard-fails.

This is the component that, in production, gets continuously corrected by the
learned layer as real actuals accumulate.
"""
from __future__ import annotations

import json
import os

from .base import Estimate, Task
from .levers import LEVERS
from .rules import RulesEstimator

_MODEL = os.environ.get("GTB_MODEL", "claude-sonnet-4-6")

_SYSTEM = (
    "You estimate the true time cost of a single to-do item. Account for hidden "
    "cost: travel, waiting/passive time, and the focus it fragments around it. "
    "Then pick the single highest-leverage move to shorten it. "
    "Reply with ONLY a JSON object, no preamble, no markdown fences, with keys: "
    "category (string), active (int minutes hands-on), wait (int minutes passive), "
    "travel (int minutes door-to-door), frag (int minutes of focus shattered around it), "
    "lever (one of: eliminate, automate, delegate, batch, defer, overlap, protect), "
    "why (one short sentence in the user's terms). "
    "Use lever 'protect' only for relationship/presence time that should be defended, never compressed."
)


class LLMEstimator:
    def __init__(self, fallback: RulesEstimator | None = None):
        self._fallback = fallback or RulesEstimator()
        self._client = None
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            try:
                import anthropic  # lazy: only needed on the LLM path
                self._client = anthropic.Anthropic(api_key=key)
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def estimate(self, task: Task) -> Estimate:
        if not self._client:
            return self._fallback.estimate(task)
        try:
            msg = self._client.messages.create(
                model=_MODEL,
                max_tokens=300,
                system=_SYSTEM,
                messages=[{"role": "user", "content": f'Task: "{task.raw}"'}],
            )
            text = "".join(
                block.text for block in msg.content if getattr(block, "type", "") == "text"
            ).strip()
            text = text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            lever = data.get("lever", "defer")
            if lever not in LEVERS:
                lever = "defer"
            return Estimate(
                title=task.title, when=task.when,
                category=str(data.get("category", "task")),
                active=int(data.get("active", 30)),
                wait=int(data.get("wait", 0)),
                travel=int(data.get("travel", 0)),
                frag=int(data.get("frag", 0)),
                lever=lever, why=str(data.get("why", "")),
                confidence=0.0, source="llm",
            )
        except Exception:
            # any hiccup -> deterministic baseline, never a 500
            return self._fallback.estimate(task)
