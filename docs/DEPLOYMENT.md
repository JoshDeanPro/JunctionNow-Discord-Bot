# Deployment

Production is one Python 3.12 daemon managed by systemd.

No Docker is used.

## Linux Setup

Create the virtual environment:

    python3.12 -m venv .venv

Install:

    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/pip install .

Configure:

    .env

Install daemon:

    sudo ./scripts/install_daemon.sh

## Management

Status:

    systemctl status junctionnow-discord

Logs:

    journalctl -u junctionnow-discord -f

Restart:

    sudo systemctl restart junctionnow-discord

Stop:

    sudo systemctl stop junctionnow-discord

Start:

    sudo systemctl start junctionnow-discord

## Local Console

Install Node dependencies and the `jnbot` command:

    npm --prefix ui ci
    ./scripts/install_cli.sh

The Updates screen checks `origin/main`. It only installs a clean fast-forward
after confirmation. It runs the project checks and rolls back the code if a
check fails. Private `.env` settings and runtime data are not tracked by Git and
remain in place.
