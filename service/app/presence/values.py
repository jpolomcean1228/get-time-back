"""Stated values — what the user actually wants the reclaimed time for.

This is the input that closes the loop. Without it, "you saved 90 minutes" is
just a number that work quietly reabsorbs. With it, those 90 minutes have a
destination the user named themselves.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Value:
    id: str
    label: str
    minutes: int      # how much time this deserves
    when: str         # preferred start, 24h "HH:MM"
    priority: int     # lower = funded first


class ValuesStore:
    def __init__(self, values: list[Value]):
        self._v = {v.id: v for v in values}

    def list(self) -> list[Value]:
        return sorted(self._v.values(), key=lambda v: v.priority)

    def add(self, value: Value) -> Value:
        self._v[value.id] = value
        return value
