# Connecting a real Google Calendar (read-only)

By default the service uses a mock calendar fixture. To read your actual day,
wire up Google Calendar. It stays **read-only** — the app only ever observes
your calendar here; writing blocks back is a separate, confirmation-gated
capability (Phase 3) that remains a mock until you wire it deliberately.

## 1. Create a Google Cloud project + enable the API

1. Go to https://console.cloud.google.com/ and create a project (or reuse one).
2. **APIs & Services → Library →** search "Google Calendar API" → **Enable**.

## 2. Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen.**
2. User type **External** (fine for personal use), fill in the app name and
   your email, save.
3. Under **Scopes**, you don't need to pre-add anything — the app requests the
   read-only scope at runtime.
4. Under **Test users**, add your own Google account. (While the app is in
   "testing", only listed test users can authorize it — which is all you need.)

## 3. Create OAuth client credentials

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID.**
2. Application type: **Desktop app.**
3. Create, then **Download JSON**. Save it somewhere private, e.g.
   `~/.config/get-time-back/credentials.json`. **Do not commit it** — it's a
   secret. (`.gitignore` already excludes `.env`, `*.json` is not ignored, so
   keep the file outside the repo.)

## 4. Point the service at it

In `service/.env` (copy from `.env.example`):

```
GTB_GOOGLE_CREDENTIALS=/Users/you/.config/get-time-back/credentials.json
GTB_GOOGLE_TOKEN=token.json
```

Install the optional dependencies (already in `requirements.txt`):

```
pip install -r requirements.txt
```

## 5. First run — authorize once

Start the service and hit the calendar once:

```
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/calendar/today
```

The first call opens a browser asking you to authorize read-only calendar
access. Approve it. A `token.json` is written so you won't be asked again; it
refreshes itself when it expires. (Add `token.json` to your ignore list — it's
a credential.)

After that, `/calendar/today` and `include_calendar: true` on `/enrich` read
your real timed events for today. All-day events are skipped (they aren't
schedulable blocks). If credentials are ever missing or invalid, the service
falls back to the mock calendar automatically — it never hard-fails.

## The read-only boundary

The requested scope is `calendar.readonly` and nothing else. Writing protected
blocks back to your calendar (Phase 5's "Protect it") currently runs through the
`MockExecutor`; turning that into real calendar writes means upgrading to the
`calendar.events` scope and implementing `CalendarExecutor` — deliberately left
as a separate step so read access never silently becomes write access.

## 6. (Optional) Calendar WRITE — protected blocks become real events

By default, confirming a "Protect it" block runs through a mock writer. To make
it create a real calendar event (and remove it on undo), enable write:

1. The write path uses the broader `calendar.events` scope. The same OAuth
   client works; you'll just authorize a second time for the wider scope, into
   a separate token file. This keeps read-only deployments read-only.
2. In `.env`:
   ```
   GTB_CALENDAR_WRITE=1
   GTB_GOOGLE_WRITE_TOKEN=token_write.json
   ```
3. Restart, then confirm a protected block in the demo. The first write opens a
   browser to authorize calendar.events; after that, "Protect it" inserts an
   event on your primary calendar, and **undo** deletes exactly that event.

Write only ever happens through the confirm gate — never automatically — and
every write is reversible by the undo it pairs with.
