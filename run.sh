#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Missing .venv"
    exit 1
fi

exec .venv/bin/python -m app.main
