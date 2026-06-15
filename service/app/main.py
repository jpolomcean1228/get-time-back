"""Get Time Back — Phase 1 API.

Assembles the engine at startup:
    base = LLMEstimator if ANTHROPIC_API_KEY else RulesEstimator
    engine = LearnedEstimator(base, store)   # corrects toward actuals

Run:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for the interactive API.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .actions import (ActionStore, CalendarExecutor, MockExecutor, propose,
                      propose_handoff)
from .calendar import MockCalendarProvider, MockCalendarWriter
from .engine import (LLMEstimator, LearnedEstimator, RulesEstimator, Task,
                     credit, kind, signature)
from .engine.levers import LEVERS
from .household import Matcher, load_mock_household, task_minutes
from .models import (ActionRef, ActualIn, CalendarEvent, CoordinationOut,
                     EnrichedTask, EnrichRequest, EnrichResponse,
                     PresenceBlockOut, PresencePlanOut, ProposedAction, Totals,
                     ValueIn)
from .presence import (DefendingExecutor, PresencePlanner, ProtectedBlocks,
                       Value, load_mock_values)
from .store import ActualsStore

app = FastAPI(title="Get Time Back", version="0.1.0",
              description="Phase 1 — true-time estimation that learns from actuals.")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# --- engine assembly -------------------------------------------------------
store = ActualsStore()
_llm = LLMEstimator()
_base = _llm if _llm.available else RulesEstimator()
engine = LearnedEstimator(_base, store)
ENGINE_NAME = "llm" if _llm.available else "rules"
def _make_calendar():
    """Use the real Google calendar if credentials are configured, else the mock.

    Selection is by credentials-file presence only; the OAuth flow itself is
    deferred to the first today() call, so this never blocks startup.
    """
    cred = os.environ.get("GTB_GOOGLE_CREDENTIALS")
    if cred and Path(cred).exists():
        try:
            from .calendar import GoogleCalendarProvider
            return GoogleCalendarProvider(cred, os.environ.get("GTB_GOOGLE_TOKEN", "token.json"))
        except Exception:
            pass
    return MockCalendarProvider()


def _make_calendar_writer():
    """Real calendar writer when write is explicitly enabled, else the mock."""
    cred = os.environ.get("GTB_GOOGLE_CREDENTIALS")
    write_on = os.environ.get("GTB_CALENDAR_WRITE", "").lower() in ("1", "true", "yes")
    if cred and write_on and Path(cred).exists():
        try:
            from .calendar import GoogleCalendarWriter
            return GoogleCalendarWriter(cred, os.environ.get("GTB_GOOGLE_WRITE_TOKEN", "token_write.json"))
        except Exception:
            pass
    return MockCalendarWriter()


calendar = _make_calendar()
protected = ProtectedBlocks()
# block_time actions write to the calendar; everything else stays mock.
# DefendingExecutor registers the protected window; CalendarExecutor writes the event.
actions = ActionStore(DefendingExecutor(CalendarExecutor(MockExecutor(), _make_calendar_writer()), protected))
household, timemap, consent = load_mock_household()
matcher = Matcher(household, timemap, consent)
values_store = load_mock_values()
planner = PresencePlanner()

_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")


def _parse(line: str) -> Task:
    m = _TIME_RE.search(line)
    when = m.group(1) if m else ""
    title = _TIME_RE.sub("", line).strip(" -\t")
    return Task(raw=line, title=title, when=when)


def _action_model(a) -> ProposedAction:
    return ProposedAction(id=a.id, type=a.type, lever=a.lever, label=a.label,
                          detail=a.detail, body=a.body, target=a.target,
                          reversible=a.reversible, status=a.status, result=a.result)


def _to_out(est, action=None, coordination=None) -> EnrichedTask:
    rec = credit(est)
    return EnrichedTask(
        title=est.title, when=est.when, category=est.category,
        active=est.active, wait=est.wait, travel=est.travel, frag=est.frag,
        total=est.total, lever=est.lever, lever_label=LEVERS.get(est.lever, est.lever),
        why=est.why, reclaim=rec, kind=kind(est),
        confidence=est.confidence, learn_level=est.learn_level, source=est.source,
        action=_action_model(action) if action else None,
        coordination=coordination,
    )


@app.get("/health")
def health():
    return {"ok": True, "engine": ENGINE_NAME}


# serve the Phase 0 demo UI from the repo root, same origin as the API
_INDEX = Path(__file__).resolve().parents[2] / "index.html"


@app.get("/")
def home():
    if _INDEX.exists():
        return FileResponse(_INDEX)
    return {"service": "get-time-back", "docs": "/docs"}


@app.post("/enrich", response_model=EnrichResponse)
def enrich(req: EnrichRequest):
    lines = [l.strip() for l in req.tasks if l.strip()]
    if req.include_calendar:
        lines += [ev.title for ev in calendar.today()]

    out = []
    for l in lines:
        est = engine.estimate(_parse(l))
        act = None
        coord_out = None
        if req.include_actions:
            coord = None
            if est.lever == "delegate":
                start = task_minutes(est.when)
                if start is not None:
                    needs_driving = est.category == "family-logistics"
                    recurring = est.category == "family-logistics"
                    coord = matcher.find(start, start + est.total, needs_driving, recurring)
            if coord is not None:
                act = actions.propose(propose_handoff(est, coord, household.my_name))
                coord_out = CoordinationOut(helper=coord.helper.name, window=coord.window,
                                            reason=coord.reason, kind=coord.kind)
            else:
                proposed = propose(est)
                if proposed is not None:
                    act = actions.propose(proposed)   # generic fallback
        out.append(_to_out(est, act, coord_out))

    committed = sum(t.total for t in out if t.kind == "logistics")
    reclaimable = sum(t.reclaim for t in out)
    presence = sum(t.total for t in out if t.kind == "presence")

    presence_plan = None
    if req.include_actions:
        plan = planner.plan(reclaimable, values_store.list())
        blocks = []
        for b in plan.blocks:
            actions.propose(b.action)          # register; idempotent
            blocks.append(PresenceBlockOut(value=b.label, minutes=b.minutes,
                                           when=b.when, action=_action_model(b.action)))
        presence_plan = PresencePlanOut(reclaimable=plan.reclaimable,
                                        allocated=plan.allocated, banked=plan.banked,
                                        blocks=blocks)

    return EnrichResponse(
        tasks=out,
        totals=Totals(committed=committed, reclaimable=reclaimable, presence=presence),
        engine=ENGINE_NAME,
        presence=presence_plan,
    )


@app.post("/actuals")
def record_actual(a: ActualIn):
    """Close the loop: log what a task really took so estimates improve.

    Recorded under the specific signature (category + normalized title) so a
    recurring item learns its own timing, with the category as the fallback.
    """
    sig = signature(a.title, a.category) if a.title else a.category
    store.record(sig, a.category, a.active_minutes, a.total_minutes)
    n_specific, _, mean_specific = store.stats(sig)
    n_category, _, mean_category = store.stats_category(a.category)
    return {"recorded": True, "signature": sig,
            "specific": {"samples": n_specific, "mean_total": round(mean_specific, 1)},
            "category": {"samples": n_category, "mean_total": round(mean_category, 1)}}


@app.get("/calendar/today", response_model=list[CalendarEvent])
def calendar_today():
    return [CalendarEvent(**ev.__dict__) for ev in calendar.today()]


@app.get("/household")
def household_view():
    """The roster and each member's consent — the shared layer, made visible."""
    return {
        "me": household.me,
        "members": [
            {"id": m.id, "name": m.name, "can_drive": m.can_drive,
             "shares_availability": consent.shares(m.id),
             "accepts_handoffs": consent.accepts(m.id),
             "candidate": consent.is_candidate(m.id)}
            for m in household.all()
        ],
    }


