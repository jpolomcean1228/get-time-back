"""Household coordination tests — the matcher and its privacy gate."""
from app.household import (Consent, Household, Matcher, Member, MemberConsent,
                           TimeMap, task_minutes)


def _setup():
    household = Household(me="justin", members=[
        Member("justin", "Justin", can_drive=True),
        Member("maya", "Maya", can_drive=True),
        Member("sam", "Sam", can_drive=False),
    ])
    timemap = TimeMap({
        "justin": [(17 * 60, 18 * 60 + 30)],   # busy at pickup time
        "maya": [(9 * 60, 12 * 60)],           # free in the afternoon
        "sam": [],
    })
    consent = Consent({
        "maya": MemberConsent(shares_availability=True, accepts_handoffs=True),
        "sam": MemberConsent(shares_availability=True, accepts_handoffs=False),
    })
    return Matcher(household, timemap, consent)


def test_picks_free_consenting_driver():
    m = _setup()
    start = task_minutes("5:30")               # -> 17:30, the pickup
    c = m.find(start, start + 65, needs_driving=True, recurring=True)
    assert c is not None
    assert c.helper.name == "Maya"             # free, consents, can drive
    assert c.kind == "swap"


def test_consent_gate_excludes_non_consenter():
    m = _setup()
    # Sam can't drive AND doesn't accept hand-offs; only Maya is eligible
    start = task_minutes("5:30")
    c = m.find(start, start + 65, needs_driving=True, recurring=False)
    assert c.helper.id == "maya"


def test_no_candidate_when_everyone_busy_or_unwilling():
    household = Household(me="justin", members=[
        Member("justin", "Justin"), Member("maya", "Maya"),
    ])
    timemap = TimeMap({"maya": [(17 * 60, 19 * 60)]})   # Maya busy at pickup
    consent = Consent({"maya": MemberConsent(True, True)})
    m = Matcher(household, timemap, consent)
    start = task_minutes("5:30")
    assert m.find(start, start + 65, needs_driving=True, recurring=False) is None


def test_pm_heuristic_reads_early_times_as_afternoon():
    assert task_minutes("5:30") == 17 * 60 + 30
    assert task_minutes("9:00") == 9 * 60
    assert task_minutes("") is None
