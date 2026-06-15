"""Google Calendar parsing tests — pure mapping, no network or Google libs."""
from app.calendar.google import to_calevent


def test_timed_event_with_offset():
    item = {
        "summary": "Weekly status sync",
        "start": {"dateTime": "2026-06-15T09:00:00-07:00"},
        "end":   {"dateTime": "2026-06-15T09:30:00-07:00"},
        "attendees": [{"email": "a@x.com"}, {"email": "b@x.com"}],
        "location": "Room 4",
    }
    ev = to_calevent(item)
    assert ev.title == "Weekly status sync"
    assert ev.minutes == 30
    assert ev.attendees == 2
    assert ev.location == "Room 4"


def test_timed_event_with_z_suffix():
    # Py3.9 fromisoformat can't take 'Z'; the parser must normalize it
    item = {
        "summary": "Dentist",
        "start": {"dateTime": "2026-06-15T21:00:00Z"},
        "end":   {"dateTime": "2026-06-15T22:00:00Z"},
    }
    ev = to_calevent(item)
    assert ev.minutes == 60
    assert ev.attendees == 1          # default when no attendees


def test_all_day_event_is_skipped():
    item = {"summary": "Holiday", "start": {"date": "2026-06-15"}, "end": {"date": "2026-06-16"}}
    assert to_calevent(item) is None


def test_missing_summary_defaults():
    item = {"start": {"dateTime": "2026-06-15T10:00:00+00:00"},
            "end": {"dateTime": "2026-06-15T10:15:00+00:00"}}
    ev = to_calevent(item)
    assert ev.title == "(no title)" and ev.minutes == 15
