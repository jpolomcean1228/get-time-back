"""Mock calendar provider.

Reads today's events from a JSON fixture so the whole service runs end-to-end
with no Google Cloud project, no OAuth, no network. Swap for GoogleCalendar
in production; the interface is identical.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path

from .base import CalEvent

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_calendar.json"


class MockCalendarProvider:
    def __init__(self, fixture: str | Path = _FIXTURE):
        self._fixture = Path(fixture)

    def today(self) -> list[CalEvent]:
        if not self._fixture.exists():
            return []
        raw = json.loads(self._fixture.read_text())
        today = date.today().isoformat()
        events: list[CalEvent] = []
        for e in raw:
            # fixture stores local HH:MM; stamp it onto today's date
            start = datetime.combine(date.today(), time.fromisoformat(e["start"]))
            end = datetime.combine(date.today(), time.fromisoformat(e["end"]))
            minutes = int((end - start).total_seconds() // 60)
            events.append(CalEvent(
                title=e["title"],
                start=f"{today}T{e['start']}",
                end=f"{today}T{e['end']}",
                minutes=minutes,
                location=e.get("location", ""),
                attendees=int(e.get("attendees", 1)),
            ))
        return events
