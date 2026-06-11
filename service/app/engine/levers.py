"""Levers and the credit calculation.

The lever is the *move* that shortens a task; credit() is how many minutes
that move hands back. Ported verbatim from the Phase 0 demo so behaviour is
continuous, then centralised here as the single source of truth.
"""
from __future__ import annotations

from .base import Estimate

LEVERS: dict[str, str] = {
    "eliminate": "Eliminate",
    "automate": "Automate",
    "delegate": "Delegate",
    "batch": "Batch",
    "defer": "Defer",
    "overlap": "Overlap",
    "protect": "Protect",
}


def credit(e: Estimate) -> int:
    """Minutes returned to the user by the recommended lever."""
    if e.lever == "eliminate":
        return e.active + e.wait + e.travel
    if e.lever == "automate":
        return round(e.active * 0.8)
    if e.lever == "delegate":
        return e.active + e.travel + e.wait
    if e.lever == "batch":
        return e.travel
    if e.lever == "overlap":
        return e.wait
    if e.lever == "defer":
        return e.frag          # focus protected, not wall-clock reclaimed
    if e.lever == "protect":
        return 0               # presence — defended, never compressed
    return 0


def kind(e: Estimate) -> str:
    """Logistics (compress) vs presence (defend)."""
    return "presence" if e.lever == "protect" and e.category == "presence" else "logistics"
