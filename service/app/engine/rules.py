"""The rules estimator.

A direct port of the Phase 0 classify/enrich logic. It needs no API key, no
network, and no data — so it is both the cold-start baseline and the fallback
whenever the LLM path is unavailable. Never let the service fail in a demo.

The category knowledge it used to hardcode now lives in `profiles.py`
(`fixtures/profiles.json`); this estimator just reads a profile and renders it
as an Estimate. Pass a custom ProfileStore to estimate against a different
table; the default is the process-wide store the /profiles endpoints manage.
"""
from __future__ import annotations

from typing import Optional

from .base import Estimate, Task
from .profiles import ProfileStore, default_profiles


def classify(text: str) -> str:
    """Bucket a task into a category using the default profile table."""
    return default_profiles().classify(text)


class RulesEstimator:
    def __init__(self, profiles: Optional[ProfileStore] = None):
        self._profiles = profiles or default_profiles()

    def estimate(self, task: Task) -> Estimate:
        category = self._profiles.classify(task.raw)
        p = self._profiles.get(category)
        return Estimate(
            title=task.title, when=task.when, category=category,
            active=p.active, wait=p.wait, travel=p.travel, frag=p.frag,
            lever=p.lever, why=p.why, confidence=0.0, source="rules",
        )
