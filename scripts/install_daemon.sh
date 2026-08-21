#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$(uname -s)" != "Linux" ]; then
    echo "This installer is for Linux systems that use systemd."
    exit 1
fi

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "Run this script with sudo."
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="/etc/systemd/system/junctionnow-discord.service"

if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    RUN_USER="$SUDO_USER"
else
    RUN_USER="$(stat -c '%U' "$ROOT")"
fi

if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "The Python environment is missing."
    exit 1
fi

if [ ! -f "$ROOT/.env" ]; then
    echo "The private .env file is missing."
    exit 1
fi

cat > "$SERVICE" <<EOF
[Unit]
Description=JunctionNow Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$ROOT
EnvironmentFile=$ROOT/.env
ExecStart=$ROOT/.venv/bin/python -m app.main
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable junctionnow-discord.service

echo "Service installed. Use jnbot to start the bot."
