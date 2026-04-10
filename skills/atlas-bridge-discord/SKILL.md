---
name: atlas_bridge_discord
description: "Post Atlas avatar session info to Discord: text, rich embed with viewer URL, optional MP4 attachment. Use after atlas_session start or offline render — not a voice/video bot inside Discord calls."
version: "0.2.0"
tags: ["atlas", "discord", "webhook", "bridge", "openclaw"]
author: "northmodellabs"
metadata:
  openclaw:
    requires:
      env: [DISCORD_WEBHOOK_URL]
      bins: [python3]
---

# Atlas → Discord (webhook bridge)

Posts to a text channel via a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks). This matches an **avatar agent** story: participants open your **browser viewer** from the channel, or you attach a **short finished video** — not live streaming into Discord voice.

## What it still is **not**

- Does **not** join **voice** channels or stream realtime WebRTC into Discord (needs a Discord bot + media gateway + bridge to LiveKit — separate product).
- Does **not** replace Google Meet / Zoom join (see `atlas-bridge-google-meet` guide).

## Prerequisites

1. Channel → Integrations → Webhooks → copy URL.
2. `export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."`

## Usage

```bash
pip install -r skills/atlas-bridge-discord/requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python3 skills/atlas-bridge-discord/scripts/post_session.py --file session.json
```

### Rich embed: viewer link (recommended)

Add a **HTTPS** field to the same JSON you get from Atlas (merge before posting):

| JSON field | Purpose |
|------------|---------|
| `viewer_url` or `client_url` | Your hosted page that loads the LiveKit room (token minted server-side or one-time link — **never** paste `token` into Discord). |
| `video_url` or `result_url` | Optional second embed pointing at a public or presigned MP4 URL. |

Example merged payload:

```json
{
  "session_id": "…",
  "room": "…",
  "mode": "conversation",
  "viewer_url": "https://yourapp.com/avatar/abc123"
}
```

### Attach a local MP4 (offline job, under ~25 MB)

```bash
python3 skills/atlas-bridge-discord/scripts/post_session.py --file session.json --video ./out.mp4
```

Discord rejects oversized files; use a link embed (`video_url`) for long renders.

## Shell tip (webhook env + pipe)

```bash
echo '{"session_id":"x","room":"r","mode":"passthrough","viewer_url":"https://example.com/v"}' \
  | DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL" python3 skills/atlas-bridge-discord/scripts/post_session.py
```

## Security

Webhook URL is a secret. Do not commit it. Do not post LiveKit `token` values into public channels.
