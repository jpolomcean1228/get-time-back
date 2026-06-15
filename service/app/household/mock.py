"""Mock household loader.

Reads roster, time-map, and consent from JSON fixtures so the whole
coordination layer runs today with no shared-calendar integration. A real
loader (shared calendars + a consent store) implements the same return shape.
"""
from __future__ import annotations

import json
from pathlib import Path

from .consent import Consent, MemberConsent
from .roster import Household, Member
from .timemap import TimeMap, parse_clock

_FX = Path(__file__).resolve().parents[1] / "fixtures"


def load_mock_household() -> tuple[Household, TimeMap, Consent]:
    roster = json.loads((_FX / "household.json").read_text())
    members = [Member(id=m["id"], name=m["name"], can_drive=m.get("can_drive", True), email=m.get("email", ""))
               for m in roster["members"]]
    household = Household(me=roster["me"], members=members)

    raw_busy = json.loads((_FX / "timemap.json").read_text())
    busy = {mid: [(parse_clock(a), parse_clock(b)) for a, b in windows]
            for mid, windows in raw_busy.items()}
    timemap = TimeMap(busy)

    raw_consent = json.loads((_FX / "consent.json").read_text())
    consent = Consent({mid: MemberConsent(**flags) for mid, flags in raw_consent.items()})

    return household, timemap, consent
