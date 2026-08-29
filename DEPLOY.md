# Deploying Get Time Back

## Why this is worth doing

On GitHub Pages the app is **offline-only** — the static shell, with the agent
brief showing "start the service." Deployed to a real host, the FastAPI backend
runs, so `/brief` is **fully live** for anyone you send the link to: the agent
runs, scores the day, fires leave-now, learns from accept/reject/edit, and mines
a pasted inbox for commitments — all in their browser, no setup on their end.
That's the difference between "clone my repo and run it" and "click this."

## What was added (all at the repo root)

- `requirements.txt` — the three runtime deps (that's all mock mode needs).
- `Procfile` — start command for Railway / Heroku-style hosts.
- `render.yaml` — one-click blueprint for Render.
- `runtime.txt` — pins Python 3.12.
- `.gitignore` — now also ignores OAuth tokens and client secrets, so you can't
  leak them.

The start command everywhere is:

    uvicorn app.main:app --app-dir service --host 0.0.0.0 --port $PORT

## Mock mode is safe to expose

Verified: with **every environment variable wiped** and no database file, the
app boots and every endpoint answers. All real integrations (Google Calendar,
Gmail, Anthropic) are lazy and flag-gated — nothing activates unless you set a
variable *and* provide credentials. So a default deploy holds no secrets, reads
no inbox, sends nothing. Deploy it as-is.

## Deploy to Render (recommended — has a free tier)

1. Push the new files (commands at the bottom).
2. Go to **render.com → New → Blueprint**, connect your GitHub repo. Render reads
   `render.yaml` and configures everything.
   *(Or New → Web Service, pick the repo, set Build Command
   `pip install -r requirements.txt` and Start Command
   `uvicorn app.main:app --app-dir service --host 0.0.0.0 --port $PORT`.)*
3. Create. First build takes ~2–3 minutes. You get a URL like
   `https://get-time-back.onrender.com`.
4. Open it → the ledger. Open `/brief` → a green **live agent** pill. Done.

Free-tier note: the service sleeps after ~15 min idle; the first hit after that
takes ~30s to wake, then it's fast. Fine for a demo — just click it a minute
before you show someone.

## Deploy to Railway (alternative)

1. **railway.app → New Project → Deploy from GitHub repo.**
2. Railway auto-detects Python from `requirements.txt` and uses the `Procfile`
   start command. It provides `$PORT` automatically.
3. **Settings → Networking → Generate Domain** for a public URL.

## Environment variables (all optional — skip them for a demo)

| Variable | What it turns on |
| --- | --- |
| `GTB_DB_PATH` | Persist the SQLite DB at a path (e.g. a mounted disk) instead of the ephemeral default |
| `GTB_GOOGLE_CREDENTIALS` | Real Google Calendar read |
| `GTB_CALENDAR_WRITE` | Calendar event writes |
| `GTB_GMAIL_DRAFTS` | Gmail draft creation (never sends) |
| `GTB_GMAIL_READ` | Inbox reading for commitment extraction |
| `GTB_AGENT_LLM=1` + `ANTHROPIC_API_KEY` | Claude for estimates / self-critique / extraction |

None are required for the mock demo. Enabling the Google ones also means
installing the optional packages listed in `requirements.txt` and adding the
deployed domain to your OAuth client's authorized redirect URIs in Google Cloud
Console.

## Persistence caveat

By default the host disk is **ephemeral**: the SQLite DB (accounts, and the
feedback the agent has learned) resets on each redeploy. That's fine for a
demo. To keep it, attach a persistent disk (on Render: add a Disk, mount at e.g.
`/var/data`) and set `GTB_DB_PATH=/var/data/gtb.db`.

## One caveat for a public URL

The accounts system is prototype-grade (no rate limiting or email
verification). For a public demo, either don't advertise sign-up, or leave it as
a labeled prototype. The agent brief works anonymously (shared feedback), so you
don't need accounts to show it off.

## Getting it onto a phone as "an app"

Once it's a public `https` URL it already works in a phone browser. To make it
feel like a real installed app, it needs a **web manifest** — then the browser's
**"Add to Home Screen"** gives it an icon on the home screen, full-screen, no
browser chrome. That's a PWA: the lightest path to "an app" with no app-store
friction. (A native wrapper or store listing is a bigger, later step.) The
manifest + icon isn't wired yet — it's a small next task whenever you want it.

## Ship the deploy files

    cd ~/Downloads
    rm -rf _gtb && mkdir _gtb
    unzip -o -q "$(ls -t ~/Downloads/get-time-back-deploy*.zip | head -1)" -d _gtb
    cp -R _gtb/get-time-back/service        /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/requirements.txt  /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/Procfile          /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/render.yaml       /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/runtime.txt       /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/.gitignore        /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/DEPLOY.md         /Users/justinpolomcean/Downloads/get-time-back/
    cp _gtb/get-time-back/ROADMAP.md        /Users/justinpolomcean/Downloads/get-time-back/
    rm -rf _gtb
    cd /Users/justinpolomcean/Downloads/get-time-back
    git add -A && git commit -m "Deploy: mock-safe hosting config (Render/Railway) + configurable DB path" && git push
