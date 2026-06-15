"""Presence planner — the values loop.

Takes the day's reclaimable-minutes budget and the user's stated values, and
proposes protected blocks: it spends reclaimed time on what matters, in
priority order, until the budget runs out. Whatever's left is "banked" rather
than silently refilled. Each block is a confirmable, defendable action — the
"protect" lever promoted to a first-class output.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..actions.base import BLOCK_TIME, Action
from ..household.timemap import fmt, parse_clock
from .values import Value


@dataclass
class PresenceBlock:
    value_id: str
    label: str
    minutes: int
    when: str            # human, e.g. "8:00pm"
    start: int
    end: int
    action: Action


@dataclass
class PresencePlan:
    reclaimable: int
    allocated: int
    banked: int
    blocks: list[PresenceBlock]


def _protect_action(v: Value, start: int, end: int) -> Action:
    return Action(
        id=f"protect:{v.id}", type=BLOCK_TIME, lever="protect",
        label=f"Protect \u201C{v.label}\u201D",
        detail=f"Fence {v.minutes} min at {fmt(start)} for \u201C{v.label}\u201D "
               f"and defend it from anything else landing there.",
        start_min=start, end_min=end,
    )


class PresencePlanner:
    def plan(self, reclaimable: int, values: list[Value]) -> PresencePlan:
        budget = reclaimable
        allocated = 0
        blocks: list[PresenceBlock] = []
        for v in values:
            if budget >= v.minutes:        # only fund whole blocks
                start = parse_clock(v.when)
                end = start + v.minutes
                blocks.append(PresenceBlock(
                    value_id=v.id, label=v.label, minutes=v.minutes,
                    when=fmt(start), start=start, end=end,
                    action=_protect_action(v, start, end),
                ))
                budget -= v.minutes
                allocated += v.minutes
        return PresencePlan(reclaimable=reclaimable, allocated=allocated,
                            banked=budget, blocks=blocks)
