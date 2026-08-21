# JunctionNow Discord Bot

A small Python bot that sends JunctionNow posts to Discord and keeps them up to date.

## What It Does

- reads the JunctionNow feed
- sends new posts to Discord
- updates old Discord messages when a post changes
- stores state in JSON
- lets server managers choose a channel
- supports optional role mentions
- has a local operator console named `jnbot`

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

## Operator Console

`jnbot` runs locally and never needs the Discord token. It reads the shared JSON
state through a small Python command bridge.

It can manage:

- servers and posting channels
- posts and photo requests
- broadcasts
- bot delivery state
- safe updates from GitHub main

Private settings stay in `.env` and are not stored in Git.

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

Install the local console:

    npm --prefix ui ci
    ./scripts/install_cli.sh

## Production

The bot runs as one Python daemon under systemd.

It does not need Docker, a database server, FastAPI, Redis, or a web server.

See `docs/DEPLOYMENT.md`.
