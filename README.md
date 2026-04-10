# avatarclaw

**North Model Labs Atlas** skills and tooling for **[OpenClaw](https://docs.openclaw.ai)** (and other agents that load `SKILL.md`): realtime **LiveKit** avatars, offline lip-sync video, and a **unified Python CLI** against [Atlas API v8](https://api.atlasv1.com).

| | |
|:--|:--|
| **Repository** | [NorthModelLabs/avatarclaw](https://github.com/NorthModelLabs/avatarclaw) *(you can rename the GitHub repo; keep `core/` + `skills/` layout)* |
| **API base** | `https://api.atlasv1.com` |
| **Dashboard** | [API keys](https://dashboard.northmodellabs.com/dashboard/keys) |

---

## Layout (Pika-Skills–style monorepo)

| Path | Purpose |
|------|---------|
| **`core/atlas_cli.py`** | **Foundation** — one CLI for Atlas REST (JSON to stdout, stable exit codes). |
| **`core/requirements.txt`** | `requests` — `pip install -r core/requirements.txt` (prefer a **venv** on macOS). |
| **`skills/atlas-avatar/`** | OpenClaw **skill**: `SKILL.md`, `references/api-reference.md`, `scripts/run_atlas_cli.py` (delegates to `core/`). |
| **`INTEGRATION.md`** | Developer integration notes. |
| **`scripts/verify-env.sh`** | Optional `GET /v1/health` + `GET /v1/me`. |
| **`skill.yaml.example`** | Optional ClawHub manifest. |

Future **connector** skills (Meet, Discord, etc.) can live alongside `skills/atlas-avatar/` and call the same **`core/`** CLI or import shared helpers.

---

## What are skills?

Each skill is a folder with a **`SKILL.md`** the agent reads for *when* and *how* to use Atlas. This repo adds a **shared Python core** so agents run **`python3 core/atlas_cli.py …`** instead of hand-assembling `curl` (curl remains documented in the skill as a fallback).

---

## Dashboard: API key

1. Open **[API keys](https://dashboard.northmodellabs.com/dashboard/keys)**.
2. Add a **payment method** if required.
3. Create a key → export `ATLAS_API_KEY`. Never commit it.

```bash
export ATLAS_API_KEY="your_key"
export ATLAS_API_BASE="https://api.atlasv1.com"   # optional
```

**Smoke check:**

```bash
cp .env.example .env   # edit; do not commit
source .env 2>/dev/null || true
./scripts/verify-env.sh
```

---

## Python CLI (core)

```bash
python3 -m venv .venv && source .venv/bin/activate   # recommended (PEP 668–safe)
pip install -r core/requirements.txt

python3 core/atlas_cli.py --help
python3 core/atlas_cli.py health
python3 core/atlas_cli.py me
python3 core/atlas_cli.py realtime create --mode conversation --face-url "https://example.com/face.jpg"
python3 core/atlas_cli.py jobs wait JOB_ID
```

**Exit codes:** `0` ok, `2` config/validation, `3` API HTTP error.

---

## Install the OpenClaw skill

[Creating skills](https://docs.openclaw.ai/tools/creating-skills):

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R skills/atlas-avatar ~/.openclaw/workspace/skills/
```

**Full monorepo clone** is recommended so `core/atlas_cli.py` exists. If you copy **only** the skill folder, set **`ATLAS_AGENT_REPO`** to the absolute path of the repo root that contains `core/`, and use:

```bash
python3 ~/.openclaw/workspace/skills/atlas-avatar/scripts/run_atlas_cli.py me
```

---

## Sample apps & npm SDK

| Resource | What it is |
|:--|:--|
| **[atlas-offline-example](https://github.com/NorthModelLabs/atlas-offline-example)** | Next.js offline pipeline. |
| **[atlas-realtime-example](https://github.com/NorthModelLabs/atlas-realtime-example)** | Next.js realtime + LLM. |
| **[@northmodellabs/atlas-react](https://www.npmjs.com/package/@northmodellabs/atlas-react)** | `useAtlasSession()` React hook. |

---

## Architecture

```
 OpenClaw (agent)  →  SKILL.md + optional core/atlas_cli.py
                              ↓
                    Atlas API (LiveKit + job queue)
```

**Billing (API):** **$5/hour** prorated — realtime **passthrough** + offline **`/v1/generate`** output; **$10/hour** prorated — realtime **conversation**.

---

## Publish to ClawHub (optional)

```bash
npm i -g clawhub
clawhub login
clawhub skill publish ./skills/atlas-avatar \
  --slug atlas-avatar \
  --name "Atlas Avatar" \
  --version 1.0.2 \
  --changelog "Monorepo: core CLI + skills/" \
  --tags latest
```

---

## Security

- Do not commit `.env` or API keys. Do not log LiveKit JWTs.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Support

- **Atlas:** [North Model Labs](https://northmodellabs.com) dashboard / support.  
- **OpenClaw:** [docs.openclaw.ai](https://docs.openclaw.ai).
