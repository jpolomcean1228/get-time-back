"""The value function — the objective the agent maximizes.

'Deliver the most time back' becomes a number: protected presence weighted
highest (it's the point), reclaimable time next, minus a penalty for the focus
fragmentation left in the day. This scores a *proposed* plan; the true
north-star is presence that survived the week, measured after the fact.
"""
from __future__ import annotations

from .base import ValueScore

W_PRESENCE = 1.5
W_RECLAIM = 1.0
W_FRAG = 0.5


def score(tasks, presence) -> ValueScore:
    reclaimable = presence.reclaimable if presence else sum(t.reclaim for t in tasks)
    presence_protected = presence.allocated if presence else 0
    banked = presence.banked if presence else 0
    fragmentation = sum(t.frag for t in tasks if t.kind == "logistics")
    total = round(presence_protected * W_PRESENCE + reclaimable * W_RECLAIM
                  - fragmentation * W_FRAG, 1)
    return ValueScore(reclaimable=reclaimable, presence_protected=presence_protected,
                      fragmentation=fragmentation, banked=banked, score=total)
