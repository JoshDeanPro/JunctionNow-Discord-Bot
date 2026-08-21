#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Python 3.12 is required."
    exit 1
fi

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"

ruff check app tests
pytest -q
npm --prefix ui ci

echo
echo "Development environment ready."
echo "Run: ./bin/jnbot"
