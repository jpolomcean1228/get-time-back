"""Defense — protected blocks that other placements must respect.

A reclaimed-time block isn't real if the next task can be scheduled on top of
it. Once a protected block is confirmed it lives here, and `defends()` lets the
rest of the system refuse to encroach. This is what makes "protected" mean
something rather than being a polite label.
"""
from __future__ import annotations


class ProtectedBlocks:
    def __init__(self):
        self._b: dict[str, tuple[int, int]] = {}

    def add(self, block_id: str, start: int, end: int) -> None:
        self._b[block_id] = (start, end)

    def remove(self, block_id: str) -> None:
        self._b.pop(block_id, None)

    def defends(self, start: int, end: int) -> bool:
        """True if [start, end] would encroach on any protected block."""
        return any(start < be and bs < end for bs, be in self._b.values())

    def list(self) -> list[dict]:
        return [{"id": k, "start": s, "end": e} for k, (s, e) in self._b.items()]
