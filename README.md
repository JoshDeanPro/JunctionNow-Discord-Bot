# JunctionNow Discord Bot

JunctionNow sends official feed posts to configured Discord servers and keeps
each Discord message up to date.

## How It Works

Every 30 minutes, one feed check finds both new and changed articles. New posts
are delivered once. Changed articles edit the existing Discord message by its
saved message ID. Unchanged posts do not cause Discord message lookups.

The bot recreates a delivery when Discord reports that its message was deleted,
unless the post was deliberately withdrawn. discord.py handles Discord rate
limits. Article text cannot create mentions, and edits do not ping roles again.

Server managers use only:

    /config
    /status

Both commands require **Manage Server** permission. `/config` selects or creates
a posting channel, chooses optional mention roles, and enables delivery.

## jnbot

`jnbot` is the local operator console and the supported place to manage the bot.
Its menus contain:

- **Dashboard** for counts and delivery state
- **Setup** for the private token, Application ID, and photo destination
- **Servers** for installed servers, channels, bans, and retained data
- **Posts** for immediate updates, automatic updates, article actions, and photos
- **Photos** and **Activity** for recent local records
- **Broadcast** for confirmed, mention-safe messages
- **Updates** for approved fast-forward updates from GitHub main
- **Bot** for daemon start and stop

Esc is the only menu key that exits the console. Ctrl-C also works. Menu movement
wraps at the top and bottom.

Private values are saved atomically in the gitignored `.env` file with private
file permissions. Tokens are masked during entry and are never shown again.
Runtime state stays in `data/state.json`, with process locking, atomic writes,
bounded backups, and bounded activity history.

Photo requests belong to individual posts. When enabled, delivered messages get
a **Submit Photos** button. Users confirm ownership before uploading. Submissions
go only to the optional private photo destination.

## Install

Requirements are Python 3.12 and Node 22.

    python3.12 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
    npm --prefix ui ci
    ./scripts/install_cli.sh
    jnbot

Open **Setup**, save the Discord token and Application ID, then use **Bot** to
start the daemon. Linux hosts may install the boot service after setup:

    sudo ./scripts/install_daemon.sh

The bot needs no Docker, database server, HTTP API, Redis, or external telemetry.

## Validate

    .venv/bin/python scripts/check_repo_safety.py
    .venv/bin/ruff check app tests scripts
    .venv/bin/pytest -q
    npm --prefix ui run check

This repository is private, but secrets, local state, private IDs, and personal
paths must still never be committed. See `SECURITY.md` and `CONTRIBUTING.md`.
