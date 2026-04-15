#!/usr/bin/env python3
# Copyright North Model Labs — MIT (see repo LICENSE)
"""Structured Atlas API checks for every endpoint wired in ``core/atlas_api.py``.

Runs from **monorepo root** (or set ``PYTHONPATH`` to ``core/`` and ``cwd`` to root).

**No key:** ``GET /``, ``GET /v1/health`` only.

**With ``ATLAS_API_KEY``:** also ``GET /v1/status``, ``GET /v1/me``, ``GET /v1/jobs``.

**Realtime (default when key is set):** ``POST`` session → ``GET`` session → ``POST …/viewer``
→ optional ``PATCH`` face → ``DELETE`` — **may bill** (prorated). Pass ``--no-realtime`` to skip.

**``--offline-audio`` + ``--offline-image``:** ``POST /v1/generate`` then poll until terminal
state (or ``--offline-no-wait`` for 202 only).

**``POST /v1/avatar/session``:** probed only with ``--probe-avatar-session`` (often 404 on
public API — soft-skip unless you know the route exists).

Examples::

  python3 scripts/bridges/test-atlas-api-harness.py
  ATLAS_API_KEY=… python3 scripts/bridges/test-atlas-api-harness.py --no-realtime
  ATLAS_API_KEY=… python3 scripts/bridges/test-atlas-api-harness.py --patch-face ./face.jpg
  ATLAS_API_KEY=… python3 scripts/bridges/test-atlas-api-harness.py --offline-audio a.wav --offline-image f.jpg

Exit codes: ``0`` all required checks passed, ``1`` failure, ``2`` bad CLI/config.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CORE = _ROOT / "core"
if not _CORE.is_dir():
    print(f"Expected monorepo root with core/ at {_CORE}", file=sys.stderr)
    sys.exit(2)
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

import atlas_api as api  # noqa: E402


def _ok(name: str, r) -> bool:
    ok = r.ok
    extra = ""
    if ok:
        try:
            body = r.json()
            extra = f" keys={list(body.keys())[:8]}"
        except Exception:
            extra = ""
    print(f"[{'OK' if ok else 'FAIL'}] {name} HTTP {r.status_code}{extra}")
    if not ok:
        try:
            print(r.text[:800])
        except Exception:
            pass
    return ok


def _require(name: str, r) -> None:
    if not _ok(name, r):
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--no-realtime",
        action="store_true",
        help="Skip realtime create/get/viewer/delete (no billing for that flow).",
    )
    p.add_argument(
        "--face",
        default="",
        help="Local image for realtime create multipart (optional).",
    )
    p.add_argument(
        "--face-url",
        default="",
        dest="face_url",
        help="HTTPS URL for realtime create JSON (optional).",
    )
    p.add_argument(
        "--patch-face",
        default="",
        dest="patch_face",
        help="If set, PATCH this face file mid-session before DELETE.",
    )
    p.add_argument("--offline-audio", default="", help="File for POST /v1/generate.")
    p.add_argument("--offline-image", default="", help="File for POST /v1/generate.")
    p.add_argument(
        "--offline-no-wait",
        action="store_true",
        help="Only assert 202 from /v1/generate; do not poll job.",
    )
    p.add_argument(
        "--offline-wait-timeout",
        type=int,
        default=600,
        help="Seconds to poll offline job (default 600).",
    )
    p.add_argument(
        "--probe-avatar-session",
        action="store_true",
        help="POST /v1/avatar/session with placeholder creds (expect failure on many deployments).",
    )
    args = p.parse_args()

    has_key = bool(os.environ.get("ATLAS_API_KEY", "").strip())
    base = api.base_url()
    print(f"ATLAS_API_BASE={base}  ATLAS_API_KEY={'set' if has_key else 'unset'}")

    _require("GET / (index)", api.api_index())
    _require("GET /v1/health", api.api_health())

    if not has_key:
        print("Done (no auth checks — set ATLAS_API_KEY for full harness).")
        return

    _require("GET /v1/status", api.api_status())
    _require("GET /v1/me", api.api_me())
    _require("GET /v1/jobs", api.api_jobs_list(5, 0))

    if args.no_realtime:
        print("Skipped realtime (--no-realtime).")
    else:
        face = args.face.strip() or None
        face_url = args.face_url.strip() or None
        r = api.api_realtime_create("passthrough", face, face_url)
        _require("POST /v1/realtime/session", r)
        try:
            sess = r.json()
        except Exception:
            print("FAIL: realtime create body not JSON", file=sys.stderr)
            sys.exit(1)
        sid = (sess.get("session_id") or "").strip()
        if not sid:
            print("FAIL: no session_id in create response", file=sys.stderr)
            sys.exit(1)
        print(f"    session_id={sid} (redacted token)")

        _require("GET /v1/realtime/session/{id}", api.api_realtime_get(sid))
        _require("POST /v1/realtime/session/{id}/viewer", api.api_realtime_viewer(sid))

        if args.patch_face.strip():
            _require(
                "PATCH /v1/realtime/session/{id}",
                api.api_realtime_patch(sid, args.patch_face.strip()),
            )

        _require("DELETE /v1/realtime/session/{id}", api.api_realtime_delete(sid))

    oa = args.offline_audio.strip()
    oi = args.offline_image.strip()
    if oa or oi:
        if not (oa and oi):
            print("FAIL: --offline-audio and --offline-image must be set together.", file=sys.stderr)
            sys.exit(2)
        r = api.api_generate(oa, oi, None)
        _require("POST /v1/generate", r)
        try:
            job = r.json()
        except Exception:
            print("FAIL: generate response body not JSON", file=sys.stderr)
            sys.exit(1)
        jid = (job.get("job_id") or "").strip()
        if not jid:
            print("FAIL: no job_id in generate response", file=sys.stderr)
            sys.exit(1)
        print(f"    job_id={jid}")
        if args.offline_no_wait:
            print("Skipped job poll (--offline-no-wait).")
        else:
            ec = api.api_jobs_wait(jid, 2.0, args.offline_wait_timeout)
            if ec != 0:
                sys.exit(ec)
            res = api.api_jobs_result(jid)
            _require("GET /v1/jobs/{id}/result", res)

    if args.probe_avatar_session:
        r = api.api_avatar_session(
            "wss://example.invalid/",
            "placeholder-token",
            "room-placeholder",
            None,
        )
        if _ok("POST /v1/avatar/session (probe — may 404)", r):
            pass
        else:
            print("    (expected on deployments without this route — not a harness failure)")

    print("All required harness checks passed.")


if __name__ == "__main__":
    main()
