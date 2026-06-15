"""Defending executor — registers a protected block when its action executes.

Wraps any base executor (the mock today). When a BLOCK_TIME action carrying a
window is confirmed, it adds that window to ProtectedBlocks so the rest of the
system will defend it; undo releases it. This is how confirm-to-protect becomes
a real, enforced reservation rather than a message.
"""
from __future__ import annotations

from ..actions.base import BLOCK_TIME, Action, Executor
from .defense import ProtectedBlocks


class DefendingExecutor:
    def __init__(self, base: Executor, protected: ProtectedBlocks):
        self._base = base
        self._protected = protected

    def execute(self, action: Action) -> str:
        msg = self._base.execute(action)
        if action.type == BLOCK_TIME and action.start_min >= 0:
            self._protected.add(action.id, action.start_min, action.end_min)
            return "Protected and defended \u2014 nothing else can land here. (demo)"
        return msg

    def undo(self, action: Action) -> str:
        self._protected.remove(action.id)
        return self._base.undo(action)
