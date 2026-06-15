"""Coordination matcher — the engine of the household layer.

Given a delegable task and the window it needs, find the best member to hand it
to: someone who consents, is free then, and (for driving tasks) can drive. This
is what turns a generic "delegate" suggestion into a targeted carpool swap or
errand hand-off across two named people — the Phase 4 success metric.
"""
from __future__ import annotations

from dataclasses import dataclass

from .consent import Consent
from .roster import Household, Member
from .timemap import TimeMap, fmt


@dataclass
class Coordination:
    helper: Member
    window: str          # human window, e.g. "5:30pm–6:35pm"
    reason: str          # why this person
    kind: str            # "swap" | "handoff"


class Matcher:
    def __init__(self, household: Household, timemap: TimeMap, consent: Consent):
        self._h = household
        self._t = timemap
        self._c = consent

    def find(self, start: int, end: int, needs_driving: bool, recurring: bool) -> Coordination | None:
        """Best eligible helper for [start, end], or None.

        Eligibility, in order: consents (shares + accepts) -> free in window ->
        can drive if the task requires it. Returns the first eligible member.
        """
        for m in self._h.others():
            if not self._c.is_candidate(m.id):
                continue                       # privacy gate
            if needs_driving and not m.can_drive:
                continue
            if not self._t.is_free(m.id, start, end):
                continue
            window = f"{fmt(start)}\u2013{fmt(end)}"
            drive = " and can drive" if needs_driving else ""
            reason = f"{m.name} is free {window}{drive}, and accepts hand-offs."
            return Coordination(helper=m, window=window, reason=reason,
                                kind="swap" if recurring else "handoff")
        return None
