"""Engine sanity tests — the contract Phases 1 & 2 must not break."""
import os
import tempfile

from app.engine import (LearnedEstimator, RulesEstimator, Task, credit, kind,
                        lever_label, register_lever, signature)
from app.engine.levers import LEVERS
from app.engine.profiles import Profile, ProfileStore, load_profiles
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


# --- profiles: the rules table is data, not code --------------------------
def test_fixture_loads_and_classifies_the_known_buckets():
    store = load_profiles()
    assert store.classify("Weekly status sync 9:00") == "recurring-meeting"
    assert store.classify("Read to the kids at bedtime") == "presence"
    # nothing matches -> the default bucket
    assert store.classify("Reticulate the splines") == "task"
    # every profile resolves, including the default fallback
    assert store.get("chore").lever == "overlap"
    assert store.get("does-not-exist").category == "task"


def test_added_profile_classifies_before_the_default():
    store = ProfileStore(load_profiles().list())
    assert store.classify("Walk the dog around the block") == "task"  # before
    store.add(Profile(category="pet", active=15, wait=0, travel=0, frag=5,
                      lever="batch", why="Stack it with the school run.",
                      keywords=("walk the dog", "feed the cat", "vet")))
    assert store.classify("Walk the dog around the block") == "pet"
    est = RulesEstimator(store).estimate(Task(raw="Walk the dog", title="Walk the dog"))
    assert est.category == "pet" and est.lever == "batch"


def test_added_profile_replaces_existing_category_in_place():
    store = ProfileStore(load_profiles().list())
    before = len(store.list())
    store.add(Profile(category="chore", active=5, wait=5, travel=0, frag=0,
                      lever="eliminate", why="Just skip it.", keywords=("laundry",)))
    assert len(store.list()) == before          # replaced, not appended
    assert store.get("chore").lever == "eliminate"


# --- levers: a registry, credit is a lookup --------------------------------
def test_credit_formulas_for_each_lever():
    est = RulesEstimator().estimate(Task(raw="Grocery run", title="Grocery run"))
    assert est.lever == "batch"
    assert credit(est) == est.travel           # batch reclaims the travel


def test_unknown_lever_credits_zero_and_labels_to_its_name():
    est = RulesEstimator().estimate(Task(raw="Laundry", title="Laundry"))
    est.lever = "nonsense"                      # a profile may name a lever not yet registered
    assert credit(est) == 0
    assert lever_label("nonsense") == "nonsense"


def test_registering_a_lever_makes_it_usable_and_visible():
    register_lever("halve", "Halve it", lambda e: e.active // 2)
    assert "halve" in LEVERS and lever_label("halve") == "Halve it"
    est = RulesEstimator().estimate(Task(raw="Laundry", title="Laundry"))
    est.lever = "halve"
    assert credit(est) == est.active // 2
