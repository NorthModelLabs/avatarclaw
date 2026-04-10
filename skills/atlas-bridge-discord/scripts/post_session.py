#!/usr/bin/env python3
"""Post Atlas session info to Discord: text + optional embeds + optional video file.

Webhook cannot join voice or stream live video into a call. For an *avatar agent* workflow:
  - Put ``viewer_url`` (or ``client_url``) in the JSON — your hosted page that connects to
    LiveKit server-side or via short-lived links (never paste ``token`` into Discord).
  - Optional ``--video`` attaches a finished MP4 (e.g. offline job) if under Discord's limit.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

import requests

# Discord webhook attachment limit (MiB); see Discord API docs.
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _embeds_from_json(data: dict) -> list[dict]:
    out: list[dict] = []
    viewer = (data.get("viewer_url") or data.get("client_url") or "").strip()
    if viewer:
        out.append(
            {
                "title": "Open avatar (browser)",
                "description": (
                    "Hosted viewer — keep LiveKit tokens off public channels; "
                    "issue short-lived links or embed credentials server-side."
                ),
                "url": viewer,
                "color": 0x5865F2,
            }
        )
    video_url = (data.get("video_url") or data.get("result_url") or "").strip()
    if video_url:
        out.append(
            {
                "title": "Video / render link",
                "url": video_url,
                "description": "Public or signed URL to a finished render (optional).",
            }
        )
    return out


def main() -> int:
    p = argparse.ArgumentParser(
        description="Post Atlas session summary to Discord (embeds + optional MP4 attach)",
    )
    p.add_argument("--file", "-f", help="Path to JSON file (else stdin)")
    p.add_argument(
        "--video",
        metavar="PATH",
        help="Attach local MP4/video file (max ~25 MB; typical for offline /v1/generate output)",
    )
    args = p.parse_args()
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("Set DISCORD_WEBHOOK_URL", file=sys.stderr)
        return 2
    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    data = json.loads(raw)
    sid = data.get("session_id", "?")
    room = data.get("room", "?")
    mode = data.get("mode", "?")
    pricing = data.get("pricing", "")
    lines = [
        "**Atlas avatar session**",
        f"• session_id: `{sid}`",
        f"• room: `{room}`",
        f"• mode: `{mode}`",
    ]
    if pricing:
        lines.append(f"• pricing: {pricing}")
    embeds = _embeds_from_json(data)
    if not embeds:
        lines.append(
            "• Add **`viewer_url`** (HTTPS) to this JSON for a clickable in-channel link to your web viewer."
        )
        lines.append(
            "• Or use **`--video`** with a short MP4 from an offline job (under 25 MB)."
        )
    content = "\n".join(lines)

    video_path = Path(args.video).resolve() if args.video else None
    if video_path is not None:
        if not video_path.is_file():
            print(f"Error: --video not a file: {video_path}", file=sys.stderr)
            return 2
        n = video_path.stat().st_size
        if n > MAX_ATTACHMENT_BYTES:
            print(
                f"Error: file {n} bytes exceeds Discord webhook limit (~25 MB).",
                file=sys.stderr,
            )
            return 2

    body: dict = {"content": content}
    if embeds:
        body["embeds"] = embeds

    if video_path is not None:
        mime = mimetypes.guess_type(str(video_path))[0] or "application/octet-stream"
        with video_path.open("rb") as fh:
            r = requests.post(
                url,
                data={"payload_json": json.dumps(body)},
                files={"files[0]": (video_path.name, fh, mime)},
                timeout=120,
            )
    else:
        r = requests.post(url, json=body, timeout=30)

    if not r.ok:
        print(r.text, file=sys.stderr)
        return 3
    print(json.dumps({"ok": True, "discord_status": r.status_code}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
