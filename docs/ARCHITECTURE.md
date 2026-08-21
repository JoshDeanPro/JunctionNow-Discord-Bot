# Architecture

## One Purpose

Fetch JunctionNow posts and keep their Discord copies synchronized.

## Runtime

One Python process:

    JunctionNow /feed/
           |
           v
      feed poller
           |
           v
    article fingerprint
           |
           v
      JSON state
           |
       +---+---+
       |       |
      new    changed
       |       |
      send    edit
       |       |
       +---+---+
           |
           v
       Discord

Discord's Gateway connection is maintained by discord.py.

There is no application HTTP listener.

## Local Control

`jnbot` is an Ink and React terminal app. Each action starts a short Python
command. The command reads state or adds an operator action to the JSON file.
The daemon executes queued Discord actions. The UI does not receive the bot
token, and no local server is required.

## Persistent Updates

Every sent JunctionNow post stores its Discord message ID.

When the source fingerprint changes, the bot edits that same message.
Unchanged posts do not cause Discord message lookups. Deleted messages reported
by Discord are marked missing and recreated on the next applicable sync.

## Expansion

Future functionality should be added as Python modules without introducing new
infrastructure unless scale or product requirements actually require it.
