"""Executors.

MockExecutor runs every action type safely — it just reports what *would*
happen — so the whole confirm-and-undo loop works today with no credentials
and no risk. Real adapters (calendar write, message draft) implement the same
two methods and slot in unchanged; they're stubbed here with wiring notes.
"""
from __future__ import annotations

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
    """Real calendar write-back (block_time) — Phase 3 stub.

    Phase 1 deliberately kept calendar access read-only. This executor is where
    write arrives, gated behind explicit per-action confirmation.

    Wiring checklist:
      1. Upgrade the OAuth scope from calendar.readonly to calendar.events
         (events scope is narrower than full calendar — request the minimum).
      2. execute(): create an event for the block; STORE THE RETURNED eventId
         on the action so undo() can delete exactly that event.
      3. undo(): delete the stored eventId. Reversibility is non-negotiable here.
    """
    def execute(self, action: Action) -> str:
        raise NotImplementedError("CalendarExecutor is a stub. Use MockExecutor.")

    def undo(self, action: Action) -> str:
        raise NotImplementedError("CalendarExecutor is a stub. Use MockExecutor.")


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
