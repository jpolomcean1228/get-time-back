"""Engine sanity tests — the contract Phase 1 must not break."""
import os
import tempfile

from app.engine import LearnedEstimator, RulesEstimator, Task, credit, kind
from app.engine.rules import classify
from app.store import ActualsStore


def test_classifier_buckets():
    assert classify("Weekly status sync 9:00") == "recurring-meeting"
    assert classify("Read to the kids at bedtime") == "presence"
    assert classify("Grocery run + pharmacy") == "errand"
    assert classify("Laundry") == "chore"
    assert classify("Pick up kids from basketball") == "family-logistics"


def test_presence_is_protected_not_credited():
    est = RulesEstimator().estimate(Task(raw="Dinner with Sarah", title="Dinner with Sarah"))
    assert est.lever == "protect"
    assert kind(est) == "presence"
    assert credit(est) == 0


def test_chore_credits_the_wait():
    est = RulesEstimator().estimate(Task(raw="Laundry", title="Laundry"))
    assert est.lever == "overlap"
    assert credit(est) == est.wait  # you get the waiting time back


def test_learned_estimator_shrinks_toward_actuals():
    with tempfile.TemporaryDirectory() as d:
        store = ActualsStore(os.path.join(d, "test.db"))
        learned = LearnedEstimator(RulesEstimator(), store, prior_weight=3.0)

        # cold: no history -> trusts the rules baseline, zero confidence
        cold = learned.estimate(Task(raw="Expense report", title="Expense report"))
        assert cold.confidence == 0.0
        baseline_active = cold.active

        # record several real completions far below the baseline estimate
        for _ in range(6):
            store.record("admin", active=10, total=10)

        warm = learned.estimate(Task(raw="Expense report", title="Expense report"))
        assert warm.confidence > 0.6                 # observed data now dominates
        assert warm.active < baseline_active         # estimate moved toward reality
        assert warm.active > 10                       # but not all the way (prior still pulls)
