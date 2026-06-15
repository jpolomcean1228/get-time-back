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
| GET  | `/household` | roster + consent (the shared layer) |
| GET / POST | `/values` | stated values reclaimed time funds |
| GET  | `/presence/protected` | blocks currently defended from encroachment |

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

## What's real vs. stubbed

Every phase of the roadmap is built and runs end to end on mocks. The seams to
real services are documented stubs, each behind the same interface as its mock:
`GoogleCalendarProvider` (read), `CalendarExecutor` / `MessageExecutor` (write),
and the household's shared-calendar / consent sources. Swap a mock for its real
adapter without touching anything upstream.

## Phase 5 — the values loop (done)

The closer. `app/presence/` adds a stated-values store (what the user wants
reclaimed time spent on), a planner that spends the day's reclaimable-minutes
budget on those values in priority order — banking the remainder instead of
letting work refill it — and real defense: a confirmed protected block is
registered in `ProtectedBlocks`, which the rest of the system must respect.
The "protect" lever is now a first-class output. `GET /presence/protected`
lists what's currently defended; `GET/POST /values` manage the intentions.

This is the difference between the product and a faster treadmill: reclaimed
time gets a named destination and is defended, rather than quietly reabsorbed.
