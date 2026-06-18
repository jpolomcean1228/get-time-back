"""Levers and the credit calculation, as a registry.

The lever is the *move* that shortens a task; its credit function is how many
minutes that move hands back. Phase 0 hardcoded these as a `LEVERS` dict plus a
parallel if/elif chain in `credit()` — so adding a lever meant editing two
places that had to stay in sync. Here a lever is one self-contained unit (label
+ credit formula) registered by name, and `credit()` is a dict lookup.

`register_lever(...)` adds or replaces one; an unknown lever credits 0, so a
profile can reference a lever that isn't registered yet without breaking enrich.

`LEVERS` is kept as a live name -> label mapping for backward compatibility
(the LLM estimator validates against it); it stays in sync as levers register.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .base import Estimate

CreditFn = Callable[[Estimate], int]


@dataclass
class Lever:
    name: str
    label: str
    credit: CreditFn


_REGISTRY: dict[str, Lever] = {}
# name -> label, kept in sync with the registry for back-compat (`x in LEVERS`,
# `LEVERS.get(...)`). Mutated only through register_lever.
LEVERS: dict[str, str] = {}


def register_lever(name: str, label: str, credit: CreditFn) -> Lever:
    """Add or replace a lever. Returns the registered Lever."""
    lever = Lever(name=name, label=label, credit=credit)
    _REGISTRY[name] = lever
    LEVERS[name] = label
    return lever


def credit(e: Estimate) -> int:
    """Minutes returned to the user by the recommended lever (0 if unknown)."""
    lever = _REGISTRY.get(e.lever)
    return lever.credit(e) if lever else 0


def lever_label(name: str) -> str:
    """Display label for a lever name, falling back to the name itself."""
    return LEVERS.get(name, name)


def kind(e: Estimate) -> str:
    """Logistics (compress) vs presence (defend)."""
    return "presence" if e.lever == "protect" and e.category == "presence" else "logistics"


# --- the default lever set (ported verbatim from Phase 0) ------------------
register_lever("eliminate", "Eliminate", lambda e: e.active + e.wait + e.travel)
register_lever("automate", "Automate", lambda e: round(e.active * 0.8))
register_lever("delegate", "Delegate", lambda e: e.active + e.travel + e.wait)
register_lever("batch", "Batch", lambda e: e.travel)
register_lever("overlap", "Overlap", lambda e: e.wait)
register_lever("defer", "Defer", lambda e: e.frag)        # focus protected, not wall-clock
register_lever("protect", "Protect", lambda e: 0)         # presence — defended, never compressed
