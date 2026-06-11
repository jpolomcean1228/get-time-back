# Get Time Back

A virtual PM that reads a messy day, surfaces each item's **true** cost — travel, waiting, and the focus it shatters around it — and credits back the time a smarter move would return. The goal isn't to do more. It's to **subtract logistics so presence can grow**, then **defend the time it reclaims**.

This repo is **Phase 0**: a self-contained prototype for putting the concept in front of stakeholders. See [`ROADMAP.md`](./ROADMAP.md) for the full phased build sequence.

## The demo

Open [`index.html`](./index.html) in any browser — that's it. No build step, no dependencies, no network. It ships with a realistic sample day; edit the list and click **Read my day** to re-run.

What it shows:
- **Committed** — the logistics time on today's list, costed for real.
- **Reclaimable** — what the suggested moves would hand back.
- **Presence on the line** — the time the tool will *protect*, not optimize.

Each row gets a subject-aware lever (eliminate · automate · delegate · batch · defer · overlap · protect) and the minutes it credits back, rendered as a ledger.

## How the engine works (and where the real one slots in)

Phase 0 uses a deterministic stand-in, all inside `index.html`:

- `classify(text)` — keyword classifier → task type
- `enrich(category)` — type → `{active, wait, travel, frag, lever, why}`
- `credit(enriched)` — recommended lever → minutes reclaimed

In **Phase 1** these three functions become a service: `classify` + `enrich` are replaced by a learned estimator (LLM first-pass, corrected against logged actuals), and `credit` becomes the lever router fed by real calendar, location, and message context. The function boundaries here are intentionally the same seams the production engine will use.

## Deploy a shareable link (GitHub Pages)

Once pushed (see below), turn on Pages so stakeholders get a URL instead of a file:

1. Repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**, branch **main**, folder **/ (root)**
3. Save. Your demo goes live at `https://<you>.github.io/get-time-back/`

## Status

| Phase | State |
|-------|-------|
| 0 — Prototype | ✅ this repo |
| 1 — Estimation engine + calendar | ⏳ next |
| 2–5 | 📋 see ROADMAP |

MIT licensed.
