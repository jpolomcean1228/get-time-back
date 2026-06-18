"""Task profiles — the rules table, externalized to data.

Phase 0/1 baked the category knowledge into Python: a `PROFILES` dict of cost
tuples plus a parallel `_KEYWORDS` list, both edited in source. That made the
classifier a developer-only seam. Here it becomes user data, exactly like
`fixtures/values.json` and the household roster: a profile is a JSON object,
and adding a category no longer means touching code.

A profile carries both halves the old two tables held separately:
  - how the item is recognised  (`keywords`)
  - what it costs and how to shorten it  (active/wait/travel/frag + lever + why)

One profile is the `default` — the bucket a task lands in when nothing matches.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_FX = Path(__file__).resolve().parents[1] / "fixtures" / "profiles.json"


@dataclass
class Profile:
    """One task type: how to spot it, what it costs, and the move that shrinks it."""
    category: str
    active: int           # hands-on minutes
    wait: int             # passive / waiting minutes
    travel: int           # door-to-door travel minutes
    frag: int             # focus minutes shattered around it
    lever: str            # the recommended move
    why: str = ""         # one-line rationale, in the user's terms
    keywords: tuple[str, ...] = ()   # substrings that classify text into this profile
    default: bool = False            # the fallback bucket when nothing matches

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        return cls(
            category=d["category"],
            active=int(d["active"]), wait=int(d["wait"]),
            travel=int(d["travel"]), frag=int(d["frag"]),
            lever=d["lever"], why=d.get("why", ""),
            keywords=tuple(d.get("keywords", ()) or ()),
            default=bool(d.get("default", False)),
        )


class ProfileStore:
    """Ordered profiles with a single default fallback.

    Classification is first-match-wins over `keywords`, in list order — the
    same precedence the old `_KEYWORDS` list relied on (presence before
    meeting, etc.). The default profile is never matched on keywords; it is
    only the answer when nothing else fits.
    """

    def __init__(self, profiles: list[Profile]):
        self._order: list[Profile] = list(profiles)
        self._by_cat: dict[str, Profile] = {p.category: p for p in profiles}
        self._default: Optional[Profile] = next(
            (p for p in profiles if p.default),
            profiles[-1] if profiles else None,
        )

    def list(self) -> list[Profile]:
        return list(self._order)

    def get(self, category: str) -> Optional[Profile]:
        """The profile for a category, falling back to the default bucket."""
        return self._by_cat.get(category) or self._default

    def classify(self, text: str) -> str:
        s = text.lower()
        for p in self._order:
            if p.default:
                continue
            if any(w in s for w in p.keywords):
                return p.category
        return self._default.category if self._default else "task"

    def add(self, profile: Profile) -> Profile:
        """Add or replace a profile. New ones are checked before the default."""
        existing = self._by_cat.get(profile.category)
        if existing is not None:
            self._order[self._order.index(existing)] = profile
        else:
            insert_at = (self._order.index(self._default)
                         if self._default is not None and self._default in self._order
                         else len(self._order))
            self._order.insert(insert_at, profile)
        self._by_cat[profile.category] = profile
        if profile.default:
            self._default = profile
        return profile


def load_profiles(path: Optional[Path] = None) -> ProfileStore:
    """Build a ProfileStore from a JSON fixture (the default table when unset)."""
    raw = json.loads((path or _FX).read_text())
    return ProfileStore([Profile.from_dict(d) for d in raw])


# Process-wide default store. The rules estimator, the standalone classify()
# helper, and the /profiles endpoints all share this one instance, so a profile
# added at runtime takes effect immediately — the same live-singleton shape the
# values store uses.
_DEFAULT: Optional[ProfileStore] = None


def default_profiles() -> ProfileStore:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load_profiles()
    return _DEFAULT
