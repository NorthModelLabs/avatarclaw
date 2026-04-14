#!/usr/bin/env bash
# Long-running Discord bot: @mention or /ask → Atlas offline lip-sync MP4.
# Needs: DISCORD_BOT_TOKEN, ATLAS_API_KEY; optional ELEVENLABS_API_KEY, .env at repo root.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

if [[ -f "$REPO/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$REPO/.env"
  set +a
fi

for d in "$REPO/.venv-cc-readme" "$REPO/.venv" "$REPO/venv"; do
  if [[ -d "$d" ]]; then
    # shellcheck source=/dev/null
    source "$d/bin/activate"
    break
  fi
done

exec python3 "$REPO/skills/atlas-bridge-discord/scripts/discord_avatar_bot.py"
