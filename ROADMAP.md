# Get Time Back — phased build sequence

The product's job is not to help you do more. It is to **subtract logistics so presence can grow**, and to **defend the time it reclaims** instead of letting it refill. Every phase below is sequenced so that each one retires a specific risk before the next one spends money on top of it.

A guiding rule runs through all of it: **suggest before you act, and act before you automate.** Trust is the scarcest resource in this category. A single wrong "you don't need to do this" early on is unrecoverable.

---

## Phase 0 — Prototype *(this repo)*

**Goal.** Prove the narrative, not the technology. Can a stakeholder look at a messy day, see its *true* cost surfaced, and feel the "time back" promise land?

**Build.** The self-contained demo in `index.html`: a keyword classifier stands in for the engine, a deterministic rules table assigns each item a lever and a credited-minutes figure, and the ledger UI renders the three numbers that matter — committed, reclaimable, presence on the line.

**Integrations.** None. Runs offline, in any browser, with zero setup. That is the point — it must never fail in front of a room.

**Success metric.** A non-technical stakeholder reaches "I want this for myself" inside two minutes.

**Risk retired.** *Is the concept legible and desirable?* Everything after this assumes yes.

---

## Phase 1 — The estimation engine + read-only calendar

**Goal.** Replace the rules table with a real engine that estimates a task's *true* cost — active time, travel, wait, and the fragmentation it imposes on the hours around it — and learns from what actually happened.

**Build.** A task-enrichment service. Each item is resolved against duration, place, people, time-window, and attention type. Start with an LLM call for first-pass estimates (cold start), then correct toward reality using a feedback loop: calendar event durations, geofence dwell times, and a lightweight "did you finish?" nudge.

**Integrations.** Google Calendar (read-only) and one task source (Reminders, Todoist, or Things). Read-only is deliberate — you are observing, not yet touching the user's day.

**Success metric.** Estimated durations land within ±20% of actuals after two weeks of a single user's data.

**Risk retired.** *Can we estimate true time well enough to be trusted?* This is the hard part and the data moat. If this fails, nothing downstream matters.

---

## Phase 2 — Lever recommendations *(advisory only)*

**Goal.** Turn enriched tasks into specific, subject-aware suggestions — and surface the hidden costs the user can't see, especially fragmentation and wait time.

**Build.** The lever router: each task type maps to its highest-leverage move (recurring meeting → async; errand → batch or deliver; chore → overlap + delay-start; family logistics → delegate). Recommendations are *advisory* — shown, never taken. The UI exposes the true-cost breakdown so the user learns to see it too.

**Integrations.** Maps/traffic for real travel times; messages and email scanned read-only for hidden commitments ("I'll send that Friday").

**Success metric.** Users accept ≥40% of suggestions and rate them "would actually do this."

**Risk retired.** *Are the recommendations smart and trustworthy enough that people would act on them?*

---

## Phase 3 — Actions and write-back

**Goal.** Let the tool do the thing, with the user's approval each time. This is where reclaimed time becomes real rather than theoretical.

**Build.** Propose-and-confirm write-back: block placement on the calendar, draft delegation messages, assemble a batched errand loop, set a delay-start reminder. Every action is one tap from a suggestion and fully reversible.

**Integrations.** Calendar write, message/email draft, optional delivery/automation hooks (grocery, bill pay).

**Success metric.** A meaningful share of suggestions convert to a completed action without the user feeling nagged.

**Risk retired.** *Will people grant the tool limited autonomy over their day?*

---

## Phase 4 — The household layer

**Goal.** Move from personal efficiency to multi-party coordination — where the largest savings actually live. "Pick up the kids" is a household optimization, not a solo one.

**Build.** A shared family time-map. The engine optimizes across members: who is free to drive, whose errands overlap, which pickup can become a carpool swap. A consent model governs what each member can see and act on.

**Integrations.** Shared calendars, a household roster, opt-in location sharing between members.

**Success metric.** A coordinated action (carpool swap, errand handoff) is completed across two or more household members.

**Risk retired.** *Is the shared layer worth its complexity and privacy cost?* This is the defensible moat — and the part most likely to be copied if you prove it first.

---

## Phase 5 — Defend the time + the values loop

**Goal.** Close the loop that separates this from every other productivity app. Reclaimed time gets fenced and pointed at something the user said they valued — not left as a vacuum that work refills.

