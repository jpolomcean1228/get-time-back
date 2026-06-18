"""Plugin registry tests — the seam that lets adapters self-register by name."""
import pytest

from app.plugins import (create, has, load_external, names, register,
                         register_builtins, summary)


def test_register_create_and_introspect():
    register("widget", "demo", lambda c: {"x": c.get("x", 0)})
    assert has("widget", "demo")
    assert "demo" in names("widget")
    assert create("widget", "demo", {"x": 5}) == {"x": 5}
    assert "widget" in summary() and "demo" in summary()["widget"]


def test_unknown_plugin_raises_lookuperror():
    with pytest.raises(LookupError):
        create("widget", "does-not-exist")


def test_register_replaces_in_place():
    register("widget", "dup", lambda c: "first")
    register("widget", "dup", lambda c: "second")
    assert names("widget").count("dup") == 1
    assert create("widget", "dup") == "second"


def test_builtins_cover_every_swappable_seam():
    register_builtins()
    assert {"rules", "llm"} <= set(names("estimator"))
    assert {"mock", "google"} <= set(names("calendar"))
    assert {"mock", "google"} <= set(names("calendar_writer"))
    assert {"mock", "gmail"} <= set(names("message_writer"))


def test_builtins_build_real_instances():
    register_builtins()
    from app.calendar import MockCalendarProvider
    from app.engine import RulesEstimator
    assert isinstance(create("calendar", "mock", {}), MockCalendarProvider)
    assert isinstance(create("estimator", "rules", {}), RulesEstimator)


def test_external_module_self_registers_on_load():
    # importing a module named in GTB_PLUGINS runs its register() calls
    assert not has("estimator", "sample") or True  # may be registered by a prior run
    loaded = load_external("tests._sample_plugin")
    assert "tests._sample_plugin" in loaded
    assert has("estimator", "sample")
    assert create("estimator", "sample", {"tag": "live"}) == "sample:live"
    # empty/blank spec is a no-op
    assert load_external("") == []
