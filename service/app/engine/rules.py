"""The rules estimator.

A direct port of the Phase 0 classify/enrich logic. It needs no API key, no
network, and no data — so it is both the cold-start baseline and the fallback
whenever the LLM path is unavailable. Never let the service fail in a demo.
"""
from __future__ import annotations

from .base import Estimate, Task

# category -> (active, wait, travel, frag, lever, why)
PROFILES: dict[str, tuple[int, int, int, int, str, str]] = {
    "presence":          (45, 0, 0, 0, "protect",
                          "This is the point. Don't compress it — defend it."),
    "recurring-meeting": (30, 0, 0, 20, "automate",
                          "Recurring status -> 5-min async update; reclaim the half-hour and the context switch."),
    "meeting":           (30, 0, 0, 15, "defer",
                          "Cut to 15 and move to the day's edge so it stops splitting a focus block."),
    "family-logistics":  (20, 25, 20, 35, "delegate",
                          "Carpool swap hands off the whole on-call window, not just the drive."),
    "errand":            (25, 0, 30, 20, "batch",
                          "Pin to one loop with the other stops, or switch to delivery; the travel is the cost."),
    "chore":             (12, 78, 0, 5, "overlap",
                          "Mostly wait time. Delay-start to finish when you're free; overlap the wait."),
    "admin":             (35, 0, 0, 10, "automate",
                          "Recurring admin -> rule, template, or auto-submit; batch what's left."),
    "appointment":       (40, 15, 25, 20, "batch",
                          "Can't shorten the visit — stack nearby errands onto the trip and reclaim the travel."),
    "deep-work":         (90, 0, 0, 0, "protect",
                          "Protect from fragmentation — fence the block, push interruptions to the edges."),
    "task":              (30, 0, 0, 10, "defer",
                          "Right-size it and place it in a low-cost slot."),
}

# ordered: first matching bucket wins (presence is checked before meeting, etc.)
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("presence", ("read to", "bedtime", "dinner with", "date", "call mom",
                  "call dad", "family time", "with the kids", "park with")),
    ("recurring-meeting", ("sync", "standup", "stand-up", "status", "weekly",
                           "1:1", "one-on-one", "check-in", "check in", "catch-up")),
    ("meeting", ("meeting", "call", "review", "huddle")),
    ("family-logistics", ("pick up", "pickup", "drop off", "dropoff", "carpool",
                          "basketball", "soccer", "practice", "school", "daycare")),
    ("errand", ("grocery", "groceries", "shop", "store", "pharmacy", "target",
                "costco", "dry clean", "errand")),
    ("chore", ("laundry", "dishes", "clean", "vacuum", "trash", "fold",
               "dishwasher", "mop")),
    ("admin", ("email", "inbox", "expense", "report", "invoice", "timesheet",
               "form", "admin", "bill", "reconcile")),
    ("appointment", ("dentist", "doctor", "appointment", "dmv", "haircut",
                     "vet", "oil change", "checkup")),
    ("deep-work", ("write", "draft", "design", "deep work", "focus", "plan ",
                   "strategy", "code", "build the")),
]


def classify(text: str) -> str:
    s = text.lower()
    for category, words in _KEYWORDS:
        if any(w in s for w in words):
            return category
    return "task"


class RulesEstimator:
    def estimate(self, task: Task) -> Estimate:
        category = classify(task.raw)
        active, wait, travel, frag, lever, why = PROFILES[category]
        return Estimate(
            title=task.title, when=task.when, category=category,
            active=active, wait=wait, travel=travel, frag=frag,
            lever=lever, why=why, confidence=0.0, source="rules",
        )
