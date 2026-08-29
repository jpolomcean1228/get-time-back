# Background agent — setup & how it runs

The agent is a control loop that sits **above** the engine. It doesn't invent
moves; it takes the day's candidate moves (from the enrich pipeline), scores the
day against an explicit value function, ranks suggestions by
value-per-interruption, critiques its own plan, and returns a timed brief that
separates *decide now* from *wait for the brief*.

    sense  ->  state  ->  assess  ->  optimize  ->  deliver
      \_________________ learn (accept / reject) ___________/

## Run one cycle

    POST /agent/run
    { "tasks": ["3:15 pick up the twins ...", "email the contractor ...",
                "family dinner 6pm"],
      "include_calendar": false }

`include_actions` is forced on internally. Returns an `AgentBriefOut`:
`headline`, `score` (the value function), ranked `suggestions` (each with
`value_minutes`, `urgency`, and an `interrupt` flag), `critique` notes, and
`interrupt_count` / `brief_count`.

Nothing acts on its own — every suggestion carries an `action_id` you confirm
through the existing action store. The agent proposes; the confirm gate stands.

## What each piece does (optimize / interrogate / suggest)

- **value.py — optimize.** The objective the agent maximizes:
  `presence*1.5 + reclaimable*1.0 - fragmentation*0.5`. Change the weights to
  change what it optimizes for. This scores a *proposed* plan; the real
  north-star is presence that *survived* the week — an outcome, measured later.
- **planner.py — suggest.** One suggestion per move; ranked interrupts-first,
  then by value. A move must clear `_INTERRUPT_MIN` (45m) to earn an interrupt;
  everything else batches into the brief. That's the restraint calculus.
- **critic.py — interrogate.** Deterministic self-checks (reclaiming but
  protecting nothing, over-delegating, too many interrupts). An optional LLM
  strategic critique slots in behind `GTB_AGENT_LLM=1` (needs `ANTHROPIC_API_KEY`);
  off by default, fails silently, same mock-first pattern as the estimator.
- **worker.py — the cycle.** `run_cycle(tasks, presence)` ties them together.

## Making it actually run in the background — three options

1. **Cadence (simplest, start here).** Point a scheduler at `/agent/run`:
   - cron / launchd: `curl -s -X POST localhost:8000/agent/run -d @day.json`
     at 7am (plan) and 6pm (what survived).
   - in-process: add APScheduler and call `agent_run_cycle(...)` on an interval.
   Blind between ticks, but a real background agent on day one.

2. **Event-driven (responsive).** Wake on change — calendar event added, email
   arrives, geofence crossed. Needs connectors that emit events (webhooks, or
   diff-on-poll) into a queue that triggers a cycle. This is where "leave now"
   lives.

3. **Standing-goal control loop (mature).** Keep a live day-model + the value
   function, and re-plan only when reality drifts past a threshold. Hybrid of
   the two above; the drift detector is the new part.

## Where the harnesses grow next

- **Optimize:** pair the (future) LLM planner with a constraint solver — LLM
  picks strategy, solver does the time-slot packing it's bad at.
- **Interrogate:** anomaly detectors over the state + an offline eval suite
  (scenarios + metrics) so plan quality is measured, not vibes.
- **Suggest:** urgency from time-to-event + travel now ships (see below); a real
  geolocation/routing provider is the remaining upgrade.
- **Trust ladder:** graduate proven low-risk moves from suggest -> auto-draft
  -> auto-execute, per action-type, while high-stakes stays gated.

## Honest limits

Deterministic today (the LLM layer is a documented hook, not wired on by
default). Urgency is coarse (time-present vs. not) until time-to-event lands.
No scheduler ships in the repo — you choose one of the three above. The value
function's weights are a starting guess, not tuned against real outcomes yet.

## Feedback harness — the agent learns your restraint (built)

The agent starts on the default rules and earns personalization from what you do
with its suggestions. Every suggestion in a brief carries a stable `id`
(a signature like `protect:an-unhurried-walk`, not the volatile confirm-action
id) so feedback survives across cycles.

    POST /agent/feedback
    { "suggestion_id": "protect:an-unhurried-walk", "kind": "protect",
      "value_minutes": 45, "interrupt": true, "verdict": "rejected" }

`verdict` is one of accepted / rejected / edited / ignored. Feedback is
per-user when signed in, shared otherwise.

    GET /agent/feedback/stats   ->  { total, by_kind, interrupt_min, suppressed_kinds }

Two things it learns, both deliberately conservative so a stray tap doesn't
reshape your day:

- **Interrupt threshold.** Dismiss interrupts in some value band enough times
  (>= 3) and the bar to interrupt you rises above it — but never above a value
  you've actually welcomed. Default 45m; bounded to 30–120.
- **Kind suppression + hard no.** A kind you wave off (< 25% accepted over >= 4
  acted-on suggestions) stops earning interrupts and drops to the brief. A
  specific suggestion you reject is not re-surfaced.

Stored in the shared `gtb.db` (table `agent_feedback`) — no new infra. The
learning is intentionally explainable: you can read the exact threshold and
suppressed kinds from `/agent/feedback/stats` and see why a suggestion did or
didn't interrupt you. Edits are now learned distinctly from rejects, and old feedback decays (see
below).

## Urgency — time-to-event forces a leave-now interrupt (built)

Value asks "is this worth interrupting for?"; urgency asks "is it too late to
wait?". A timed task has a leave-by moment (`start - travel`); once now crosses
it the agent interrupts regardless of the suggestion's minute value, and warns
within 30 minutes of it. A genuine leave-now beats even a suppressed kind.

Pass the client's local time so it's timezone-correct (server time if omitted):

    POST /agent/run   { "tasks": [...], "now_min": 900 }   # 15:00 = 900

Each suggestion's `urgency` is now / soon / today / flexible, and time-critical
ones carry a "leave by 2:55pm" note. "Location" here is the engine's travel
estimate; a real geolocation + routing provider (your position -> ETA) slots in
by supplying `travel` per task — this logic doesn't change.

## Edit-learning + decay (built)

`POST /agent/feedback` takes an optional `edited_to` when the verdict is
`edited`:

    { "suggestion_id": "handoff:...", "kind": "handoff", "value_minutes": 65,
      "interrupt": true, "verdict": "edited", "edited_to": "Grandma" }

Three things follow. An edit counts as *wanted* (it keeps a kind from being
suppressed — you tweaked it, you didn't wave it off). Repeat the same change
(>= 2x) and it becomes a **preferred edit** the agent surfaces proactively
("you usually change this to Grandma"). And all learning now **decays** — only
feedback inside a 90-day window shapes behavior, so the agent tracks a life that
changes rather than anchoring on last quarter. `/agent/feedback/stats` returns
`preferred_edits` and `learning_window_days`.
