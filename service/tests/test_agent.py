"""Agent tests: value weighting, suggestion build, interruption calculus, critique."""
from types import SimpleNamespace as NS

from app.agent import run_cycle
from app.agent import value, planner, critic


def _action(i, label="Do it"):
    return NS(id=i, label=label)


def _task(kind="logistics", reclaim=0, frag=0, action=None, coordination=None,
          title="t", why="because", when="", travel=0):
    return NS(kind=kind, reclaim=reclaim, frag=frag, action=action, coordination=coordination,
              title=title, why=why, when=when, travel=travel)


def _block(value_="Walk", minutes=45, when="18:00", i="b1"):
    return NS(value=value_, minutes=minutes, when=when, action=_action(i))


def _presence(reclaimable=0, allocated=0, banked=0, blocks=None):
    return NS(reclaimable=reclaimable, allocated=allocated, banked=banked,
              blocks=blocks or [])


def test_value_weights_presence_highest():
    tasks = [_task(kind="logistics", reclaim=0, frag=40)]
    p = _presence(reclaimable=60, allocated=60, banked=0)
    vs = value.score(tasks, p)
    # 60*1.5 + 60*1.0 - 40*0.5 = 90 + 60 - 20 = 130
    assert vs.score == 130.0
    assert vs.presence_protected == 60 and vs.fragmentation == 40


def test_value_prefers_protected_over_banked():
    tasks = []
    protect = value.score(tasks, _presence(reclaimable=60, allocated=60))
    bank = value.score(tasks, _presence(reclaimable=60, allocated=0, banked=60))
    assert protect.score > bank.score   # protecting beats banking, per the objective


def test_build_makes_protect_and_reclaim():
    tasks = [_task(reclaim=30, action=_action("a1", "Make it async"))]
    p = _presence(reclaimable=30, allocated=45, blocks=[_block(minutes=45, i="pb")])
    sugg = planner.build_suggestions(tasks, p)
    kinds = {s.kind for s in sugg}
    assert "protect" in kinds and "reclaim" in kinds


def test_interrupt_calculus_threshold():
    # a 45-min protect earns an interrupt; a 30-min one does not
    big = planner.build_suggestions([], _presence(blocks=[_block(minutes=45, i="x")]))
    small = planner.build_suggestions([], _presence(blocks=[_block(minutes=30, i="y")]))
    assert big[0].interrupt is True
    assert small[0].interrupt is False


def test_rank_interrupts_first_then_value():
    tasks = [
        _task(reclaim=65, coordination=NS(reason="Maya can drive"),
              action=_action("h", "Ask Maya")),            # handoff 65 -> interrupt
        _task(reclaim=20, action=_action("r", "Async")),   # reclaim 20 -> brief
    ]
    p = _presence(blocks=[_block(minutes=50, i="p")])       # protect 50 -> interrupt
    ranked = planner.rank(planner.build_suggestions(tasks, p))
    assert ranked[0].interrupt and ranked[1].interrupt      # both interrupts on top
    assert ranked[0].value_minutes >= ranked[1].value_minutes
    assert ranked[-1].interrupt is False                    # low-value reclaim last


def test_critique_flags_reclaim_without_presence():
    tasks = [_task(reclaim=80, action=_action("a"))]
    notes = critic.critique(tasks, _presence(reclaimable=80, allocated=0), [])
    assert any("protect none" in n for n in notes)


def test_critique_flags_over_delegation():
    handoffs = [NS(kind="handoff", interrupt=False) for _ in range(3)]
    notes = critic.critique([], _presence(allocated=30), handoffs)
    assert any("handing a lot off" in n for n in notes)


def test_run_cycle_counts_and_headline():
    tasks = [
        _task(reclaim=65, coordination=NS(reason="Maya"), action=_action("h", "Ask Maya")),
        _task(reclaim=20, action=_action("r", "Async")),
    ]
    p = _presence(reclaimable=85, allocated=45, banked=40, blocks=[_block(minutes=45, i="p")])
    brief = run_cycle(tasks, p)
    assert brief.interrupt_count == 2          # handoff 65 + protect 45
    assert brief.brief_count == 1              # reclaim 20
    assert brief.headline and "Reclaim" in brief.headline
    assert brief.score.presence_protected == 45
