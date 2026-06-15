"""Household roster — who's in the pod and what each can do.

The roster is the first thing the coordination layer needs: a list of people
(beyond just "me") and their capabilities, so the matcher knows who *could*
take a task before it checks who's free and willing.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Member:
    id: str
    name: str
    can_drive: bool = True


class Household:
    def __init__(self, me: str, members: list[Member]):
        self.me = me
        self._by_id = {m.id: m for m in members}

    def get(self, member_id: str) -> Member | None:
        return self._by_id.get(member_id)

    def all(self) -> list[Member]:
        return list(self._by_id.values())

    def others(self) -> list[Member]:
        """Everyone except the current user — the candidate helpers."""
        return [m for m in self._by_id.values() if m.id != self.me]

    @property
    def my_name(self) -> str:
        m = self._by_id.get(self.me)
        return m.name if m else "You"
