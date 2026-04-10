#!/usr/bin/env python3
"""Atlas API v8 — unified CLI for agents and humans.

Uses ATLAS_API_KEY and optional ATLAS_API_BASE (default https://api.atlasv1.com).

Exit codes: 0 ok, 2 validation/config, 3 HTTP error from API.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


def eprint(*a: object) -> None:
    print(*a, file=sys.stderr)


def base_url() -> str:
    return os.environ.get("ATLAS_API_BASE", "https://api.atlasv1.com").rstrip("/")


def auth_headers(*, required: bool) -> dict[str, str]:
    if not required:
        return {}
    key = os.environ.get("ATLAS_API_KEY", "").strip()
    if not key:
        eprint("Error: set ATLAS_API_KEY in the environment.")
        sys.exit(2)
    return {"Authorization": f"Bearer {key}"}


def emit_response(r: requests.Response) -> int:
    if not r.ok:
        eprint(f"HTTP {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2))
    except Exception:
        print(r.text or "(empty body)")
    return 0 if r.ok else 3


def cmd_index(_: argparse.Namespace) -> int:
    r = requests.get(f"{base_url()}/", timeout=30)
    return emit_response(r)


def cmd_health(_: argparse.Namespace) -> int:
    r = requests.get(f"{base_url()}/v1/health", timeout=30)
    return emit_response(r)


def cmd_status(_: argparse.Namespace) -> int:
    r = requests.get(
        f"{base_url()}/v1/status",
        headers={**auth_headers(required=True)},
        timeout=30,
    )
    return emit_response(r)


def cmd_me(_: argparse.Namespace) -> int:
    r = requests.get(
        f"{base_url()}/v1/me",
        headers={**auth_headers(required=True)},
        timeout=30,
    )
    return emit_response(r)


def cmd_realtime_create(args: argparse.Namespace) -> int:
    b = base_url()
    h = auth_headers(required=True)
    mode = args.mode or "conversation"
    if args.face:
        p = Path(args.face)
        if not p.is_file():
            eprint(f"Error: face file not found: {p}")
            return 2
        mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        with p.open("rb") as fh:
            r = requests.post(
                f"{b}/v1/realtime/session",
                headers=h,
                data={"mode": mode},
                files={"face": (p.name, fh, mime)},
                timeout=120,
            )
        return emit_response(r)
    body: dict[str, Any] = {"mode": mode}
    if args.face_url:
        body["face_url"] = args.face_url
    r = requests.post(
        f"{b}/v1/realtime/session",
        headers={**h, "Content-Type": "application/json"},
        json=body,
        timeout=120,
    )
    return emit_response(r)


def cmd_realtime_get(args: argparse.Namespace) -> int:
    r = requests.get(
        f"{base_url()}/v1/realtime/session/{args.session_id}",
        headers={**auth_headers(required=True)},
        timeout=30,
    )
    return emit_response(r)


def cmd_realtime_patch(args: argparse.Namespace) -> int:
    p = Path(args.face)
    if not p.is_file():
        eprint(f"Error: face file not found: {p}")
        return 2
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    with p.open("rb") as fh:
        r = requests.patch(
            f"{base_url()}/v1/realtime/session/{args.session_id}",
            headers={**auth_headers(required=True)},
            files={"face": (p.name, fh, mime)},
            timeout=120,
        )
    return emit_response(r)


def cmd_realtime_delete(args: argparse.Namespace) -> int:
    r = requests.delete(
        f"{base_url()}/v1/realtime/session/{args.session_id}",
        headers={**auth_headers(required=True)},
        timeout=60,
    )
    return emit_response(r)


def cmd_generate(args: argparse.Namespace) -> int:
    audio = Path(args.audio)
    image = Path(args.image)
    if not audio.is_file() or not image.is_file():
        eprint("Error: --audio and --image must be existing files.")
        return 2
    am = mimetypes.guess_type(str(audio))[0] or "application/octet-stream"
    im = mimetypes.guess_type(str(image))[0] or "application/octet-stream"
    h = {**auth_headers(required=True)}
    if args.callback_url:
        h["X-Callback-URL"] = args.callback_url
    with audio.open("rb") as af, image.open("rb") as imf:
        r = requests.post(
            f"{base_url()}/v1/generate",
            headers=h,
            files={
                "audio": (audio.name, af, am),
                "image": (image.name, imf, im),
            },
            timeout=120,
        )
    return emit_response(r)


def cmd_jobs_list(args: argparse.Namespace) -> int:
    params: dict[str, int] = {}
    if args.limit is not None:
        params["limit"] = args.limit
    if args.offset is not None:
        params["offset"] = args.offset
    r = requests.get(
        f"{base_url()}/v1/jobs",
        headers={**auth_headers(required=True)},
        params=params or None,
        timeout=30,
    )
    return emit_response(r)


def cmd_jobs_get(args: argparse.Namespace) -> int:
    r = requests.get(
        f"{base_url()}/v1/jobs/{args.job_id}",
        headers={**auth_headers(required=True)},
        timeout=30,
    )
    return emit_response(r)


def cmd_jobs_result(args: argparse.Namespace) -> int:
    r = requests.get(
        f"{base_url()}/v1/jobs/{args.job_id}/result",
        headers={**auth_headers(required=True)},
        timeout=30,
    )
    return emit_response(r)


def cmd_jobs_wait(args: argparse.Namespace) -> int:
    deadline = time.time() + args.timeout
    h = auth_headers(required=True)
    b = base_url()
    while time.time() < deadline:
        r = requests.get(f"{b}/v1/jobs/{args.job_id}", headers=h, timeout=30)
        try:
            data = r.json()
        except Exception:
            eprint(r.text)
            return 3
        status = data.get("status")
        print(json.dumps(data, indent=2))
        if status in ("completed", "failed"):
            return 0 if status == "completed" else 3
        time.sleep(args.interval)
    eprint("Error: timeout waiting for job terminal state.")
    return 3


def cmd_avatar_session(args: argparse.Namespace) -> int:
    """POST /v1/avatar/session — BYO LiveKit (plugin flow)."""
    h = auth_headers(required=True)
    data = {
        "livekit_url": args.livekit_url,
        "livekit_token": args.livekit_token,
        "room_name": args.room_name,
    }
    if args.avatar_image:
        p = Path(args.avatar_image)
        if not p.is_file():
            eprint(f"Error: avatar_image not found: {p}")
            return 2
        mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        with p.open("rb") as fh:
            r = requests.post(
                f"{base_url()}/v1/avatar/session",
                headers=h,
                data=data,
                files={"avatar_image": (p.name, fh, mime)},
                timeout=120,
            )
        return emit_response(r)
    r = requests.post(
        f"{base_url()}/v1/avatar/session",
        headers=h,
        data=data,
        timeout=120,
    )
    return emit_response(r)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Atlas API CLI — use ATLAS_API_KEY and optional ATLAS_API_BASE.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("index", help="GET / (API index, no auth)").set_defaults(fn=cmd_index)
    sub.add_parser("health", help="GET /v1/health (no auth)").set_defaults(fn=cmd_health)
    sub.add_parser("status", help="GET /v1/status").set_defaults(fn=cmd_status)
    sub.add_parser("me", help="GET /v1/me").set_defaults(fn=cmd_me)

    rt = sub.add_parser("realtime", help="Realtime LiveKit sessions")
    rts = rt.add_subparsers(dest="rtc", required=True)

    c = rts.add_parser("create", help="POST /v1/realtime/session")
    c.add_argument("--mode", choices=("conversation", "passthrough"), default="conversation")
    c.add_argument("--face-url", dest="face_url", default="", help="HTTPS URL (JSON body)")
    c.add_argument("--face", default="", help="Local image file (multipart)")
    c.set_defaults(fn=cmd_realtime_create)

    g = rts.add_parser("get", help="GET /v1/realtime/session/{id}")
    g.add_argument("session_id")
    g.set_defaults(fn=cmd_realtime_get)

    pa = rts.add_parser("patch", help="PATCH face swap — multipart face file")
    pa.add_argument("session_id")
    pa.add_argument("--face", required=True)
    pa.set_defaults(fn=cmd_realtime_patch)

    d = rts.add_parser("delete", help="DELETE /v1/realtime/session/{id}")
    d.add_argument("session_id")
    d.set_defaults(fn=cmd_realtime_delete)

    gen = sub.add_parser("generate", help="POST /v1/generate (offline video job)")
    gen.add_argument("--audio", required=True)
    gen.add_argument("--image", required=True)
    gen.add_argument("--callback-url", default="", help="X-Callback-URL header (HTTPS)")
    gen.set_defaults(fn=cmd_generate)

    jobs = sub.add_parser("jobs", help="Job queue")
    js = jobs.add_subparsers(dest="jobcmd", required=True)

    jl = js.add_parser("list", help="GET /v1/jobs")
    jl.add_argument("--limit", type=int, default=None)
    jl.add_argument("--offset", type=int, default=None)
    jl.set_defaults(fn=cmd_jobs_list)

    jg = js.add_parser("get", help="GET /v1/jobs/{id}")
    jg.add_argument("job_id")
    jg.set_defaults(fn=cmd_jobs_get)

    jr = js.add_parser("result", help="GET /v1/jobs/{id}/result")
    jr.add_argument("job_id")
    jr.set_defaults(fn=cmd_jobs_result)

    jw = js.add_parser("wait", help="Poll GET /v1/jobs/{id} until completed or failed")
    jw.add_argument("job_id")
    jw.add_argument("--interval", type=float, default=2.0)
    jw.add_argument("--timeout", type=int, default=600)
    jw.set_defaults(fn=cmd_jobs_wait)

    av = sub.add_parser("avatar-session", help="POST /v1/avatar/session (BYO LiveKit)")
    av.add_argument("--livekit-url", required=True)
    av.add_argument("--livekit-token", required=True)
    av.add_argument("--room-name", required=True)
    av.add_argument("--avatar-image", default="", help="Optional face image file")
    av.set_defaults(fn=cmd_avatar_session)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    fn = getattr(args, "fn", None)
    if fn is None:
        parser.print_help()
        sys.exit(2)
    sys.exit(fn(args))


if __name__ == "__main__":
    main()
