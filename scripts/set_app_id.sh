#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
umask 077

printf "Discord Application ID: "
IFS= read -r APP_ID

if ! [[ "$APP_ID" =~ ^[0-9]+$ ]]; then
    echo "Application ID must contain only numbers."
    exit 1
fi

ENV_FILE=".env"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
fi

awk -v value="$APP_ID" '
    BEGIN { replaced = 0 }
    /^DISCORD_APPLICATION_ID=/ {
        print "DISCORD_APPLICATION_ID=" value
        replaced = 1
        next
    }
    { print }
    END {
        if (!replaced) {
            print "DISCORD_APPLICATION_ID=" value
        }
    }
' "$ENV_FILE" > "$TMP_FILE"

mv "$TMP_FILE" "$ENV_FILE"
trap - EXIT

chmod 600 "$ENV_FILE"

echo "Application ID saved to private .env."
