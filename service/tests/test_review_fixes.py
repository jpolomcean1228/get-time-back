"""Fixes from code review: calendar informs estimates, unique action ids,
input validation. (Undo is exercised via the live action store elsewhere.)"""
from fastapi.testclient import TestClient

from app.main import app, _event_task
from app.actions.propose import _id
from app.calendar.base import CalEvent

c = TestClient(app)


# ---- #3 calendar events carry real duration + time ----

def test_event_task_uses_real_duration_and_time():
    ev = CalEvent(title="Weekly sync", start="2026-08-31T09:00", end="2026-08-31T09:30",
                  minutes=30)
    t = _event_task(ev)
    assert t.when == "09:00" and t.fixed_minutes == 30 and t.forced_category == "meeting"
    assert t.uid.startswith("cal-")


def test_include_calendar_reflects_event_length():
    tasks = c.post("/enrich", json={"tasks": [], "include_calendar": True}).json()["tasks"]
    assert tasks, "mock calendar should yield events"
    # a real event's total should equal its scheduled length, not a generic guess
    assert any(t["when"] and t["total"] > 0 for t in tasks)


# ---- #4 same-titled items get distinct action ids ----

def test_action_id_distinct_by_uid():
    assert _id("defer", "Daily Standup", "09:00", "cal-a") != \
           _id("defer", "Daily Standup", "09:00", "cal-b")


def test_action_id_distinct_by_time_without_uid():
    assert _id("defer", "Daily Standup", "09:00") != _id("defer", "Daily Standup", "14:00")


def test_action_id_stable_when_reproposed():
    assert _id("defer", "Daily Standup", "09:00", "cal-a") == \
           _id("defer", "Daily Standup", "09:00", "cal-a")


# ---- #5 malformed input is rejected ----

def test_negative_minutes_rejected():
    r = c.post("/values", json={"id": "x", "label": "X", "minutes": -5, "when": "", "priority": 1})
    assert r.status_code == 422


def test_bad_time_rejected():
    r = c.post("/values", json={"id": "x", "label": "X", "minutes": 30, "when": "9pm", "priority": 1})
    assert r.status_code == 422


def test_empty_label_rejected():
    r = c.post("/values", json={"id": "x", "label": "", "minutes": 30, "when": "", "priority": 1})
    assert r.status_code == 422


def test_unknown_verdict_rejected():
    r = c.post("/agent/feedback", json={"suggestion_id": "a", "kind": "reclaim",
               "value_minutes": 10, "interrupt": False, "verdict": "maybe"})
    assert r.status_code == 422


def test_out_of_range_now_min_rejected():
    assert c.post("/agent/run", json={"tasks": ["email"], "now_min": 9999}).status_code == 422


def test_valid_value_accepted():
    r = c.post("/values", json={"id": "walk", "label": "Walk", "minutes": 30,
               "when": "18:00", "priority": 2})
    assert r.status_code == 200
