# Real sources — inbox → commitments

The tasks that eat your time are rarely on a list: they're a line in an email
("can you send the form by Friday"), a text ("don't forget the dentist"). This
pulls those hidden commitments out of raw messages so the agent can cost and
route them like anything else.

## Try it now (no credentials)

    POST /agent/inbox
    { "text": "Could you send the Q3 numbers by Tuesday? Please sign the field
               trip form due Thursday." }

Returns `commitments` — each a short task line with a `cue`
(request / reminder / deadline / task) and a `confidence`. Omit `text` and it
pulls from a mock inbox so the demo works end-to-end. In the brief UI
(`/brief`), the "Pull from your inbox" panel does this and drops the results
into your day.

## How extraction works

`app/agent/extract.py` is deterministic by default — regex cues for requests,
reminders, imperative task verbs, and deadlines — so it runs locally with
nothing leaving the machine, which matters when the source is your inbox. It's
read-only and never sends. An LLM pass (Claude) is opt-in behind
`GTB_AGENT_LLM=1` (+ `ANTHROPIC_API_KEY`); it only improves recall and falls
back to the rules on any failure.

## Enabling your real inbox (Gmail, read-only)

`app/agent/sources.py` has `GmailInbox`, a faithful scaffold that mirrors the
Gmail draft writer's auth but with a separate **read-only** scope
(`gmail.readonly`) and its own token (`token_gmail_read.json`), so read access
never implies send. Enable it by pointing `GTB_GMAIL_READ` at your OAuth client
secrets JSON:

    export GTB_GMAIL_READ=/path/to/credentials.json

Then `POST /agent/inbox` with no `text` lists your recent inbox messages and
extracts from them. First run opens a browser consent screen and caches the
read-only token.

## Honest limits

The Gmail path can't be exercised without your Google credentials, so treat it
as prototype-grade — a scaffold to enable, not a tested integration (the
extractor and mock inbox are fully tested). Extraction is heuristic: it favors
precision over recall (it skips chatter, so it will miss some real asks) until
you turn the LLM pass on. Reading an inbox is sensitive; keep the LLM off to
keep extraction fully local.
