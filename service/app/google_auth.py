"""Shared Google OAuth — one authorize() for every Google integration.

Calendar (read + write) and Gmail (drafts) all run through this. Each caller
passes its own scope and token file, so capabilities stay separate: read access
never silently gains write, and calendar access never gains mail access.
"""
from __future__ import annotations

from pathlib import Path


def authorize(credentials_path: str, token_path: str, scopes: list[str]):
    """Run/refresh OAuth and return credentials, caching to token_path."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)  # opens a browser once
        Path(token_path).write_text(creds.to_json())
    return creds
