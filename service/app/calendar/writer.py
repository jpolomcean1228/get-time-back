"""Calendar writers — create/delete events behind one interface.

The Phase 5 "Protect it" action writes a defended block onto the calendar on
confirm and removes it on undo. MockCalendarWriter runs that loop safely today;
GoogleCalendarWriter does it for real with the calendar.events (write) scope —
a deliberate, separate opt-in from the read-only provider, so read access never
silently becomes write access.
"""
from __future__ import annotations

import datetime as dt
from typing import Protocol

WRITE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarWriter(Protocol):
    def create_event(self, summary: str, start: dt.datetime, end: dt.datetime) -> str: ...
    def delete_event(self, event_id: str) -> None: ...


class MockCalendarWriter:
    """Safe writer: hands back a fake id, deletes nothing. Records calls."""
    def __init__(self):
        self.created: list[tuple[str, str]] = []   # (id, summary)
        self.deleted: list[str] = []
        self._n = 0

    def create_event(self, summary: str, start: dt.datetime, end: dt.datetime) -> str:
        self._n += 1
        eid = f"mock-evt-{self._n}"
        self.created.append((eid, summary))
        return eid

    def delete_event(self, event_id: str) -> None:
        self.deleted.append(event_id)


class GoogleCalendarWriter:
    """Real read/write calendar client (calendar.events scope)."""
    def __init__(self, credentials_path: str, token_path: str = "token_write.json"):
        self._credentials_path = str(credentials_path)
        self._token_path = str(token_path)
        self._service = None

    def _ensure_service(self):
        if self._service is not None:
            return
        from googleapiclient.discovery import build
        from ..google_auth import authorize
        creds = authorize(self._credentials_path, self._token_path, WRITE_SCOPES)
        self._service = build("calendar", "v3", credentials=creds)

    def create_event(self, summary: str, start: dt.datetime, end: dt.datetime) -> str:
        self._ensure_service()
        body = {
            "summary": summary,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()},
        }
        ev = self._service.events().insert(calendarId="primary", body=body).execute()
        return ev["id"]

    def delete_event(self, event_id: str) -> None:
        self._ensure_service()
        self._service.events().delete(calendarId="primary", eventId=event_id).execute()
