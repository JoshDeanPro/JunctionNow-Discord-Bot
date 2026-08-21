#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
umask 077

printf "Paste Discord bot token: "
IFS= read -r -s TOKEN
printf "\n"

TOKEN="${TOKEN//$'\r'/}"
TOKEN="${TOKEN//$'\n'/}"

if [ -z "$TOKEN" ]; then
    echo "Token was empty. Nothing changed."
    exit 1
fi

ENV_FILE=".env"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

if [ -f "$ENV_FILE" ]; then
    awk '
        BEGIN { replaced = 0 }
        /^DISCORD_TOKEN=/ {
            print "DISCORD_TOKEN=__TOKEN__"
            replaced = 1
            next
        }
        { print }
        END {
            if (!replaced) {
                print "DISCORD_TOKEN=__TOKEN__"
            }
        }
    ' "$ENV_FILE" > "$TMP_FILE"
else
    cat > "$TMP_FILE" <<'ENV'
DISCORD_TOKEN=__TOKEN__
DISCORD_APPLICATION_ID=
JUNCTIONNOW_FEED_URL=https://junctionnow.com/feed/
JUNCTIONNOW_REQUEST_TIMEOUT=20
MAX_FEED_ITEMS=10
SYNC_INTERVAL_SECONDS=300
SYNC_ON_STARTUP=true
STATE_FILE=./data/state.json
STATE_MAX_POSTS=1000
STATE_MAX_EVENTS=500
STATE_BACKUP_COUNT=5
MANAGEMENT_GUILD_ID=
MANAGEMENT_CHANNEL_ID=
MANAGEMENT_OPERATOR_IDS=
LOG_LEVEL=INFO
LOG_FILE=./logs/junctionnow-bot.log
ENV
fi

TOKEN="$TOKEN" python3 - "$TMP_FILE" <<'PY'
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace("__TOKEN__", os.environ["TOKEN"])
path.write_text(text, encoding="utf-8")
PY

mv "$TMP_FILE" "$ENV_FILE"
trap - EXIT

chmod 600 "$ENV_FILE"

echo "Token saved to private .env."
echo "The token was not printed."
