"""Urgency — time-to-event (and travel) can force an interrupt.

Value answers 'is this worth interrupting for?'. Urgency answers 'is it too late
to wait?'. A timed task with travel has a leave-by moment (start - travel); once
now crosses it, the agent interrupts regardless of the suggestion's minute value
— the 'leave now' case — and warns as it approaches.

'Location' here is the travel estimate the engine already produces. A real
geolocation + routing provider (current position -> ETA to the task) slots in by
supplying `travel` per task; this logic doesn't change.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from ..household.timemap import fmt, task_minutes

_SOON_MIN = 30    # within this many minutes of leave-by -> interrupt ("leaving soon")


def now_minutes(now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    return now.hour * 60 + now.minute


def assess(when: str, travel: int, now_min: int) -> Tuple[str, Optional[str], bool]:
    """Return (urgency, leave_by_label, interrupt_override) for a timed task.

    urgency is one of now | soon | today | flexible. interrupt_override is True
    only for the time-critical cases (now, soon) — it beats the value threshold.
    """
    start = task_minutes(when) if when else None
    if start is None:
        return ("flexible", None, False)
    leave_by = start - max(0, travel)
    label = fmt(max(0, leave_by))
    if now_min >= start:                      # already underway or past
        return ("today", label, False)
    slack = leave_by - now_min
    if slack <= 0:                            # you should already be moving
        return ("now", label, True)
    if slack <= _SOON_MIN:
        return ("soon", label, True)
    return ("today", label, False)
