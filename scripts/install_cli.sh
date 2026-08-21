#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HOME/.local/bin"
TARGET="$DEST/jnbot"

mkdir -p "$DEST"

ln -sfn \
    "$ROOT/bin/jnbot" \
    "$TARGET"

echo "Installed:"
echo "  $TARGET"
echo
echo "Run:"
echo "  jnbot"
