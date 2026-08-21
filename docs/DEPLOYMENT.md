# Deployment

Production is one Python 3.12 daemon managed by systemd.

No Docker is used.

## Linux Setup

Create the virtual environment:

    python3.12 -m venv .venv

Install:

    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/pip install .

Install and open the local console, then use **Setup** for the Discord token and
Application ID:

    npm --prefix ui ci
    ./scripts/install_cli.sh
    jnbot

Install the system service after private setup is complete:

    sudo ./scripts/install_daemon.sh

## Service Checks

Status:

    systemctl status junctionnow-discord

Logs:

    journalctl -u junctionnow-discord -f

Use the **Bot** area in `jnbot` to start, stop, pause, or resume delivery.

## Local Console

The Updates screen checks `origin/main`. It only installs a clean fast-forward
after confirmation. It runs the project checks and rolls back the code if a
check fails. Private `.env` settings and runtime data are not tracked by Git and
remain in place.
