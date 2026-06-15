"""Propose a concrete action from an enriched task.

Each lever maps to one reversible action the user can confirm. The id is
deterministic (lever + normalized title), so re-proposing the same task on a
later /enrich call returns the same action rather than duplicating it.
"""
from __future__ import annotations

from ..engine.base import Estimate
from ..engine.signature import normalize
from .base import (ASYNC_UPDATE, BATCH_ERRANDS, BLOCK_TIME, CANCEL,
                   DELAY_START, DRAFT_MESSAGE, Action)


def _id(lever: str, title: str) -> str:
    key = normalize(title) or title.lower().strip()
    return f"{lever}:{key}"


def propose(est: Estimate) -> Action | None:
    """Map a recommendation to a proposed, reversible action (or None)."""
    title = est.title
    when = est.when or "this evening"
    aid = _id(est.lever, title)

    if est.lever == "protect":
        return Action(id=aid, type=BLOCK_TIME, lever=est.lever,
                      label="Protect the block",
                      detail=f"Fence {est.total} min around {when} for \u201C{title}\u201D and defend it from other invites.")

    if est.lever == "defer":
        return Action(id=aid, type=BLOCK_TIME, lever=est.lever,
                      label="Move to the edge",
                      detail=f"Move \u201C{title}\u201D to the edge of the day so it stops splitting a focus block.")

    if est.lever == "delegate":
        return Action(id=aid, type=DRAFT_MESSAGE, lever=est.lever,
                      label="Draft the hand-off",
                      detail=f"Draft a message to hand off \u201C{title}\u201D (e.g. a carpool swap).",
                      body=f"Hey \u2014 any chance you could cover \u201C{title}\u201D this week? "
                           f"Happy to swap and take one of yours in return. Let me know what works.")

    if est.lever == "batch":
        return Action(id=aid, type=BATCH_ERRANDS, lever=est.lever,
                      label="Add to the loop",
                      detail=f"Add \u201C{title}\u201D to one errand loop with your other stops to reclaim the {est.travel} min of travel.")

    if est.lever == "overlap":
        return Action(id=aid, type=DELAY_START, lever=est.lever,
                      label="Set delay-start",
                      detail=f"Start \u201C{title}\u201D on a delay so its {est.wait} min of waiting finishes when you're free.")

    if est.lever == "automate":
        return Action(id=aid, type=ASYNC_UPDATE, lever=est.lever,
                      label="Make it async",
                      detail=f"Replace \u201C{title}\u201D with a 5-minute async update and reclaim the slot.")

    if est.lever == "eliminate":
        return Action(id=aid, type=CANCEL, lever=est.lever,
                      label="Drop it",
                      detail=f"Remove \u201C{title}\u201D from today.")

    return None  # nothing actionable (shouldn't happen for known levers)
