"""Actuals signatures.

Phase 2 stops lumping every task of a category into one learning bucket.
A signature has two levels:

    specific  -> "chore:laundry"        (this exact recurring item)
    category  -> "chore"                (the category average, the fallback)

Recurring items have stable titles, so their specific buckets accumulate
samples fast and learn precisely. Novel one-offs fall back to the category
average until they've been seen enough times. The estimator and the /actuals
endpoint both call signature() so they always agree on the bucket.
"""
from __future__ import annotations

import re

_STOP = {
    "the", "a", "an", "to", "from", "of", "and", "or", "with", "for",
    "my", "at", "on", "in", "this", "that", "some", "do", "go",
}
_TIME = re.compile(r"\b\d{1,2}:\d{2}\b")
_NONWORD = re.compile(r"[^a-z0-9 ]")


def normalize(title: str) -> str:
    """Reduce a title to an order-independent key of meaningful words."""
    s = title.lower()
    s = _TIME.sub(" ", s)            # drop trailing times
    s = _NONWORD.sub(" ", s)         # drop punctuation
    tokens = [t for t in s.split() if t and t not in _STOP]
    return " ".join(sorted(tokens))  # sorted -> "grocery pharmacy" == "pharmacy grocery"


def signature(title: str, category: str) -> str:
    """The specific bucket: category + normalized title key."""
    key = normalize(title)
    return f"{category}:{key}" if key else category
