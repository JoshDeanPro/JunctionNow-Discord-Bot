#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="${JNBOT_REPOSITORY:-JoshDeanPro/JunctionNow-Discord-Bot}"
ORIGIN="${JNBOT_ORIGIN:-https://github.com/$REPOSITORY.git}"
APP_ROOT="${JNBOT_INSTALL_ROOT:-$HOME/.local/share/junctionnow}"
COMMAND_PATH="${JNBOT_COMMAND_PATH:-$HOME/.local/bin/jnbot}"
SOURCE="${JNBOT_INSTALL_SOURCE:-$ORIGIN}"
BRANCH="${JNBOT_INSTALL_BRANCH:-main}"
CREATED=0
RUNTIME_TEMP=""

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

    if [ -n "$RUNTIME_TEMP" ] && [ -d "$RUNTIME_TEMP" ]; then
        find "$RUNTIME_TEMP" -depth -delete
    fi

    exit "$status"
}

trap cleanup EXIT

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
RUNTIME_ROOT="$APP_ROOT/.runtime"
mkdir -p "$RUNTIME_ROOT"

PYTHON_COMMAND=""

for candidate in python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' 2>/dev/null; then
        PYTHON_COMMAND="$candidate"
        break
    fi
done

if [ -z "$PYTHON_COMMAND" ]; then
    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is required to install the private Python runtime."
        exit 1
    fi

    echo "Installing a private Python 3.12 runtime..."
    mkdir -p "$RUNTIME_ROOT/bin" "$RUNTIME_ROOT/python" "$RUNTIME_ROOT/uv-cache"
    curl -LsSf https://astral.sh/uv/install.sh |
        env UV_INSTALL_DIR="$RUNTIME_ROOT/bin" UV_NO_MODIFY_PATH=1 sh >/dev/null
    UV_PYTHON_INSTALL_DIR="$RUNTIME_ROOT/python" \
    UV_CACHE_DIR="$RUNTIME_ROOT/uv-cache" \
        "$RUNTIME_ROOT/bin/uv" python install 3.12 >/dev/null
    PYTHON_COMMAND="$RUNTIME_ROOT/bin/uv"
fi

NODE_COMMAND=""
NPM_COMMAND=""

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 &&
   [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]; then
    NODE_COMMAND="$(command -v node)"
    NPM_COMMAND="$(command -v npm)"
else
    if ! command -v curl >/dev/null 2>&1; then
        echo "curl is required to install the private Node runtime."
        exit 1
    fi

    case "$(uname -s)-$(uname -m)" in
        Darwin-arm64) NODE_PLATFORM="darwin-arm64" ;;
        Darwin-x86_64) NODE_PLATFORM="darwin-x64" ;;
        Linux-aarch64|Linux-arm64) NODE_PLATFORM="linux-arm64" ;;
        Linux-x86_64) NODE_PLATFORM="linux-x64" ;;
        *)
            echo "This computer cannot use the automatic Node runtime."
            exit 1
            ;;
    esac

    echo "Installing a private Node 22 runtime..."
    NODE_VERSION="$(curl -fsSL https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt | sed -n "s/ .*node-\(v[0-9.]*\)-$NODE_PLATFORM.tar.xz/\1/p" | head -n 1)"

    if [ -z "$NODE_VERSION" ]; then
        echo "Unable to find the current Node 22 runtime."
        exit 1
    fi

    RUNTIME_TEMP="$(mktemp -d "$RUNTIME_ROOT/node.new.XXXXXX")"
    NODE_ARCHIVE="$RUNTIME_TEMP/node.tar.xz"
    curl -fsSL "https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-$NODE_PLATFORM.tar.xz" -o "$NODE_ARCHIVE"
    EXPECTED_HASH="$(curl -fsSL "https://nodejs.org/dist/$NODE_VERSION/SHASUMS256.txt" | awk "/node-$NODE_VERSION-$NODE_PLATFORM.tar.xz$/ {print \$1}")"

    if command -v shasum >/dev/null 2>&1; then
        ACTUAL_HASH="$(shasum -a 256 "$NODE_ARCHIVE" | awk '{print $1}')"
    else
        ACTUAL_HASH="$(sha256sum "$NODE_ARCHIVE" | awk '{print $1}')"
    fi

    if [ -z "$EXPECTED_HASH" ] || [ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
        echo "The private Node runtime failed verification."
        exit 1
    fi

    tar -xJf "$NODE_ARCHIVE" -C "$RUNTIME_TEMP"
    if [ -d "$RUNTIME_ROOT/node" ]; then
        find "$RUNTIME_ROOT/node" -depth -delete
    fi
    mv "$RUNTIME_TEMP/node-$NODE_VERSION-$NODE_PLATFORM" "$RUNTIME_ROOT/node"
    find "$RUNTIME_TEMP" -depth -delete
    RUNTIME_TEMP=""
    NODE_COMMAND="$RUNTIME_ROOT/node/bin/node"
    NPM_COMMAND="$RUNTIME_ROOT/node/bin/npm"
fi

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
if [ "$(basename "$PYTHON_COMMAND")" = "uv" ]; then
    UV_PYTHON_INSTALL_DIR="$RUNTIME_ROOT/python" \
    UV_CACHE_DIR="$RUNTIME_ROOT/uv-cache" \
        "$PYTHON_COMMAND" venv --clear --python 3.12 "$APP_ROOT/.venv" >/dev/null
    UV_CACHE_DIR="$RUNTIME_ROOT/uv-cache" \
        "$PYTHON_COMMAND" pip install --quiet --python "$APP_ROOT/.venv/bin/python" -e "$APP_ROOT"
else
    "$PYTHON_COMMAND" -m venv --clear "$APP_ROOT/.venv"
    "$APP_ROOT/.venv/bin/python" -m pip install --quiet --upgrade pip
    "$APP_ROOT/.venv/bin/python" -m pip install --quiet -e "$APP_ROOT"
fi
PATH="$(dirname "$NODE_COMMAND"):$PATH" "$NPM_COMMAND" --prefix "$APP_ROOT/ui" ci --omit=dev --silent

if [ ! -L "$COMMAND_PATH" ]; then
    ln -s "$APP_ROOT/bin/jnbot" "$COMMAND_PATH"
fi

echo "Installed. Run: jnbot"

if [ "${JNBOT_NO_LAUNCH:-0}" != "1" ]; then
    trap - EXIT
    exec "$COMMAND_PATH"
fi

trap - EXIT
