#!/usr/bin/env python3
"""Local demo: Atlas **conversation** session + browser viewer (mic ↔ agent).

You talk in the **localhost** page (LiveKit); Atlas runs STT/LLM/TTS/avatar on the
hosted side. This does **not** inject a participant into Google Meet — for Meet,
**Present** this tab in Meet (Share → Window) so others see/hear the same stream.

Prereqs: repo root with skills/, ``pip install -r core/requirements.txt``, ``ATLAS_API_KEY``.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def repo_root() -> Path:
    env = os.environ.get("ATLAS_AGENT_REPO", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "skills" / "atlas-avatar" / "scripts" / "atlas_session.py").is_file():
            return p
        _die(f"ATLAS_AGENT_REPO invalid: {p}")
    here = Path(__file__).resolve().parent
    for d in (here, *here.parents):
        if (d / "skills" / "atlas-avatar" / "scripts" / "atlas_session.py").is_file():
            return d
    _die("Could not find monorepo root (set ATLAS_AGENT_REPO).")


def _viewer_html(cfg_b64: str) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Atlas local viewer</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 1rem; max-width: 52rem; }}
  #log {{ white-space: pre-wrap; background: #111; color: #cfc; padding: .75rem; border-radius: 8px; min-height: 4rem; }}
  h1 {{ font-size: 1.1rem; }}
</style>
<body data-cfg="{cfg_b64}">
<h1>Atlas conversation (local)</h1>
<p>Allow the microphone when prompted. Speak normally — audio goes to LiveKit, not to Google Meet.</p>
<p><strong>In Meet:</strong> Share → <strong>this Chrome tab</strong> so the call sees the avatar.</p>
<div id="log">Connecting…</div>
<script type="module">
import {{ Room, RoomEvent, Track }} from "https://cdn.jsdelivr.net/npm/livekit-client@2.9.9/+esm";

const log = (m) => {{
  const el = document.getElementById("log");
  el.textContent += "\\n" + m;
  console.log(m);
}};

const b64 = document.body.getAttribute("data-cfg");
const cfg = JSON.parse(atob(b64));
const room = new Room({{ adaptiveStream: true, dynacast: true }});

room.on(RoomEvent.Disconnected, (r) => log("Disconnected: " + (r || "")));
room.on(RoomEvent.Reconnecting, () => log("Reconnecting…"));
room.on(RoomEvent.Reconnected, () => log("Reconnected."));
room.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {{
  if (track.kind === Track.Kind.Audio) {{
    const el = track.attach();
    el.autoplay = true;
    el.playsInline = true;
    document.body.appendChild(el);
    log("Subscribed to audio from " + (participant?.identity || "?"));
  }}
  if (track.kind === Track.Kind.Video) {{
    const el = track.attach();
    el.autoplay = true;
    el.playsInline = true;
    el.style.maxWidth = "100%";
    document.body.appendChild(el);
    log("Video track from " + (participant?.identity || "?"));
  }}
}});

try {{
  await room.connect(cfg.url, cfg.token);
  log("Connected to room.");
  await room.localParticipant.setMicrophoneEnabled(true);
  log("Microphone on — talk now.");
}} catch (e) {{
  log("Error: " + (e?.message || e));
}}
</script>
</body>
</html>
""".encode(
        "utf-8"
    )


class _QuietHandler(BaseHTTPRequestHandler):
    page: ClassVar[bytes] = b""

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/", "/viewer"):
            self.send_error(404)
            return
        body = self.page
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--face-url", default="", help="HTTPS face image for conversation mode")
    p.add_argument("--port", type=int, default=9876, help="Local HTTP port for viewer")
    p.add_argument(
        "--meet-url",
        default="",
        help="Optional: open this Meet link in your browser after the viewer",
    )
    p.add_argument("--no-browser", action="store_true", help="Do not open a browser")
    args = p.parse_args()

    root = repo_root()
    atlas = root / "skills" / "atlas-avatar" / "scripts" / "atlas_session.py"
    if not atlas.is_file():
        _die(f"Missing {atlas}")

    cmd = [sys.executable, str(atlas), "start", "--mode", "conversation"]
    if args.face_url.strip():
        cmd += ["--face-url", args.face_url.strip()]

    print("Starting Atlas conversation session…", file=sys.stderr)
    r = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return r.returncode
    raw = r.stdout.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        _die(f"Bad JSON from atlas_session: {e}\n{raw[:800]}")
    url = data.get("livekit_url")
    token = data.get("token")
    sid = data.get("session_id")
    if not url or not token or not sid:
        _die("Session JSON missing livekit_url, token, or session_id")

    cfg = {"url": url, "token": token}
    cfg_b64 = base64.b64encode(json.dumps(cfg).encode("utf-8")).decode("ascii")
    page = _viewer_html(cfg_b64)
    _QuietHandler.page = page

    httpd = HTTPServer(("127.0.0.1", args.port), _QuietHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    viewer = f"http://127.0.0.1:{args.port}/"
    print(f"Viewer: {viewer}", file=sys.stderr)

    if not args.no_browser:
        webbrowser.open(viewer, new=1)
        if args.meet_url.strip():
            webbrowser.open(args.meet_url.strip(), new=2)

    def cleanup(*_: object) -> None:
        print("\nLeaving Atlas session…", file=sys.stderr)
        try:
            lr = subprocess.run(
                [sys.executable, str(atlas), "leave", "--session-id", sid],
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                timeout=60,
            )
            if lr.stdout:
                print(lr.stdout, end="", file=sys.stderr)
            if lr.returncode != 0 and lr.stderr:
                print(lr.stderr, end="", file=sys.stderr)
        except Exception as e:
            print(f"leave failed: {e}", file=sys.stderr)
        try:
            httpd.shutdown()
        except Exception:
            pass

    print(
        "If Meet is open: Share → Window → pick the **viewer** tab so the call sees the avatar.\n"
        "Press Enter here to end the Atlas session and stop the local server.",
        file=sys.stderr,
    )
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
