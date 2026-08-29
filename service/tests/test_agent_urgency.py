"""Urgency tests: time-to-event + travel decide the leave-now interrupt."""
from types import SimpleNamespace as NS

from app.agent import run_cycle
from app.agent import urgency


def test_flexible_when_no_time():
    assert urgency.assess("", 10, 600) == ("flexible", None, False)


def test_leave_now_when_past_leave_by():
    # start 3:15 -> 15:15 (915); travel 20 -> leave_by 895 (14:55); now 15:00 (900)
    urg, _, override = urgency.assess("3:15", 20, 900)
    assert urg == "now" and override is True


def test_soon_within_window():
    urg, _, override = urgency.assess("3:15", 20, 880)   # leave_by 895, slack 15
    assert urg == "soon" and override is True


def test_today_when_far_out():
    urg, _, override = urgency.assess("3:15", 20, 600)   # slack ~295
    assert urg == "today" and override is False


def test_today_once_started():
    urg, _, override = urgency.assess("3:15", 20, 916)   # now past start
    assert urg == "today" and override is False


# ---- the override beats the value threshold ---------------------------------

def _action(i, label="Do"):
    return NS(id=i, label=label)


def _presence(reclaimable=0, allocated=0, banked=0, blocks=None):
    return NS(reclaimable=reclaimable, allocated=allocated, banked=banked, blocks=blocks or [])


def _task(reclaim, when, travel, coordination, title):
    return NS(kind="logistics", reclaim=reclaim, frag=0, action=_action("h", "Ask X"),
              coordination=coordination, title=title, why="w", when=when, travel=travel)


def test_leave_now_interrupts_low_value_handoff():
    # a 10-minute handoff would never clear the 45m threshold, but it's time-critical
    t = _task(10, "3:15", 20, NS(reason="X can drive"), "pickup")
    out = run_cycle([t], _presence(), now_min=900)       # inside leave-by window
    s = out.suggestions[0]
    assert s.value_minutes == 10 and s.interrupt is True and s.urgency == "now"


def test_same_handoff_waits_when_far_out():
    t = _task(10, "3:15", 20, NS(reason="X can drive"), "pickup")
    out = run_cycle([t], _presence(), now_min=600)       # hours before
    assert out.suggestions[0].interrupt is False
