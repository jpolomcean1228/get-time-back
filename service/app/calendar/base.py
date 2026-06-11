"""Read-only calendar interface.

Phase 1 reads the calendar for two reasons:
  1. today's committed events are input alongside the task list
  2. scheduled-vs-observed durations are a free source of actuals

Providers are swappable behind this interface. The Mock provider runs with no
credentials; the Google provider is the real (OAuth) implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class CalEvent:
    title: str
    start: str          # ISO 8601
    end: str            # ISO 8601
    minutes: int        # scheduled duration
    location: str = ""
    attendees: int = 1


class CalendarProvider(Protocol):
    def today(self) -> list[CalEvent]: ...
