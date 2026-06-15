"""Google Calendar provider (read-only) — real implementation.

Reads today's timed events from the user's primary calendar and maps them to
CalEvent, behind the same interface as MockCalendarProvider. Read-only by
design (Phase 1 invariant); calendar *write* lives in the Phase 3 executor and
stays separate.

Auth is lazy: nothing happens until today() is first called, so a misconfigured
install never blocks startup — the app simply keeps using the mock until a
valid credentials file is present (see app/main.py factory).

Setup: see service/CALENDAR_SETUP.md.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .base import CalEvent

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _parse_rfc3339(s: str) -> dt.datetime:
    # Python 3.9's fromisoformat can't parse a trailing 'Z'; normalize it.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s)


def to_calevent(item: dict) -> CalEvent | None:
    """Map one Google Calendar event dict to a CalEvent.

    Pure function (no network, no Google libs) so it's unit-testable. Returns
    None for all-day events, which carry 'date' not 'dateTime' and aren't
    schedulable blocks.
    """
    start = item.get("start", {})
    end = item.get("end", {})
    if "dateTime" not in start or "dateTime" not in end:
        return None
    s = _parse_rfc3339(start["dateTime"])
    e = _parse_rfc3339(end["dateTime"])
    minutes = int((e - s).total_seconds() // 60)
    return CalEvent(
        title=item.get("summary", "(no title)"),
        start=start["dateTime"], end=end["dateTime"], minutes=minutes,
        location=item.get("location", ""),
        attendees=len(item.get("attendees", []) or []) or 1,
    )


class GoogleCalendarProvider:
    SCOPES = SCOPES

    def __init__(self, credentials_path: str, token_path: str = "token.json"):
        self._credentials_path = str(credentials_path)
        self._token_path = str(token_path)
        self._service = None

    def _ensure_service(self):
        if self._service is not None:
            return
        from googleapiclient.discovery import build
        from ..google_auth import authorize
        creds = authorize(self._credentials_path, self._token_path, SCOPES)
        self._service = build("calendar", "v3", credentials=creds)

    def today(self) -> list[CalEvent]:
        self._ensure_service()
        now = dt.datetime.now().astimezone()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + dt.timedelta(days=1)
        resp = (
            self._service.events()
            .list(calendarId="primary", timeMin=start.isoformat(),
                  timeMax=end.isoformat(), singleEvents=True, orderBy="startTime")
            .execute()
        )
        events = []
        for item in resp.get("items", []):
            ev = to_calevent(item)
            if ev is not None:
                events.append(ev)
        return events
