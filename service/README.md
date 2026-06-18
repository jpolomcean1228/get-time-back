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

### Extending it without editing code

The two pieces of domain knowledge the rules engine used to hardcode are now
data:

- **Categories** live in [`fixtures/profiles.json`](./app/fixtures/profiles.json).
  A profile pairs how an item is recognised (`keywords`) with what it costs
  (`active`/`wait`/`travel`/`frag`) and the move that shrinks it (`lever`, `why`).
  Adding a task type is adding a JSON object — and `POST /profiles` does it at
  runtime, so the next `/enrich` classifies against it immediately. One profile
  is the `default` bucket when nothing matches.
- **Levers** are a registry (`app/engine/levers.py`): each is a label plus a
  `credit(estimate) -> minutes` formula, registered by name. `credit()` is a
  lookup, so a new lever is one `register_lever(...)` call, and a profile that
  names an unregistered lever simply credits 0 instead of breaking enrich.
- **Components** (the base estimator, calendar provider, calendar writer,
  message writer) are built through a plugin registry (`app/plugins.py`)
  instead of hand-constructed in `main.py`. Each implementation registers a
  factory under a name; the assembly picks a name (from env, with the same
  mock-vs-real auto-selection as before) and calls `create(kind, name, cfg)`.
  A third-party adapter ships in its own module, calls `register(...)`, and is
  activated by listing that module in `GTB_PLUGINS` and selecting it by name
  (e.g. `GTB_CALENDAR=outlook`) — no edit to the service. `GET /plugins` lists
  what's registered and what's active.

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
| GET  | `/plugins` | registered adapters per swappable seam + which are active |
| POST | `/enrich` | enrich a day → per-task levers + totals (+ proposed actions) |
| POST | `/actuals` | log a real completion (closes the loop) |
| GET  | `/calendar/today` | today's events (read-only) |
| GET / POST | `/profiles` | the category/cost table the engine classifies against — add a task type as data |
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
    profiles.py      the category/cost table, loaded from a fixture
    rules.py         deterministic baseline (Phase 0 port), reads profiles
    llm.py           Claude first-pass, falls back to rules
    learned.py       shrinkage correction toward actuals
    levers.py        lever registry + credit() + logistics/presence split
  store/
    actuals.py       SQLite feedback store
  calendar/
    base.py          CalendarProvider protocol
    mock.py          fixture-backed provider (runs keyless)
    google.py        read-only OAuth stub + wiring checklist
  fixtures/
    profiles.json      the category table — edit data, not code
    sample_calendar.json
tests/
  test_engine.py     classifier, levers, and the learning loop
```

## What's real vs. stubbed

Every phase of the roadmap is built and runs end to end on mocks. The seams to
real services are documented stubs, each behind the same interface as its mock:
Calendar read (`GoogleCalendarProvider`), calendar write (`GoogleCalendarWriter`
+ `CalendarExecutor`), and Gmail drafts (`GmailMessageWriter` + `MessageExecutor`)
are all implemented. Only the household's shared-calendar / consent sources
remain mocked — inherent to a multi-user backend. Each real adapter sits behind
the same interface as its mock and is enabled per-capability via env flags. Swap a mock for its real
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
