"""MessageExecutor tests — Gmail draft create/discard against a fake writer."""
from app.actions import MessageExecutor, MockExecutor
from app.actions.base import BLOCK_TIME, DRAFT_MESSAGE, Action
from app.messaging import MockMessageWriter


def test_draft_action_creates_then_discards_a_draft():
    writer = MockMessageWriter()
    ex = MessageExecutor(MockExecutor(), writer)
    a = Action(id="delegate:pickup", type=DRAFT_MESSAGE, lever="delegate",
               label="Ask Maya", detail="", body="Hi Maya — cover the pickup?",
               recipient="maya@example.com")

    msg = ex.execute(a)
    assert "draft" in msg.lower()
    assert a.external_id != ""
    assert len(writer.created) == 1
    assert writer.created[0][1] == "maya@example.com"   # drafted to the matched member

    did = a.external_id
    ex.undo(a)
    assert writer.deleted == [did]
    assert a.external_id == ""


def test_non_draft_actions_delegate_to_base():
    writer = MockMessageWriter()
    ex = MessageExecutor(MockExecutor(), writer)
    a = Action(id="overlap:laundry", type="delay_start", lever="overlap", label="Set delay-start", detail="")
    ex.execute(a)
    assert writer.created == []        # writer untouched for non-draft types