# --- Phase 5: the values loop ----------------------------------------------
@app.get("/values", response_model=list[ValueIn])
def list_values():
    """What the user wants reclaimed time spent on, in priority order."""
    return [ValueIn(id=v.id, label=v.label, minutes=v.minutes, when=v.when,
                    priority=v.priority) for v in values_store.list()]


@app.post("/values", response_model=list[ValueIn])
def add_value(v: ValueIn):
    values_store.add(Value(id=v.id, label=v.label, minutes=v.minutes,
                           when=v.when, priority=v.priority))
    return list_values()


@app.get("/presence/protected")
def protected_blocks():
    """Blocks that have been confirmed and are now defended from encroachment."""
    return {"protected": protected.list()}


# --- Phase 3: the confirm gate ---------------------------------------------
@app.get("/actions", response_model=list[ProposedAction])
def list_actions():
    return [_action_model(a) for a in actions.list()]


@app.post("/actions/confirm", response_model=ProposedAction)
def confirm_action(ref: ActionRef):
    """The gate: execute a proposed action only on explicit confirmation."""
    a = actions.confirm(ref.id)
    if a is None:
        raise HTTPException(status_code=404, detail="No such proposed action")
    return _action_model(a)


@app.post("/actions/undo", response_model=ProposedAction)
def undo_action(ref: ActionRef):
    """Reverse an executed action."""
    a = actions.undo(ref.id)
    if a is None:
        raise HTTPException(status_code=404, detail="No such action")
    return _action_model(a)
