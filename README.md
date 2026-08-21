# JunctionNow Discord Bot

Official JunctionNow Discord bot.

## Architecture

JunctionNow content source:

    https://junctionnow.com/feed/

The source is RSS.

All bot state is JSON.

No SQL database is required.

Persistent state:

    data/state.json

The JSON state contains:

- server configuration
- selected posting channels
- selected mention roles
- source post fingerprints
- Discord message IDs
- delivery state
- synchronization analytics
- command usage analytics
- bounded event history

Writes are atomic.

Hourly bounded JSON backups are stored under:

    data/backups/

## Commands

Only two slash commands are registered:

    /config
    /status

/config is the primary interface.

It uses Discord Components V2 and provides:

- Discord-native channel picker
- Make Channel button
- Discord-native role picker
- No Mentions button
- Enable/Disable button

/status shows the current configuration and tracked delivery count.

Both commands are:

- server-install only
- server-context only
- Manage Server by default
- ephemeral

## Updates

The bot does not use a simple seen-items list.

Each JunctionNow source post stores:

- canonical post ID
- canonical URL
- RSS fingerprint
- article-page fingerprint
- image
- publication time
- source fingerprint

Each Discord delivery stores:

- server ID
- channel ID
- Discord message ID
- source fingerprint
- delivery state

When a source fingerprint changes, the bot edits the existing Discord message.

Updated posts display:

    JunctionNow • Updated

The word Breaking is not used.

If Discord reports that a delivered message was deleted while the bot is online, the JSON delivery state is marked missing and the message is recreated on reconciliation.

## Mentions

Article content can never create Discord mentions.

Only roles explicitly selected by a server administrator can be mentioned.

Mention roles are used on new posts.

Edits do not re-ping roles.

## Permissions

Normal operation needs:

- View Channels
- Send Messages
- Embed Links
- Read Message History

Make Channel additionally needs:

- Manage Channels

Administrator permission is not required.

## Development

Python 3.12 is used for this project.

Activate:

    source .venv/bin/activate

Install:

    pip install -e ".[dev]"

Run:

    ./run.sh

State status:

    python scripts/state_status.py
