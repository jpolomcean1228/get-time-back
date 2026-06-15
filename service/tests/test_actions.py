"""Action layer tests — the Phase 3 confirm gate and reversibility."""
from app.actions import ActionStore, MockExecutor, propose
from app.engine import RulesEstimator, Task


def est(title):
    return RulesEstimator().estimate(Task(raw=title, title=title))


def test_levers_map_to_expected_actions():
    assert propose(est("Dinner with Sarah")).type == "block_time"     # protect
    assert propose(est("Pick up kids from basketball")).type == "draft_message"  # delegate
    assert propose(est("Grocery run + pharmacy")).type == "batch_errands"        # batch
    assert propose(est("Laundry")).type == "delay_start"              # overlap
    assert propose(est("Weekly status sync")).type == "async_update"  # automate


def test_proposing_is_idempotent():
    store = ActionStore(MockExecutor())
    a1 = store.propose(propose(est("Laundry")))
    a2 = store.propose(propose(est("Laundry")))
    assert a1.id == a2.id
    assert len(store.list()) == 1


def test_confirm_gate_then_undo():
    store = ActionStore(MockExecutor())
    a = store.propose(propose(est("Laundry")))
    assert a.status == "proposed" and a.result == ""

    confirmed = store.confirm(a.id)
    assert confirmed.status == "executed"
    assert "demo" in confirmed.result            # mock executor ran

    undone = store.undo(a.id)
    assert undone.status == "undone"
    assert undone.result == "Reverted."


def test_confirm_missing_action_returns_none():
    store = ActionStore(MockExecutor())
    assert store.confirm("nope:does-not-exist") is None
