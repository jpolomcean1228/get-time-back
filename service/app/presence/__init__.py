"""Presence layer — the values loop (Phase 5)."""
from .values import Value, ValuesStore
from .planner import PresencePlanner, PresencePlan, PresenceBlock
from .defense import ProtectedBlocks
from .executor import DefendingExecutor
from .mock import load_mock_values

__all__ = [
    "Value", "ValuesStore", "PresencePlanner", "PresencePlan", "PresenceBlock",
    "ProtectedBlocks", "DefendingExecutor", "load_mock_values",
]
