# Time Back Project — MVP Plan

**One-line pitch:** An AI co-pilot that watches how your time gets spent, tells you what's wasting it, and actually does the work to give those hours back.

**Tagline candidates:** *Get your hours back.* / *Less doing. More living.* / *Your time, on autopilot.*

---

## 1. The Problem

The average consumer loses 2–4 hours a day to low-value, repeatable tasks: email triage, scheduling, comparison shopping, form-filling, "quick" admin, meeting follow-ups, scrolling. Most productivity apps make people *track* time better. They don't actually *give it back*.

**The insight:** AI is now good enough to do the work, not just describe it. The product is the time saved, not the dashboard.

---

## 2. The Core Loop

Five-step engine — every feature in the MVP slots into one of these stages:

1. **Capture** — pull signals from where time actually lives (calendar, email, browser, tasks).
2. **Classify** — AI tags each chunk: *high-value / low-value*, *automatable / not*, *energy-giving / draining*.
3. **Recommend** — for each chunk, one verdict: **Automate, Delegate, Batch, Shorten, Eliminate, or Keep.**
4. **Execute** — actually perform the action (draft the reply, fill the form, summarize the thread, block the focus time).
5. **Measure** — show hours saved per week and where they went.

The user-facing promise is step 5. Everything else is plumbing.

---

## 3. Target User (MVP)

Even though the long-term vision is "everyone," the MVP needs a beachhead. Recommend starting with:

**Primary persona:** Digital-first adults (25–45) who live in Gmail, Google Calendar, and a browser. Knowledge workers, freelancers, and busy parents are all subsets. They already feel time-poor and are willing to try AI tools.

**Why this slice:** Their time-sinks are highly observable through 2–3 integrations (Gmail, Calendar, browser). That keeps build scope small while the value proposition stays huge.

---

## 4. Platform Recommendation

**Build a Chrome extension + lightweight web dashboard.**

Reasoning:
- A **browser extension** is the cheapest way to observe behavior across email, calendar, shopping, research — the four biggest time-sinks for a consumer — without building separate integrations for each.
- A **web dashboard** at `app.[yourname].com` handles onboarding, the weekly "time back" report, and settings.
- Mobile can come in v2 once you know what's worth pushing to a phone.

Stack suggestion (scrappy):
- **Extension:** Plain JS or React + Vite, Manifest V3.
- **Backend:** Node/Express or Python/FastAPI on Railway or Fly.io.
- **AI:** Anthropic API (Claude Sonnet for classification + drafting; Haiku for cheap, high-volume tagging).
- **DB:** Postgres (Supabase = auth + DB + storage in one).
- **Auth:** Google OAuth (you need it anyway for Gmail/Calendar scopes).

---

## 5. MVP Feature Set (4-Week Scope)

Cut hard. Ship these five and nothing else:

### Feature 1 — Inbox Triage
AI reads new email, sorts into *Reply now / Reply later / FYI / Trash*, drafts replies for the first two buckets. User approves or edits.
**Time saved:** 30–60 min/day.

### Feature 2 — Calendar Audit
Weekly scan: which meetings repeat, which have no agenda, which could be email, which conflict with focus time. One-click "decline + propose async."
**Time saved:** 1–3 hours/week.

### Feature 3 — Smart Summarize
Right-click any article, thread, PDF, or YouTube video → 3-bullet summary + "is this worth your full attention?" verdict.
**Time saved:** 20–40 min/day.

### Feature 4 — Task Compressor
Paste or forward any task ("research best dishwashers under $800", "plan kid's birthday party"). AI returns a 5-minute decision instead of a 2-hour rabbit hole — shortlist, recommendation, and rationale.
**Time saved:** highly variable, but the "wow" feature.

### Feature 5 — The Weekly Time Back Report
Sunday email + dashboard: *"You got 6.4 hours back this week. Here's how."* Breakdown by feature, plus one suggested change for next week.
**Why critical:** this is the product. Without it, users don't *feel* the value.

**Explicitly out of scope for v1:** team features, mobile app, custom integrations beyond Google, on-device AI, voice, Slack/Notion/Asana hooks.

---

## 6. The 4-Week Build Plan

**Week 1 — Foundations**
- Set up repo, Supabase, Anthropic API keys.
- Google OAuth + Gmail/Calendar read scopes.
- Skeleton Chrome extension with auth handoff to web app.
- Ship Feature 3 (Smart Summarize) first — it's the smallest and gives a daily-use hook.

**Week 2 — Inbox & Calendar**
- Feature 1 (Inbox Triage) end-to-end with one model call per email.
- Feature 2 (Calendar Audit) as a weekly cron job + dashboard view.
- Internal dogfooding starts.

**Week 3 — Task Compressor + Measurement**
- Feature 4 (Task Compressor) — extension popup + paste box.
- Logging layer: every AI action records *estimated minutes saved* (heuristic per action type).
- Feature 5 v1: dashboard widget showing weekly total.

**Week 4 — Polish & Launch**
- Weekly email report.
- Onboarding flow (3 screens max).
- Pricing page + Stripe (suggest free tier with 50 actions/month, $12/mo unlimited).
- Soft launch: Product Hunt, X, a few subreddits (r/productivity, r/getdisciplined).

---

## 7. Pricing & Business Model

- **Free:** 50 AI actions/month — enough to feel the value, not enough to live on.
- **Pro — $12/mo:** unlimited actions, weekly report, priority models.
- **Family — $20/mo:** up to 5 accounts. (Defer to v1.1.)

Unit economics check: at ~$0.01–$0.03 per action with Claude Haiku/Sonnet mix, even a heavy user costs < $3/mo in inference. Healthy margin.

---

## 8. Success Metrics

Three numbers that matter — track from day one:

1. **Median hours saved per active user per week.** Target: 3+ by end of month 1, 6+ by end of month 3.
2. **Weekly active rate** (% of signups using the product in a given week). Target: 40%+.
3. **Free → Paid conversion.** Target: 4–6%.

A vanity metric to ignore: signups. Time saved is the only number that matters.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Users don't trust AI with their inbox | Drafts only; never auto-send in v1. |
| Google API quotas / approval | Apply for OAuth verification week 1 — it takes weeks. |
| "Time saved" feels invented | Be conservative in estimates; show the math. |
| Inference cost spikes | Route easy tasks to Haiku; cache classifications. |
| Privacy concerns | On-device classification where possible; clear data deletion. |

---

## 10. What to Decide Next

Before we start building, three calls you need to make:

1. **Name + domain.** ("Hourback", "Reclaim" — taken, "Tempo", "Backhour", "Unbusy"…)
2. **First feature to prototype end-to-end** — recommend Smart Summarize, since it's a single-day build and gives an immediate hook.
3. **Solo or co-founder?** Affects whether you also need a basic team setup, billing-on-an-org, etc.

---

*Next step from here: pick the first feature, and I'll generate a working prototype — extension code, backend endpoint, and Anthropic API integration — in the next message.*
