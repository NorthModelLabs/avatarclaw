#!/usr/bin/env python3
"""Human-in-the-loop helper for using Atlas avatars alongside Google Meet.

This does **not** join Meet as a synthetic participant (no meeting-bot). It helps you:
  open the Meet URL, print a checklist, and draft chat text after you create an Atlas session.

True auto-join (like third-party hosted meeting skills) needs a separate bot fleet + product API.
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path


def _looks_like_meet_url(url: str) -> bool:
    u = url.lower().split("?", 1)[0].rstrip("/")
    return "meet.google.com/" in u or ".google.com/meet/" in u


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def cmd_checklist(args: argparse.Namespace) -> int:
    url = args.meet_url.strip()
    if not _looks_like_meet_url(url):
        _die("meet_url should be a Google Meet link (meet.google.com/...)")
    print(
        json.dumps(
            {
                "meet_url": url,
                "steps": [
                    "Join the Meet as yourself (this script does not log in as a bot).",
                    "Create an Atlas realtime session (atlas_session.py start or atlas_cli.py realtime create).",
                    "Host a small web viewer that connects to LiveKit using session token (server-side mint).",
                    "Paste viewer_url into Meet chat — or screen-share that browser tab.",
                    "When done: atlas_session leave / realtime delete to stop billing.",
                ],
                "limitations": (
                    "No OSS Meet-bot join in this repo; compare hosted skills that ship their own join API."
                ),
            },
            indent=2,
        )
    )
    return 0


def cmd_open_meet(args: argparse.Namespace) -> int:
    url = args.meet_url.strip()
    if not _looks_like_meet_url(url):
        _die("Invalid meet_url")
    webbrowser.open(url)
    print(json.dumps({"ok": True, "opened": url}))
    return 0


def cmd_paste_message(args: argparse.Namespace) -> int:
    url = args.meet_url.strip()
    if not _looks_like_meet_url(url):
        _die("Invalid meet_url")
    sp = Path(args.session_file)
    if not sp.is_file():
        _die(f"Not a file: {sp}")
    raw = sp.read_text(encoding="utf-8")
    try:
        sess = json.loads(raw)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in session file: {e}")
    sid = sess.get("session_id", "?")
    room = sess.get("room", "?")
    mode = sess.get("mode", "?")
    viewer = (args.viewer_url or sess.get("viewer_url") or sess.get("client_url") or "").strip()
    lines = [
        "Atlas avatar (LiveKit) — I'm running the session in a browser viewer.",
        f"Meet link: {url}",
        f"(session_id={sid}, room={room}, mode={mode})",
    ]
    if viewer:
        lines.insert(2, f"Open avatar: {viewer}")
    else:
        lines.insert(
            2,
            "Open avatar: <add viewer_url to session JSON or pass --viewer-url https://...>",
        )
    text = "\n".join(lines)
    print(text)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("checklist", help="Print JSON checklist (no network)")
    c.add_argument("--meet-url", required=True)
    c.set_defaults(fn=cmd_checklist)

    o = sub.add_parser("open-meet", help="Open Meet URL in default browser")
    o.add_argument("--meet-url", required=True)
    o.set_defaults(fn=cmd_open_meet)

    m = sub.add_parser(
        "paste-message",
        help="Draft text for Meet chat from Atlas session JSON + meet URL",
    )
    m.add_argument("--meet-url", required=True)
    m.add_argument("--session-file", "-f", required=True, help="JSON from realtime create")
    m.add_argument("--viewer-url", default="", help="HTTPS viewer link (if not in JSON)")
    m.set_defaults(fn=cmd_paste_message)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
