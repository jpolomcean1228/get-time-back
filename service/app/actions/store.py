"""Action store + lifecycle.

Holds proposed actions and drives them through confirm/undo behind the gate.
In-memory by design: proposals are ephemeral working state, not durable data
like actuals. Re-proposing an existing action is idempotent — it never resets
an action that's already been executed.
"""
from __future__ import annotations

from .base import Action, Executor


class ActionStore:
    def __init__(self, executor: Executor):
        self._actions: dict[str, Action] = {}
        self._executor = executor

    def propose(self, action: Action) -> Action:
        """Register a proposal. If it already exists, keep its current state."""
        existing = self._actions.get(action.id)
        if existing is not None:
            return existing
        self._actions[action.id] = action
        return action

    def get(self, action_id: str) -> Action | None:
        return self._actions.get(action_id)

    def list(self) -> list[Action]:
        return list(self._actions.values())

    def confirm(self, action_id: str) -> Action | None:
        """The gate: execute a proposed action on explicit confirmation."""
        a = self._actions.get(action_id)
        if a is None:
            return None
        if a.status == "proposed":
            a.result = self._executor.execute(a)
            a.status = "executed"
        return a

    def undo(self, action_id: str) -> Action | None:
        a = self._actions.get(action_id)
        if a is None:
            return None
        if a.status == "executed" and a.reversible:
            a.result = self._executor.undo(a)
            a.status = "undone"
        return a
