# Get Time Back — estimation service (Phase 1)

The first real backend. It promotes the three Phase 0 functions into a
pluggable engine and adds the two things Phase 1 is about: **estimates that
learn from actuals**, and **read-only calendar** input.

## Run it

```bash
cd service
python -m venv .venv && source .venv/bin/activate    # optional
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive API, or
**http://127.0.0.1:8000/** for the live demo UI — the Phase 0 frontend is now
served from the same origin, so it calls this engine with no CORS setup and
shows confidence climbing as you log actuals. With no API key it runs on the
deterministic rules engine — no setup, no network. Add an `ANTHROPIC_API_KEY`
in `.env` to switch the first-pass estimates to Claude.

```bash
pytest          # run the engine + learning-loop tests
```

## How it's wired

```
            ┌──────────────────────────────────────────┐
  task ───▶ │  base estimator   (RulesEstimator  OR     │
            │                    LLMEstimator → Claude) │ first-pass estimate
            └───────────────────┬──────────────────────┘
                                ▼
            ┌──────────────────────────────────────────┐
            │  LearnedEstimator                         │ corrects toward
            │  blends estimate with recorded actuals    │ observed reality
            └───────────────────┬──────────────────────┘
                                ▼
            ┌──────────────────────────────────────────┐
            │  levers.credit()  → minutes reclaimed     │
            └──────────────────────────────────────────┘
```

The estimators are interchangeable behind one `Estimator` protocol
(`app/engine/base.py`). That's the seam: swap rules for LLM, or wrap either in
the learned layer, without touching the API.

### The learning loop

`LearnedEstimator` corrects a first-pass estimate toward the mean of recorded
actuals using a shrinkage blend:

```
corrected = estimate · k/(k+n)  +  observed_mean · n/(k+n)
```

With no history (`n=0`) it trusts the estimate. As actuals accumulate, observed
reality takes over. `confidence = n/(n+k)` is exactly that observed weight, so
the number shown to the user is the number doing the math. `k` (prior weight)
lives in `learned.py`.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | liveness + which engine is active |
| POST | `/enrich` | enrich a day → per-task levers + totals (+ proposed actions) |
| POST | `/actuals` | log a real completion (closes the loop) |
| GET  | `/calendar/today` | today's events (read-only) |
| GET  | `/actions` | list proposed / executed actions |
| POST | `/actions/confirm` | execute a proposed action — the confirm gate |
| POST | `/actions/undo` | reverse an executed action |

`POST /enrich`
```json
{ "tasks": ["Weekly status sync 9:00", "Laundry", "Dinner with Sarah 7:30"],
  "include_calendar": false }
```

`POST /actuals`
```json
{ "category": "chore", "active_minutes": 12, "total_minutes": 110 }
```

## Layout

```
app/
  main.py            FastAPI app + engine assembly
  models.py          request/response schemas
  engine/
    base.py          Estimate + Estimator protocol  (the seam)
    rules.py         deterministic baseline (Phase 0 port)
    llm.py           Claude first-pass, falls back to rules
    learned.py       shrinkage correction toward actuals
    levers.py        lever set + credit() + logistics/presence split
  store/
    actuals.py       SQLite feedback store
  calendar/
    base.py          CalendarProvider protocol
    mock.py          fixture-backed provider (runs keyless)
    google.py        read-only OAuth stub + wiring checklist
  fixtures/
    sample_calendar.json
tests/
  test_engine.py     classifier, levers, and the learning loop
```

## What's deliberately stubbed (and where Phase 4 picks up)

- `GoogleCalendarProvider` (read) and `CalendarExecutor` / `MessageExecutor`
  (write) are documented stubs; `MockCalendarProvider` and `MockExecutor` serve
  the same interfaces so everything runs today with no credentials.
- Everything is single-user. The household / multi-party layer is Phase 4.

## Phase 3 — action layer with a confirm gate (done)

Recommendations can now become reversible actions. Each lever proposes one
concrete move (`app/actions/propose.py`): protect → block time, delegate →
draft a hand-off, batch → errand loop, overlap → delay-start, automate → async.
Nothing happens until the user confirms — `proposed → (confirm) → executed →
(undo) → undone`. `MockExecutor` runs the loop safely today; the real
`CalendarExecutor` and `MessageExecutor` slot in behind the same interface,
each carrying its wiring checklist. Calendar write is the first non-read-only
capability and is gated behind explicit per-action confirmation by design.
