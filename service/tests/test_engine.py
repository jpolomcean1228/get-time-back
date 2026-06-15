"""Engine sanity tests — the contract Phases 1 & 2 must not break."""
import os
import tempfile

from app.engine import (LearnedEstimator, RulesEstimator, Task, credit, kind,
                        signature)
from app.engine.rules import classify
from app.engine.signature import normalize
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


def test_signature_is_order_independent_and_drops_noise():
    assert normalize("Grocery run + pharmacy") == normalize("pharmacy, grocery run")
    assert signature("Laundry", "chore") == "chore:laundry"
    assert signature("Dentist 2:00", "appointment") == "appointment:dentist"


def test_learned_falls_back_to_category_then_prefers_specific():
    with tempfile.TemporaryDirectory() as d:
        store = ActualsStore(os.path.join(d, "test.db"))
        learned = LearnedEstimator(RulesEstimator(), store, prior_weight=3.0, min_specific=2)

        # cold: no history
        cold = learned.estimate(Task(raw="Laundry", title="Laundry"))
        assert cold.confidence == 0.0 and cold.learn_level == ""
        baseline = cold.total

        # one specific sample is below the min_specific threshold -> still category (none) 
        store.record(signature("Laundry", "chore"), "chore", 12, 110)
        one = learned.estimate(Task(raw="Laundry", title="Laundry"))
        # category bucket now has 1 row, so it learns at category level
        assert one.learn_level == "category"

        # add more specific samples -> now it prefers the specific bucket
        store.record(signature("Laundry", "chore"), "chore", 12, 110)
        store.record(signature("Laundry", "chore"), "chore", 12, 110)
        warm = learned.estimate(Task(raw="Laundry", title="Laundry"))
        assert warm.learn_level == "specific"
        assert warm.total > baseline          # moved toward the observed 110
        assert warm.confidence > 0.4

        # a different chore with no specific history backs off to the category avg
        other = learned.estimate(Task(raw="Wash the dishes", title="Wash the dishes"))
        assert other.learn_level == "category"
