---
name: atlas_bridge_google_meet
description: "Combine Atlas avatars with Google Meet: honest limits, meet_assist checklist/open/paste-message, and integration_guide JSON. Does not join Meet as a hosted bot."
version: "0.2.0"
tags: ["atlas", "google-meet", "bridge", "openclaw", "integration"]
author: "northmodellabs"
metadata:
  openclaw:
    requires:
      bins: [python3]
---

# Atlas + Google Meet

## What this skill **does not** do

There is **no hosted Meet bot** in this repo (no synthetic participant that joins `meet.google.com` on your behalf via Atlas HTTP). Products that offer that ([example pattern](https://github.com/Pika-Labs/Pika-Skills)) ship **their own** join API and cloud fleet.

**Atlas here** = `POST /v1/realtime/session` → **LiveKit** for **your** viewer app or pipeline.

## What we ship: `meet_assist.py` (human + viewer workflow)

| Subcommand | Purpose |
|------------|---------|
| `checklist --meet-url URL` | JSON steps: join Meet yourself, start Atlas session, share viewer, leave session when done. |
| `open-meet --meet-url URL` | Open the Meet link in the default browser (you still join as a user). |
| `paste-message --meet-url URL -f session.json [--viewer-url HTTPS]` | Text block for Meet **chat** (session ids + link to your avatar page). |

```bash
python3 skills/atlas-bridge-google-meet/scripts/meet_assist.py checklist --meet-url "https://meet.google.com/xxx-xxxx-xxx"
python3 skills/atlas-bridge-google-meet/scripts/meet_assist.py open-meet --meet-url "https://meet.google.com/xxx-xxxx-xxx"
python3 skills/atlas-bridge-google-meet/scripts/meet_assist.py paste-message \
  --meet-url "https://meet.google.com/xxx-xxxx-xxx" \
  -f session.json \
  --viewer-url "https://yourapp.com/avatar/..."
```

**Flow:** `atlas_session.py start … > session.json` → add or pass **`viewer_url`** → `paste-message` → paste into Meet chat; or screen-share your viewer tab.

## Practical patterns (same as before)

1. **Link in chat** — Viewer opens your HTTPS page (token minted server-side).
2. **Presenter** — Screen-share the tab running the Atlas/LiveKit client.
3. **Build or buy a bot** — Separate project: Meet media bridge → Atlas **passthrough** (compliance + engineering).

## Machine-readable summary

```bash
python3 skills/atlas-bridge-google-meet/scripts/integration_guide.py
```

Returns JSON with doc hints and `meeting_bot_layer_note`.
