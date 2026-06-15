"""Executors.

MockExecutor runs every action type safely — it just reports what *would*
happen — so the whole confirm-and-undo loop works today with no credentials
and no risk. Real adapters (calendar write, message draft) implement the same
two methods and slot in unchanged; they're stubbed here with wiring notes.
"""
from __future__ import annotations

import datetime as dt

from .base import (ASYNC_UPDATE, BATCH_ERRANDS, BLOCK_TIME, CANCEL,
                   DELAY_START, DRAFT_MESSAGE, Action)

_DONE = {
    BLOCK_TIME:    "Blocked on your calendar.",
    DRAFT_MESSAGE: "Drafted \u2014 waiting in your outbox to send.",
    BATCH_ERRANDS: "Added to today's errand loop.",
    DELAY_START:   "Delay-start scheduled.",
    ASYNC_UPDATE:  "Async update created; meeting slot freed.",
    CANCEL:        "Removed from today.",
}


class MockExecutor:
    """Safe no-op executor: records the outcome without touching anything."""
    def execute(self, action: Action) -> str:
        return _DONE.get(action.type, "Done.") + " (demo)"

    def undo(self, action: Action) -> str:
        return "Reverted."


class CalendarExecutor:
    """Real calendar write-back for block_time actions.

    On confirm, creates a calendar event for the block and stores its id on the
    action; on undo, deletes exactly that event. Everything that isn't a
    block_time action delegates to the base executor (mock today). Pair with a
    CalendarWriter (mock or Google); the executor itself is interface-only, so
    it's testable with a fake writer and no network.

    Calendar *write* is the first capability beyond read-only, and it only ever
    runs through the confirm gate — never automatically.
    """
    def __init__(self, base, writer):
        self._base = base
        self._writer = writer

    def _window(self, action):
        # turn minutes-since-midnight into today's datetimes, local tz
        today = dt.datetime.now().astimezone().replace(
            hour=0, minute=0, second=0, microsecond=0)
        start = today + dt.timedelta(minutes=action.start_min)
        end = today + dt.timedelta(minutes=action.end_min)
        return start, end

    def execute(self, action: Action) -> str:
        if action.type == BLOCK_TIME and action.start_min >= 0:
            start, end = self._window(action)
            summary = action.label.replace("Protect ", "").strip("\u201C\u201D\" ")
            action.external_id = self._writer.create_event(summary or action.label, start, end)
            return "Added to your calendar."
        return self._base.execute(action)

    def undo(self, action: Action) -> str:
        if action.type == BLOCK_TIME and action.external_id:
            self._writer.delete_event(action.external_id)
            action.external_id = ""
            return "Removed from your calendar."
        return self._base.undo(action)


class MessageExecutor:
    """Real message draft (draft_message) — Phase 3 stub.

    Drafts only — never auto-sends. Create a draft in Gmail/Slack/etc. from
    action.body, store the draft id, and let undo() discard it. The user still
    presses send themselves; the tool only ever prepares the message.
    """
    def execute(self, action: Action) -> str:
        raise NotImplementedError("MessageExecutor is a stub. Use MockExecutor.")

    def undo(self, action: Action) -> str:
        raise NotImplementedError("MessageExecutor is a stub. Use MockExecutor.")
