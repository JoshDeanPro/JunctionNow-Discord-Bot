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

Install the local console:

    npm --prefix ui ci
    ./scripts/install_cli.sh

Run `jnbot`, open **Setup**, and save the Discord token and Application ID.
Then open **Bot** and start the daemon.

## Production

The bot runs as one Python daemon.

It does not need Docker, a database server, FastAPI, Redis, or a web server.

See `docs/DEPLOYMENT.md`.
