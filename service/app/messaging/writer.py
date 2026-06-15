"""Message writers — create/delete Gmail drafts behind one interface.

The "Ask Maya" hand-off drafts a message on confirm and discards it on undo.
MockMessageWriter runs that loop safely today; GmailMessageWriter does it for
real with the gmail.compose scope. Drafts only — the tool never sends; the user
reviews and sends themselves.
"""
from __future__ import annotations

from typing import Protocol

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


class MessageWriter(Protocol):
    def create_draft(self, to: str, subject: str, body: str) -> str: ...
    def delete_draft(self, draft_id: str) -> None: ...


class MockMessageWriter:
    """Safe writer: hands back a fake draft id, sends nothing. Records calls."""
    def __init__(self):
        self.created: list[tuple[str, str, str]] = []   # (id, to, subject)
        self.deleted: list[str] = []
        self._n = 0

    def create_draft(self, to: str, subject: str, body: str) -> str:
        self._n += 1
        did = f"mock-draft-{self._n}"
        self.created.append((did, to, subject))
        return did

    def delete_draft(self, draft_id: str) -> None:
        self.deleted.append(draft_id)


class GmailMessageWriter:
    """Real Gmail draft client (gmail.compose scope). Creates drafts, never sends."""
    def __init__(self, credentials_path: str, token_path: str = "token_gmail.json"):
        self._credentials_path = str(credentials_path)
        self._token_path = str(token_path)
        self._service = None

    def _ensure_service(self):
        if self._service is not None:
            return
        from googleapiclient.discovery import build
        from ..google_auth import authorize
        creds = authorize(self._credentials_path, self._token_path, GMAIL_SCOPES)
        self._service = build("gmail", "v1", credentials=creds)

    def create_draft(self, to: str, subject: str, body: str) -> str:
        import base64
        from email.mime.text import MIMEText
        self._ensure_service()
        msg = MIMEText(body)
        if to:
            msg["To"] = to
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft = self._service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}).execute()
        return draft["id"]

    def delete_draft(self, draft_id: str) -> None:
        self._ensure_service()
        self._service.users().drafts().delete(userId="me", id=draft_id).execute()
