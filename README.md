# JunctionNow Discord Bot

Official Python Discord bot for JunctionNow.

The bot publishes JunctionNow posts into administrator-selected Discord
channels and keeps previously delivered Discord messages synchronized when
JunctionNow content changes.

## Core design

JunctionNow owns the canonical source content.

The database owns delivery state.

Every delivery maps:

- JunctionNow post ID
- Discord server
- Discord channel
- Discord message ID
- source revision
- rendered content hash

This allows the bot to edit an existing Discord message when JunctionNow
content changes rather than blindly posting a duplicate.

## Commands

- /junction setup
- /junction status
- /junction enable
- /junction disable
- /junction test
- /junction sync
- /junction help

Configuration commands require Manage Server permission.

## Development setup

Requirements:

- Python 3.12 or newer
- Git
- Discord bot application credentials

Run:

    ./scripts/bootstrap_mac.sh

Then configure:

    .env

At minimum:

    DISCORD_TOKEN=
    DISCORD_APPLICATION_ID=
    JUNCTIONNOW_FEED_URL=

For fast slash-command development, also configure:

    DISCORD_DEV_GUILD_ID=

Start the bot:

    ./run.sh

## Local database

Development defaults to SQLite:

    sqlite+aiosqlite:///./data/junctionnow.db

Production supports PostgreSQL:

    postgresql+asyncpg://user:password@hostname/database

## JunctionNow sources

SOURCE_MODE supports:

- auto
- json
- rss

The long-term preferred source is a JunctionNow-owned versioned JSON feed
with stable post IDs and explicit revisions.

## Internal API

Local health endpoints:

    GET /health
    GET /ready

When INTERNAL_API_SECRET is configured:

    POST /internal/sync
    GET /internal/status

Supply the secret using the X-JunctionNow-Secret request header.

The HTTP API binds to 127.0.0.1 by default.

## Security

- Secrets are excluded from Git.
- Discord Message Content intent is not required.
- Source content cannot generate @everyone, @here, role, or user pings.
- The internal API is loopback-only by default.
- Production database credentials belong in environment configuration.

## Current production integration

The old JunctionNow droplet implementation remains untouched.

Its jn_news implementation should be inspected read-only before final source
and presentation behavior are wired into this project.
