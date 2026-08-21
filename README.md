# JunctionNow Discord Bot

A lightweight Python Discord bot with one purpose:

Keep JunctionNow posts synchronized into configured Discord servers.

## Runtime

One Python daemon.

It contains only:

- Discord Gateway connection
- JunctionNow feed polling
- article update detection
- Discord message delivery/editing
- JSON state
- /config
- /status

It does not use Docker, PostgreSQL, SQLite, Redis, FastAPI, an application
HTTP server, worker queues, or AI.

## Source

    https://junctionnow.com/feed/

## Storage

    data/state.json

JSON stores server configuration, article fingerprints, Discord message IDs,
and small bounded operational state.

## Commands

    /config
    /status

/config includes the native Discord channel picker, Make Channel, native role
picker, No Mentions, and Enable/Disable.

## Local Run

    ./run.sh

## Production

Run directly under systemd:

    sudo ./scripts/install_daemon.sh

See docs/DEPLOYMENT.md.

## Optional n8n Reference

See:

    n8n/

n8n is not required by the Python daemon.
