"""CalendarExecutor tests — real write/delete behaviour against a fake writer."""
from app.actions import CalendarExecutor, MockExecutor
from app.actions.base import BLOCK_TIME, DRAFT_MESSAGE, Action
from app.calendar import MockCalendarWriter


def _block():
    return Action(id="protect:bedtime", type=BLOCK_TIME, lever="protect",
                  label='Protect "Read to the kids"', detail="",
                  start_min=20 * 60, end_min=20 * 60 + 30)


def test_block_action_creates_then_deletes_a_calendar_event():
    writer = MockCalendarWriter()
    ex = CalendarExecutor(MockExecutor(), writer)
    a = _block()

    msg = ex.execute(a)
    assert "calendar" in msg.lower()
    assert a.external_id != ""              # event id captured for undo
    assert len(writer.created) == 1
    assert writer.created[0][1] == "Read to the kids"   # clean summary

    eid = a.external_id
    ex.undo(a)
    assert writer.deleted == [eid]          # deleted exactly that event
    assert a.external_id == ""              # cleared


def test_non_block_actions_delegate_to_base():
    writer = MockCalendarWriter()
    ex = CalendarExecutor(MockExecutor(), writer)
    a = Action(id="delegate:x", type=DRAFT_MESSAGE, lever="delegate",
               label="Ask Maya", detail="")
    msg = ex.execute(a)
    assert "draft" in msg.lower()           # came from MockExecutor
    assert writer.created == []             # writer untouched
