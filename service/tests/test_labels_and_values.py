"""Label override (#tags), the labels endpoint, and the persistent protect list."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import connect, lock
from app.presence import Value, load_mock_values
from app.presence.values_repo import ValuesRepo

c = TestClient(app)


def _cat(line):
    return c.post("/enrich", json={"tasks": [line]}).json()["tasks"][0]["category"]


def test_labels_endpoint_lists_categories():
    labels = c.get("/labels").json()
    assert "admin" in labels and "presence" in labels and "recurring-meeting" in labels


def test_tag_overrides_auto_classification():
    assert _cat("xyzzy widget") != "recurring-meeting"          # nothing matches -> default
    assert _cat("xyzzy widget #recurring-meeting") == "recurring-meeting"


def test_protect_alias_defends():
    t = c.post("/enrich", json={"tasks": ["Bedtime #protect"]}).json()["tasks"][0]
    assert t["category"] == "presence" and t["lever"] == "protect"


def test_invalid_tag_is_ignored_and_stripped():
    t = c.post("/enrich", json={"tasks": ["Pay the water bill #nonsense"]}).json()["tasks"][0]
    assert t["category"] != "nonsense"
    assert "#" not in t["title"]


# ---- persistent protect list ----

@pytest.fixture
def clean_values():
    with lock(), connect() as db:
        db.execute("DELETE FROM values_protect")
    yield
    with lock(), connect() as db:
        db.execute("DELETE FROM values_protect")
    ValuesRepo(seed=load_mock_values().list())      # restore defaults for other tests


def test_values_persist_across_instances(clean_values):
    ValuesRepo().add(Value(id="yoga", label="Yoga", minutes=30, when="07:00", priority=1))
    assert any(v.id == "yoga" for v in ValuesRepo().list())     # a fresh instance sees it


def test_value_remove(clean_values):
    r = ValuesRepo()
    r.add(Value(id="run", label="Evening run", minutes=40, when="18:00", priority=2))
    assert r.remove("run") is True
    assert not any(v.id == "run" for v in ValuesRepo().list())
    assert r.remove("run") is False                             # already gone


def test_seed_only_when_empty(clean_values):
    seed = [Value(id="a", label="A", minutes=10, when="", priority=1)]
    ValuesRepo(seed=seed)
    ValuesRepo(seed=[Value(id="b", label="B", minutes=10, when="", priority=1)])  # non-empty now
    ids = {v.id for v in ValuesRepo().list()}
    assert "a" in ids and "b" not in ids                        # second seed ignored
