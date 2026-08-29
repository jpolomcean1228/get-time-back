"""Worker — one background cycle: score, plan, learn, critique, brief.

What a scheduler calls (cadence wake) or an event handler triggers. It turns the
day's candidate moves into a ranked, self-critiqued brief that separates 'decide
now' from 'wait for the brief' — applying learned prefs (threshold, suppression,
preferred edits) and time-to-event urgency before ranking. A genuine leave-now
still interrupts even for a kind you usually wave off.
"""
from __future__ import annotations

from . import critic, planner, urgency, value
from .base import AgentBrief

_TIME_CRITICAL = ("now", "soon")


def _headline(vs, interrupt_count, brief_count) -> str:
    return (f"Reclaim {vs.reclaimable} min, protect {vs.presence_protected} for what "
            f"matters. {interrupt_count} need a decision now; {brief_count} can wait "
            f"for the brief.")


def run_cycle(tasks, presence, prefs=None, now_min=None) -> AgentBrief:
    if now_min is None:
        now_min = urgency.now_minutes()
    interrupt_min = prefs.interrupt_min if prefs else planner._INTERRUPT_MIN
    suppressed = prefs.suppressed_kinds if prefs else frozenset()
    rejected = prefs.rejected_ids if prefs else frozenset()
    preferred = prefs.preferred_edits if prefs else {}

    vs = value.score(tasks, presence)
    sugg = planner.build_suggestions(tasks, presence, interrupt_min, now_min, preferred)
    sugg = [s for s in sugg if s.id not in rejected]     # don't re-surface a hard no
    for s in sugg:
        # a kind you wave off never interrupts — unless it's genuinely time-critical
        if s.kind in suppressed and s.urgency not in _TIME_CRITICAL:
            s.interrupt = False
    sugg = planner.rank(sugg)

    notes = critic.critique(tasks, presence, sugg)
    interrupt_count = sum(1 for s in sugg if s.interrupt)
    brief_count = len(sugg) - interrupt_count
    return AgentBrief(headline=_headline(vs, interrupt_count, brief_count), score=vs,
                      suggestions=sugg, critique=notes,
                      interrupt_count=interrupt_count, brief_count=brief_count)
