#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="${JNBOT_REPOSITORY:-JoshDeanPro/JunctionNow-Discord-Bot}"
ORIGIN="${JNBOT_ORIGIN:-https://github.com/$REPOSITORY.git}"
APP_ROOT="${JNBOT_INSTALL_ROOT:-$HOME/.local/share/junctionnow}"
COMMAND_PATH="${JNBOT_COMMAND_PATH:-$HOME/.local/bin/jnbot}"
SOURCE="${JNBOT_INSTALL_SOURCE:-$ORIGIN}"
BRANCH="${JNBOT_INSTALL_BRANCH:-main}"
CREATED=0

case "$APP_ROOT" in
    ""|/|"$HOME")
        echo "The install location is unsafe."
        exit 1
        ;;
esac

cleanup() {
    status=$?

    if [ "$status" -ne 0 ] && [ "$CREATED" -eq 1 ] && [ -d "$APP_ROOT" ]; then
        if [ -L "$COMMAND_PATH" ] && [ "$(readlink "$COMMAND_PATH")" = "$APP_ROOT/bin/jnbot" ]; then
            unlink "$COMMAND_PATH"
        fi

        find "$APP_ROOT" -depth -delete
    fi

    exit "$status"
}

trap cleanup EXIT

if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Python 3.12 is required."
    exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "Node 22 or newer is required."
    exit 1
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"

if [ "$NODE_MAJOR" -lt 22 ]; then
    echo "Node 22 or newer is required."
    exit 1
fi

if [ -e "$APP_ROOT" ]; then
    if [ ! -d "$APP_ROOT/.git" ] ||
       [ "$(git -C "$APP_ROOT" remote get-url origin 2>/dev/null || true)" != "$ORIGIN" ]; then
        echo "The install location is occupied by another application:"
        echo "  $APP_ROOT"
        exit 1
    fi

    if [ -n "$(git -C "$APP_ROOT" status --porcelain --untracked-files=no)" ]; then
        echo "The installed application has tracked local changes."
        exit 1
    fi

    git -C "$APP_ROOT" fetch --quiet origin main
    git -C "$APP_ROOT" merge --quiet --ff-only origin/main
else
    mkdir -p "$(dirname "$APP_ROOT")"
    CREATED=1

    if [ "$SOURCE" = "$ORIGIN" ] && command -v gh >/dev/null 2>&1; then
        gh repo clone "$REPOSITORY" "$APP_ROOT" -- --quiet --branch "$BRANCH" --single-branch
    else
        git clone --quiet --branch "$BRANCH" --single-branch "$SOURCE" "$APP_ROOT"
    fi

    git -C "$APP_ROOT" remote set-url origin "$ORIGIN"
fi

APP_ROOT="$(cd "$APP_ROOT" && pwd -P)"
mkdir -p "$(dirname "$COMMAND_PATH")"
COMMAND_PATH="$(cd "$(dirname "$COMMAND_PATH")" && pwd -P)/$(basename "$COMMAND_PATH")"

if [ -e "$COMMAND_PATH" ] || [ -L "$COMMAND_PATH" ]; then
    if [ ! -L "$COMMAND_PATH" ] || [ "$(readlink "$COMMAND_PATH")" != "$APP_ROOT/bin/jnbot" ]; then
        echo "The jnbot command is managed by another application:"
        echo "  $COMMAND_PATH"
        exit 1
    fi
fi

echo "Installing JunctionNow Discord Bot Manager..."
python3.12 -m venv --clear "$APP_ROOT/.venv"
"$APP_ROOT/.venv/bin/python" -m pip install --quiet --upgrade pip
"$APP_ROOT/.venv/bin/python" -m pip install --quiet -e "$APP_ROOT"
npm --prefix "$APP_ROOT/ui" ci --omit=dev --silent

if [ ! -L "$COMMAND_PATH" ]; then
    ln -s "$APP_ROOT/bin/jnbot" "$COMMAND_PATH"
fi

echo "Installed. Run: jnbot"

if [ "${JNBOT_NO_LAUNCH:-0}" != "1" ]; then
    trap - EXIT
    exec "$COMMAND_PATH"
fi

trap - EXIT
