"""Feedback harness tests: threshold tuning, suppression, store, learned prefs."""
from types import SimpleNamespace as NS

import pytest

from app.agent import Prefs, run_cycle
from app.agent.feedback import FeedbackStore, _suppressed, _threshold
from app.db import connect, lock


# ---- pure tuning functions ---------------------------------------------------

def _r(kind="protect", value=45, interrupt=True, verdict="rejected"):
    return {"kind": kind, "value_minutes": value, "interrupt": 1 if interrupt else 0,
            "verdict": verdict, "suggestion_id": f"{kind}:x"}


def test_threshold_default_on_thin_evidence():
    assert _threshold([]) == 45
    assert _threshold([_r()]) == 45                       # 1 reject < min sample


def test_threshold_rises_above_rejected_band():
    rows = [_r(value=45), _r(value=48), _r(value=50)]     # 3 dismissed interrupts
    assert _threshold(rows) == 55                         # max(50) + 5


def test_threshold_respects_accepted_band():
    rows = [_r(value=50), _r(value=52), _r(value=55),     # rejects would push to 60
            _r(value=40, verdict="accepted")]             # but a 40m was welcomed
    assert _threshold(rows) == 40                         # don't rise past what they accept


def test_suppressed_when_acceptance_low():
    rows = [_r(kind="reclaim", verdict="rejected") for _ in range(4)]
    assert "reclaim" in _suppressed(rows)


def test_not_suppressed_with_decent_acceptance():
    rows = [_r(kind="handoff", verdict="accepted") for _ in range(3)] + \
           [_r(kind="handoff", verdict="rejected")]       # 75% accepted
    assert "handoff" not in _suppressed(rows)


# ---- persistent store --------------------------------------------------------

@pytest.fixture
def store():
    s = FeedbackStore()
    with lock(), connect() as c:
        c.execute("DELETE FROM agent_feedback")
    yield s
    with lock(), connect() as c:
        c.execute("DELETE FROM agent_feedback")


def test_store_roundtrip_and_stats(store):
    store.record("protect:walk", "protect", 45, True, "rejected")
    store.record("protect:walk", "protect", 45, True, "rejected")
    store.record("handoff:x", "handoff", 65, True, "accepted")
    st = store.stats()
    assert st["total"] == 3
    assert st["by_kind"]["protect"]["rejected"] == 2
    assert "protect:walk" in store.prefs().rejected_ids


def test_store_rejects_bad_verdict(store):
    with pytest.raises(ValueError):
        store.record("x", "protect", 45, True, "maybe")


# ---- learned prefs applied in a cycle ---------------------------------------

def _action(i, label="Do"):
    return NS(id=i, label=label)


def _block(v="Walk", m=45, when="18:00", i="b"):
    return NS(value=v, minutes=m, when=when, action=_action(i))


def _presence(reclaimable=0, allocated=0, banked=0, blocks=None):
    return NS(reclaimable=reclaimable, allocated=allocated, banked=banked, blocks=blocks or [])


def _task(kind="logistics", reclaim=0, frag=0, action=None, coordination=None, title="t",
          why="w", when="", travel=0):
    return NS(kind=kind, reclaim=reclaim, frag=frag, action=action, coordination=coordination,
              title=title, why=why, when=when, travel=travel)


def test_no_prefs_matches_default():
    p = _presence(allocated=45, blocks=[_block(m=45, i="pb")])
    assert any(s.interrupt for s in run_cycle([], p).suggestions)


def test_rejected_id_is_dropped():
    p = _presence(allocated=45, blocks=[_block(v="Walk", m=45, i="pb")])
    prefs = Prefs(interrupt_min=45, suppressed_kinds=frozenset(),
                  rejected_ids=frozenset({"protect:walk"}))
    out = run_cycle([], p, prefs)
    assert all("walk" not in s.id for s in out.suggestions)


def test_raised_threshold_reduces_interrupts():
    p = _presence(allocated=45, blocks=[_block(m=45, i="pb")])
    prefs = Prefs(interrupt_min=60, suppressed_kinds=frozenset(), rejected_ids=frozenset())
    assert run_cycle([], p, prefs).interrupt_count == 0     # 45 < 60


def test_suppressed_kind_never_interrupts():
    t = _task(reclaim=65, coordination=NS(reason="Maya"),
              action=_action("h", "Ask Maya"), title="drive")
    prefs = Prefs(interrupt_min=45, suppressed_kinds=frozenset({"handoff"}),
                  rejected_ids=frozenset())
    assert run_cycle([t], _presence(), prefs).interrupt_count == 0


# ---- edit-learning + decay ---------------------------------------------------

def test_preferred_edit_learned(store):
    for _ in range(2):
        store.record("handoff:x", "handoff", 65, True, "edited", edited_to="Grandma")
    assert store.prefs().preferred_edits == {"handoff:x": "Grandma"}


def test_single_edit_not_yet_a_preference(store):
    store.record("handoff:x", "handoff", 65, True, "edited", edited_to="Grandma")
    assert store.prefs().preferred_edits == {}


def test_edits_count_as_wanted_not_suppressed():
    rows = [_r(kind="reclaim", verdict="edited") for _ in range(4)]
    assert "reclaim" not in _suppressed(rows)          # an edit is positive engagement


def test_decay_ignores_old_feedback(store):
    with lock(), connect() as c:                        # three rejects, 200 days ago
        for v in (50, 52, 55):
            c.execute("INSERT INTO agent_feedback "
                      "(user_id,suggestion_id,kind,value_minutes,interrupt,verdict,created_at) "
                      "VALUES (NULL,?,?,?,1,'rejected',datetime('now','-200 days'))",
                      ("protect:x", "protect", v))
    assert store.prefs().interrupt_min == 45            # decayed -> default
    for v in (50, 52, 55):                              # fresh rejects do move it
        store.record("protect:x", "protect", v, True, "rejected")
    assert store.prefs().interrupt_min == 60            # max(55)+5
