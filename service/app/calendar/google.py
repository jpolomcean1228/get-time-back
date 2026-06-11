"""Google Calendar provider (read-only) — production stub.

Wiring checklist (do this when you're ready to leave the mock behind):

1. Create a Google Cloud project, enable the Google Calendar API.
2. Configure an OAuth consent screen and create OAuth client credentials
   (Desktop or Web). Download the client secret JSON.
3. Request the READ-ONLY scope only:
       https://www.googleapis.com/auth/calendar.readonly
   Read-only is a Phase 1 invariant — we observe the day, we don't touch it.
   (Write-back arrives in Phase 3, behind explicit per-action confirmation.)
4. Run the OAuth flow once to mint a refresh token; store it per user.
5. Implement today() using the Calendar API events.list call, filtered to
   timeMin = start of today and timeMax = end of today, singleEvents=True.

Dependencies (add to requirements.txt when you implement this):
    google-api-python-client, google-auth, google-auth-oauthlib

Until then, MockCalendarProvider serves the same interface from a fixture.
"""
from __future__ import annotations

from .base import CalEvent


class GoogleCalendarProvider:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, credentials=None):
        self._credentials = credentials

    def today(self) -> list[CalEvent]:
        raise NotImplementedError(
            "GoogleCalendarProvider is a Phase 1 stub. Use MockCalendarProvider, "
            "or implement events.list per the checklist in this module's docstring."
        )
