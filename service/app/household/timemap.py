"""Shared time-map — each member's free/busy windows for today.

The matcher asks this one question: is member X free for the window this task
needs? Busy windows come from members' calendars (mock fixture here; a real
shared-calendar adapter slots in behind the same interface).

Two clock parsers, because the two sources use different conventions:
  - parse_clock: fixtures are written in 24h ("17:00") — taken literally.
  - task_minutes: tasks are written informally ("5:30" meaning afternoon), so
    times before 8:00 are read as PM. Keeps the demo's "5:30 pickup" at 17:30
    instead of dawn.
"""
from __future__ import annotations


def parse_clock(s: str) -> int:
    """'HH:MM' (24h) -> minutes since midnight."""
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def task_minutes(when: str) -> int | None:
    """Informal task time -> minutes, reading early hours as PM. None if blank."""
    if not when:
        return None
    h, m = when.split(":")
    h, m = int(h), int(m)
    if h < 8:           # "5:30" means 5:30 PM in a day's schedule
        h += 12
    return h * 60 + m


def fmt(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{suffix}"


class TimeMap:
    def __init__(self, busy: dict[str, list[tuple[int, int]]]):
        # busy[member_id] = list of (start_min, end_min)
        self._busy = busy

    def is_free(self, member_id: str, start: int, end: int) -> bool:
        for bs, be in self._busy.get(member_id, []):
            if start < be and bs < end:      # overlap
                return False
        return True
