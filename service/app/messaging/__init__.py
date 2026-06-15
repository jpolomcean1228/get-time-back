"""Messaging integration — Gmail drafts behind a writer interface."""
from .writer import MessageWriter, MockMessageWriter, GmailMessageWriter

__all__ = ["MessageWriter", "MockMessageWriter", "GmailMessageWriter"]
