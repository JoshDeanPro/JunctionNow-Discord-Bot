#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Missing .venv."
    echo "Run: ./scripts/bootstrap_mac.sh"
    exit 1
fi

source .venv/bin/activate

exec python -m app.main
