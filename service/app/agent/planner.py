"""Planner — candidate moves into ranked suggestions.

Optimize + suggest: one suggestion per actionable move. Each earns an interrupt
in one of two ways — its time value clears the (learned) threshold, OR it's
time-critical (a leave-by moment has arrived). Ranked by value-per-interruption.
Each suggestion carries a stable signature (id) so feedback survives across
cycles, plus the volatile confirm-action id. Learned edit preferences are
surfaced in the detail so the agent reflects what you keep changing.
"""
from __future__ import annotations

import re

from . import urgency
from .base import Suggestion

_INTERRUPT_MIN = 45   # default; feedback can raise this per person


def _sig(kind: str, key: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")[:40]
    return f"{kind}:{slug}"


def _pref_note(sig, preferred_edits):
    val = (preferred_edits or {}).get(sig)
    return f" (you usually change this to {val})" if val else ""


def build_suggestions(tasks, presence, interrupt_min: int = _INTERRUPT_MIN,
                      now_min=None, preferred_edits=None):
    out = []
    if presence:
        for b in presence.blocks:
            sig = _sig("protect", b.value)
            out.append(Suggestion(
                id=sig, kind="protect", title=f"Protect \u201C{b.value}\u201D",
                detail=f"Fence {b.minutes} min at {b.when} and defend it." + _pref_note(sig, preferred_edits),
                value_minutes=b.minutes, urgency="today",
                interrupt=b.minutes >= interrupt_min, action_id=b.action.id))

    for t in tasks:
        if not t.action or t.kind == "presence":
            continue
        urg, leave_by, override = ("flexible", None, False)
        if now_min is not None:
            urg, leave_by, override = urgency.assess(t.when, t.travel, now_min)

        if t.coordination:
            sig = _sig("handoff", t.title)
            detail = t.coordination.reason
            if override and leave_by:
                detail += f" \u2014 leave by {leave_by}."
            out.append(Suggestion(
                id=sig, kind="handoff", title=t.action.label,
                detail=detail + _pref_note(sig, preferred_edits),
                value_minutes=t.reclaim,
                urgency=(urg if override else "today"),
                interrupt=override or t.reclaim >= interrupt_min, action_id=t.action.id))
        elif t.reclaim > 0:
            sig = _sig("reclaim", t.title)
            detail = t.why
            if override and leave_by:
                detail += f" \u2014 leave by {leave_by}."
            out.append(Suggestion(
                id=sig, kind="reclaim", title=f"{t.action.label} \u2014 {t.title}",
                detail=detail + _pref_note(sig, preferred_edits),
                value_minutes=t.reclaim,
                urgency=(urg if override else "flexible"),
                interrupt=override, action_id=t.action.id))
    return out


def rank(suggestions):
    return sorted(suggestions, key=lambda s: (not s.interrupt, -s.value_minutes))
