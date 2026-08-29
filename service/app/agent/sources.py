"""Inbox sources — where raw messages come from.

Two that run anywhere: a mock inbox (realistic fixtures, for the demo and tests)
and pasted text (handled at the endpoint). One real, behind a flag: GmailInbox,
read-only (gmail.readonly), which lists recent inbox messages so the extractor
can mine them. The real source mirrors the Gmail draft writer's auth exactly but
with a separate read-only scope and token, so read access never implies send.

The real path can't be exercised without your Google credentials, so treat it as
prototype-grade: it's a faithful scaffold to enable, not a tested integration.
Enable by pointing GTB_GMAIL_READ at your OAuth client secrets JSON.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

GMAIL_READ_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


@dataclass
class Message:
    sender: str
    subject: str
    text: str


_MOCK_INBOX = [
    Message("Lincoln Elementary", "Friday field trip",
            "Hi families — a reminder that permission slips for Friday's field trip are due "
            "Thursday. Please sign and return them with the $12 fee. Thanks!"),
    Message("Maya (soccer carpool)", "Saturday game",
            "Hey! Can you bring orange slices for Saturday's game? Also don't forget we moved "
            "the start time to 9am. See you there!"),
    Message("Dr. Patel's office", "Annual checkup",
            "It's time to schedule the twins' annual checkup. Please call the office to book "
            "an appointment before the end of the month."),
    Message("Dana (work)", "Re: Q3 deck",
            "Thanks for the update, looks great. Could you send me the revised Q3 numbers by "
            "Tuesday? No rush beyond that. Hope you had a good weekend."),
]


def mock_inbox():
    return list(_MOCK_INBOX)


def harvest(messages, extractor):
    """Run the extractor over each message; dedupe commitments across the inbox."""
    out, seen = [], set()
    for m in messages:
        for c in extractor(m.text, source=m.sender):
            key = c.task.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
    return out


class GmailInbox:
    """Real read-only Gmail source (gmail.readonly). Untested here — a scaffold."""

    def __init__(self, credentials_path, token_path="token_gmail_read.json", max_messages=12):
        self._credentials_path = str(credentials_path)
        self._token_path = str(token_path)
        self._max = int(max_messages)
        self._service = None

    def _connect(self):
        if self._service is None:
            from googleapiclient.discovery import build

            from ..google_auth import authorize
            creds = authorize(self._credentials_path, self._token_path, GMAIL_READ_SCOPES)
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def fetch(self):
        svc = self._connect()
        listing = svc.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=self._max).execute()
        out = []
        for ref in listing.get("messages", []):
            msg = svc.users().messages().get(
                userId="me", id=ref["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"]
                       for h in msg.get("payload", {}).get("headers", [])}
            out.append(Message(sender=headers.get("from", ""),
                               subject=headers.get("subject", ""),
                               text=_body_text(msg) or msg.get("snippet", "")))
        return out


def _body_text(msg):
    """Pull readable text from a Gmail message payload (plain-text parts)."""
    def walk(part):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data + "===").decode("utf-8", "ignore")
        for sub in part.get("parts", []) or []:
            t = walk(sub)
            if t:
                return t
        return ""
    return walk(msg.get("payload", {}))