**Build.** Protected-presence scheduling. The user names what matters (bedtime, a walk, dinner). The tool positively schedules reclaimed time against it and defends that block from encroachment. The "Protect" lever becomes a first-class output, never a residual.

**Integrations.** Builds on everything prior; adds a stated-values store.

**Success metric.** Reclaimed time measurably converts into protected presence blocks that survive the week.

**Risk retired.** *Does the product deliver on its actual promise — presence, not just efficiency?* Get this wrong and you have shipped a faster treadmill.

---

## Sequencing logic at a glance

| Phase | What you prove | If it fails, you stop |
|-------|----------------|------------------------|
| 0 | The concept is desirable | …before writing a backend |
| 1 | You can estimate true time | …before recommending anything |
| 2 | Recommendations are trusted | …before touching the calendar |
| 3 | People grant autonomy | …before building for households |
| 4 | The shared layer earns its cost | …before scaling go-to-market |
| 5 | Presence actually grows | …this is the bar for success |

The two product decisions to lock before Phase 1: **how reclaimed time is defended** (Phase 5's mechanic, but designed up front), and **where the line sits between logistics you compress and presence you never touch.** Those are the soul of the product; everything else is plumbing.

## Phase 6 — Background agent

A control loop above the engine: scores the day against a value function, ranks
suggestions by value-per-interruption, self-critiques, and returns a timed brief
(`POST /agent/run`). See `service/AGENT_SETUP.md`. Optimize / interrogate /
suggest split across `app/agent/{value,planner,critic}.py`; deterministic core,
optional LLM critique behind `GTB_AGENT_LLM=1`.

## Phase 6.1 — Feedback harness

The agent learns restraint: `POST /agent/feedback` records accept/reject/edit/
ignore per suggestion, `GET /agent/feedback/stats` shows what it learned.
Tunes a personalized interrupt threshold and suppresses waved-off kinds;
`run_cycle` applies learned prefs before ranking. Stored in `gtb.db`
(`agent_feedback`). See `service/AGENT_SETUP.md`.

## Phase 6.2 — Urgency + edit-learning

Time-to-event (`start - travel`) forces a leave-now interrupt past the value
threshold and beats suppression; pass `now_min` for tz-correct timing
(`app/agent/urgency.py`). Feedback gains `edited_to`: edits count as wanted,
repeated edits become surfaced preferences, and learning decays to a 90-day
window. See `service/AGENT_SETUP.md`.

## Phase 6.3 — Agent brief UI

A surface for the agent at `agent.html` (served at `/brief` and `/agent.html`):
runs `/agent/run`, shows the decide-now vs. wait split with leave-by notes and
the value score, and wires accept/reject/edit buttons to `/agent/feedback` with
a live "what the agent has learned" panel (threshold, suppressed kinds,
preferred edits). Linked from the ledger header. Needs the running service.

## Phase 6.4 — Real source: inbox to commitments

Mines raw messages for hidden commitments (`app/agent/extract.py`, deterministic
+ optional LLM) and feeds them into the brief. `POST /agent/inbox` extracts from
pasted text or a configured inbox — real read-only Gmail behind `GTB_GMAIL_READ`
(`app/agent/sources.py`, scope `gmail.readonly`), mock inbox otherwise. Surfaced
in the brief UI via a "Pull from your inbox" panel. See `service/SOURCES_SETUP.md`.

## Deployment

Mock-safe hosting config at repo root: `requirements.txt` (three runtime deps),
`Procfile`, `render.yaml`, `runtime.txt`. Start: `uvicorn app.main:app --app-dir
service --host 0.0.0.0 --port $PORT`. All real integrations stay flag-gated, so a
default deploy holds no secrets. `GTB_DB_PATH` makes SQLite persistence optional.
Deployed (unlike Pages), `/brief` is fully live. See `DEPLOY.md`.

## Phase 6.5 — Editable labels + protect list

Inline `#label` tags on a day line force a category (e.g. `#admin`,
`#recurring-meeting`, `#protect`->presence); `GET /labels` exposes the
vocabulary and the brief UI adds a per-item re-label dropdown that rewrites the
tag and re-runs. The protect list is now persistent (`app/presence/values_repo.py`,
DB-backed) with `DELETE /values/{id}` and an editor panel in the brief UI.
