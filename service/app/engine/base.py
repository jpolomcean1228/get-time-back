"""Core engine types shared by every estimator.

An Estimator turns one task into an Estimate. Different estimators (rules,
LLM, learned) are interchangeable behind this one interface — that is the
seam the whole service is built around.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Task:
    """A single thing on the day, as the user wrote it."""
    raw: str
    title: str
    when: str = ""  # optional trailing time, e.g. "5:30"


@dataclass
class Estimate:
    """The enriched view of a task: its true cost and the smarter move."""
    title: str
    when: str
    category: str
    active: int          # hands-on minutes
    wait: int            # passive / waiting minutes (laundry, hold music)
    travel: int          # door-to-door travel minutes
    frag: int            # focus minutes shattered around it (placement cost)
    lever: str           # eliminate | automate | delegate | batch | defer | overlap | protect
    why: str             # one-line rationale, in the user's terms
    confidence: float = 0.0  # 0..1, rises as the engine learns from actuals
    source: str = "rules"    # which estimator produced this

    @property
    def total(self) -> int:
        """Wall-clock minutes the task consumes (frag is a separate hidden cost)."""
        return self.active + self.wait + self.travel


class Estimator(Protocol):
    """Anything that can turn a Task into an Estimate."""
    def estimate(self, task: Task) -> Estimate: ...
