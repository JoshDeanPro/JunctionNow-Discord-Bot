#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required."
    exit 1
fi

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

ruff check app tests
pytest -q

echo
echo "Bootstrap complete."
echo "Activate: source .venv/bin/activate"
echo "Run:      ./run.sh"
