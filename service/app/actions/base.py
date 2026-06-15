"""Action layer core types — Phase 3.

Phases 1-2 only observed and recommended. Phase 3 is the first time the tool
reaches into the user's world and changes something, so every action is:
  - proposed by default (nothing happens without an explicit confirm)
  - reversible (undo restores the prior state)
  - executed behind one interface, so a mock runs today and real adapters
    (calendar write, message draft) slot in unchanged.

Lifecycle: proposed -> (confirm) -> executed -> (undo) -> undone
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# action types, one per lever that produces a concrete move
BLOCK_TIME = "block_time"        # protect / defer  -> fence a calendar block
DRAFT_MESSAGE = "draft_message"  # delegate         -> carpool / handoff text
BATCH_ERRANDS = "batch_errands"  # batch            -> one errand loop
DELAY_START = "delay_start"      # overlap          -> start chore so it ends when free
ASYNC_UPDATE = "async_update"    # automate         -> replace meeting with async
CANCEL = "cancel"                # eliminate        -> drop it


@dataclass
class Action:
    id: str            # deterministic: f"{lever}:{normalized title}" — idempotent to re-propose
    type: str
    lever: str
    label: str         # the button verb, e.g. "Block the time"
    detail: str        # human preview of what will happen
    body: str = ""     # optional draft text (messages)
    reversible: bool = True
    status: str = "proposed"   # proposed | executed | undone
    result: str = ""           # executor's confirmation message


class Executor(Protocol):
    def execute(self, action: Action) -> str: ...
    def undo(self, action: Action) -> str: ...
