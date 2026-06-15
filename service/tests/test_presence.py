"""Presence loop tests — the values planner and real defense."""
from app.actions import MockExecutor
from app.presence import (DefendingExecutor, PresencePlanner, ProtectedBlocks,
                          Value, load_mock_values)


def _values():
    return [
        Value("bedtime", "Read to the kids", 30, "20:00", 1),
        Value("walk", "A walk", 45, "18:00", 2),
        Value("dinner", "Dinner", 60, "19:00", 3),
    ]


def test_planner_spends_budget_in_priority_order_and_banks_the_rest():
    plan = PresencePlanner().plan(reclaimable=90, values=_values())
    # 90 funds bedtime (30) + walk (45) = 75; dinner (60) doesn't fit
    labels = [b.label for b in plan.blocks]
    assert labels == ["Read to the kids", "A walk"]
    assert plan.allocated == 75
    assert plan.banked == 15            # leftover is banked, not refilled


def test_planner_funds_nothing_when_budget_too_small():
    plan = PresencePlanner().plan(reclaimable=10, values=_values())
    assert plan.blocks == []
    assert plan.allocated == 0 and plan.banked == 10


def test_blocks_carry_a_protect_action_with_a_window():
    plan = PresencePlanner().plan(reclaimable=200, values=_values())
    a = plan.blocks[0].action
    assert a.lever == "protect" and a.type == "block_time"
    assert a.start_min == 20 * 60 and a.end_min == 20 * 60 + 30


def test_confirming_a_block_defends_it_undo_releases_it():
    protected = ProtectedBlocks()
    ex = DefendingExecutor(MockExecutor(), protected)
    plan = PresencePlanner().plan(reclaimable=200, values=_values())
    block = plan.blocks[0]            # bedtime 20:00-20:30

    assert not protected.defends(20 * 60, 20 * 60 + 30)   # nothing yet
    ex.execute(block.action)
    assert protected.defends(20 * 60 + 10, 20 * 60 + 40)  # now defended (overlap)
    assert not protected.defends(21 * 60, 22 * 60)        # outside is fine
    ex.undo(block.action)
    assert not protected.defends(20 * 60, 20 * 60 + 30)   # released


def test_mock_values_fixture_loads():
    vs = load_mock_values()
    assert len(vs.list()) >= 1
    assert vs.list()[0].priority <= vs.list()[-1].priority
