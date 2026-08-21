# JunctionNow Discord Bot

A small Python bot that sends JunctionNow posts to Discord and keeps them up to date.

## What It Does

- reads the JunctionNow feed
- sends new posts to Discord
- updates old Discord messages when a post changes
- stores state in JSON
- lets server managers choose a channel
- supports optional role mentions
- has a private operator panel

Feed:

    https://junctionnow.com/feed/

## Commands

The bot has two server commands:

    /config
    /status

Both require **Manage Server** permission.

`/config` lets a server manager:

- choose a channel
- make a channel
- choose mention roles
- turn mentions off
- enable or disable posting

## Private Management

The private management panel is only for approved JunctionNow operators.

It can:

- sync now
- pause or resume the feed
- refresh status
- view server status

Private Discord IDs stay in `.env` and are not stored in Git.

## Local Setup

Create the Python environment:

    python3.12 -m venv .venv
    .venv/bin/pip install -e ".[dev]"

Set the Discord token:

    ./scripts/set_token.sh

Set the Discord Application ID:

    ./scripts/set_app_id.sh

Run:

    ./run.sh

## Production

The bot runs as one Python daemon under systemd.

It does not need Docker, a database server, FastAPI, Redis, or a web server.

See `docs/DEPLOYMENT.md`.
