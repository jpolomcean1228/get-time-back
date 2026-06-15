# Connecting Gmail drafts (hand-off messages)

By default, confirming an "Ask <name>" hand-off runs through a mock writer. To
make it create a real Gmail **draft** (and discard it on undo), enable Gmail.
The tool only ever drafts — it never sends. You review and send yourself.

## 1. Reuse your Google setup

You can use the same OAuth client and credentials JSON from CALENDAR_SETUP.md.
Just enable the Gmail API for the project:

- **APIs & Services → Library →** search "Gmail API" → **Enable**.

## 2. Configure the service

In `service/.env`:

```
GTB_GOOGLE_CREDENTIALS=/Users/you/.config/get-time-back/credentials.json
GTB_GMAIL_DRAFTS=1
GTB_GMAIL_TOKEN=token_gmail.json
```

The Gmail path uses the `gmail.compose` scope and its own token file, separate
from calendar — so enabling drafts never touches your calendar access, and vice
versa.

## 3. First run — authorize once

Start the service, then confirm an "Ask <name>" hand-off in the demo (the
basketball-pickup row). The first draft opens a browser to authorize
`gmail.compose`. After that, confirming a hand-off creates a draft in your Gmail
(addressed to the matched member if their email is in the roster), and **undo**
deletes that draft.

## Why draft, never send

The product's job is to prepare the message, not to speak for you. Sending stays
a human action: you open the draft, read it, and send. There is no send scope
and no auto-send path anywhere in the code.
