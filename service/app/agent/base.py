"""Agent types — the shape of a background cycle's output."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValueScore:
    reclaimable: int          # minutes the day's moves free up
    presence_protected: int   # minutes routed to what matters
    fragmentation: int        # focus-minutes still shattered (a cost)
    banked: int               # freed minutes deliberately left unspent
    score: float              # weighted objective the agent maximizes


@dataclass
class Suggestion:
    id: str
    kind: str                 # protect | handoff | reclaim | warning
    title: str
    detail: str
    value_minutes: int
    urgency: str              # now | today | flexible
    interrupt: bool           # earns an interrupt vs. batched into the brief
    action_id: str = ""


@dataclass
class AgentBrief:
    headline: str
    score: ValueScore
    suggestions: list[Suggestion] = field(default_factory=list)
    critique: list[str] = field(default_factory=list)
    interrupt_count: int = 0
    brief_count: int = 0
