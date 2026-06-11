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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .calendar import MockCalendarProvider
from .engine import (LLMEstimator, LearnedEstimator, RulesEstimator, Task,
                     credit, kind)
from .engine.levers import LEVERS
from .models import (ActualIn, CalendarEvent, EnrichedTask, EnrichRequest,
                     EnrichResponse, Totals)
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

_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")


def _parse(line: str) -> Task:
    m = _TIME_RE.search(line)
    when = m.group(1) if m else ""
    title = _TIME_RE.sub("", line).strip(" -\t")
    return Task(raw=line, title=title, when=when)


def _to_out(est) -> EnrichedTask:
    rec = credit(est)
    return EnrichedTask(
        title=est.title, when=est.when, category=est.category,
        active=est.active, wait=est.wait, travel=est.travel, frag=est.frag,
        total=est.total, lever=est.lever, lever_label=LEVERS.get(est.lever, est.lever),
        why=est.why, reclaim=rec, kind=kind(est),
        confidence=est.confidence, source=est.source,
    )


@app.get("/health")
def health():
    return {"ok": True, "engine": ENGINE_NAME}


@app.post("/enrich", response_model=EnrichResponse)
def enrich(req: EnrichRequest):
    lines = [l.strip() for l in req.tasks if l.strip()]
    if req.include_calendar:
        lines += [ev.title for ev in calendar.today()]

    out = [_to_out(engine.estimate(_parse(l))) for l in lines]

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
    """Close the loop: log what a task really took so estimates improve."""
    store.record(a.category, a.active_minutes, a.total_minutes)
    n, mean_active, mean_total = store.stats(a.category)
    return {"recorded": True, "signature": a.category,
            "samples": n, "mean_active": round(mean_active, 1),
            "mean_total": round(mean_total, 1)}


@app.get("/calendar/today", response_model=list[CalendarEvent])
def calendar_today():
    return [CalendarEvent(**ev.__dict__) for ev in calendar.today()]
