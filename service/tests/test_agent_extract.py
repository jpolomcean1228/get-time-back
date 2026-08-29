"""Commitment-extraction tests: pull real tasks, skip chatter."""
from app.agent.extract import extract, _rule_extract
from app.agent import sources as src


def _tasks(text):
    return [c.task for c in extract(text)]


def test_extracts_a_request():
    out = _tasks("Could you send me the Q3 numbers by Tuesday?")
    assert any("send" in t.lower() and "q3" in t.lower() for t in out)


def test_extracts_a_reminder():
    out = _tasks("Don't forget to book the dentist for the kids.")
    assert any("book the dentist" in t.lower() for t in out)


def test_appends_deadline():
    out = _tasks("Please sign the field trip form due Thursday.")
    assert any("thursday" in t.lower() for t in out)


def test_skips_chatter():
    assert extract("Hope you had a great weekend! Talk soon.") == []
    assert extract("Thanks so much, really appreciate it.") == []


def test_dedupes():
    txt = "Please send the form. Can you send the form?"
    assert len(_tasks(txt)) == 1


def test_empty_text():
    assert extract("") == [] and extract("   ") == []


def test_confidence_is_bounded():
    for c in _rule_extract("Please send the report by Friday, don't forget!"):
        assert 0.0 < c.confidence <= 0.95


def test_harvest_mock_inbox_dedupes_and_tags_source():
    commits = src.harvest(src.mock_inbox(), extract)
    assert len(commits) >= 3
    assert all(c.source for c in commits)              # each tagged with its sender
    tasks = [c.task.lower() for c in commits]
    assert len(tasks) == len(set(tasks))               # deduped across messages


def test_harvest_finds_the_q3_ask():
    commits = src.harvest(src.mock_inbox(), extract)
    assert any("q3" in c.task.lower() for c in commits)
