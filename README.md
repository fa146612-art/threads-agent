# threads-agent

An AI that actually runs a Threads account — posts on its own, reads what people
say back, and answers them in its own words.

Not a scheduler. Not canned replies. Every answer is written fresh by a model
that has read the specific comment it is answering.

---

## Why it is built this way

The model's sandbox cannot reach Meta's servers, and Meta's servers cannot call
a model. So this repository sits between them as a mailbox.

```
   Threads  <---->  GitHub Actions  <---->  this repo  <---->  Claude session
              (has network)          (shared state)      (writes the words)
```

- **GitHub Actions** runs every 30 minutes. It publishes whatever is waiting in
  `outbox.json`, then pulls any new replies into `inbox.json`.
- **A Claude session** runs on its own schedule. It reads `inbox.json`, writes
  answers into `outbox.json`, and commits.
- Nothing in this repository generates reply text. That is the point.

Round trip is under an hour. Public repositories get unlimited free Actions
minutes, so running costs nothing.

---

## Files

| File | Written by | Purpose |
|---|---|---|
| `inbox.json` | Actions | New replies from other people, waiting for an answer |
| `outbox.json` | Claude | Posts and replies queued to publish |
| `metrics.json` | Actions | Views, likes and replies per post, plus quota |
| `state.json` | Actions | Which replies are already handled |
| `log.jsonl` | Actions | Append-only record of every action taken |

### outbox.json format

```json
{
  "items": [
    { "type": "post",   "text": "A single post." },
    { "type": "reply",  "reply_to_id": "17901234567890123", "text": "An answer." },
    { "type": "thread", "parts": ["First part.", "Second part.", "Third."] }
  ]
}
```

Anything that fails to publish stays queued and is retried on the next cycle.

---

## Setup

### 1. Meta app and access token

1. Go to <https://developers.facebook.com/apps> and create an app. Choose the
   **Threads** use case.
2. In **App roles → Roles**, add your own Threads account as a **Threads tester**,
   then accept the invitation at <https://www.threads.com/settings/account>
   (Website permissions → Invites).
   *Testers skip Meta's App Review entirely — this is why no review is needed.*
3. Under **Use cases → Threads API**, enable these permissions:
   `threads_basic`, `threads_content_publish`, `threads_manage_replies`.
4. Generate a **long-lived access token** (valid 60 days) and copy it.

### 2. This repository

1. Create a new **public** repository on GitHub and push these files to it.
2. Go to **Settings → Secrets and variables → Actions → New repository secret**.
   Name it `THREADS_TOKEN` and paste the token.
3. Go to **Settings → Actions → General → Workflow permissions** and select
   **Read and write permissions**. The workflow commits its own state.
4. Open the **Actions** tab and run `threads-agent` once by hand to confirm it
   works. `log.jsonl` should gain a `cycle_done` line.

### 3. Token renewal

The token expires after 60 days. Refresh it from the Meta dashboard and update
the repository secret. This is the only recurring manual task.

---

## Running it locally

```bash
pip install requests
export THREADS_TOKEN="..."
python bot/run.py
```

## Guardrails

- The account should say plainly, in its bio or pinned post, that an AI writes
  the posts and replies. It is the most interesting thing about the account, and
  pretending otherwise would be dishonest.
- Meta's limits: 250 API calls per hour, 500 posts and 1,000 replies per day.
  A 30-minute cycle uses a small fraction of that.
- Replies published by mistake can be deleted from the Threads app as normal.
