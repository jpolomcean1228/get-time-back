"""Get Time Back — Phase 1 API.

Assembles the engine at startup:
    base = LLMEstimator if ANTHROPIC_API_KEY else RulesEstimator
    engine = LearnedEstimator(base, store)   # corrects toward actuals

Run:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for the interactive API.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .actions import ActionStore, MockExecutor, propose
from .calendar import MockCalendarProvider
from .engine import (LLMEstimator, LearnedEstimator, RulesEstimator, Task,
                     credit, kind, signature)
from .engine.levers import LEVERS
from .models import (ActionRef, ActualIn, CalendarEvent, EnrichedTask,
                     EnrichRequest, EnrichResponse, ProposedAction, Totals)
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
calendar = MockCalendarProvider()
actions = ActionStore(MockExecutor())

_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")


def _parse(line: str) -> Task:
    m = _TIME_RE.search(line)
    when = m.group(1) if m else ""
    title = _TIME_RE.sub("", line).strip(" -\t")
    return Task(raw=line, title=title, when=when)


def _action_model(a) -> ProposedAction:
    return ProposedAction(id=a.id, type=a.type, lever=a.lever, label=a.label,
                          detail=a.detail, body=a.body, reversible=a.reversible,
                          status=a.status, result=a.result)


def _to_out(est, action=None) -> EnrichedTask:
    rec = credit(est)
    return EnrichedTask(
        title=est.title, when=est.when, category=est.category,
        active=est.active, wait=est.wait, travel=est.travel, frag=est.frag,
        total=est.total, lever=est.lever, lever_label=LEVERS.get(est.lever, est.lever),
        why=est.why, reclaim=rec, kind=kind(est),
        confidence=est.confidence, learn_level=est.learn_level, source=est.source,
        action=_action_model(action) if action else None,
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
        if req.include_actions:
            proposed = propose(est)
            if proposed is not None:
                act = actions.propose(proposed)   # register; idempotent
        out.append(_to_out(est, act))

    committed = sum(t.total for t in out if t.kind == "logistics")
    reclaimable = sum(t.reclaim for t in out)
    presence = sum(t.total for t in out if t.kind == "presence")

    return EnrichResponse(
        tasks=out,
        totals=Totals(committed=committed, reclaimable=reclaimable, presence=presence),
        engine=ENGINE_NAME,
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
