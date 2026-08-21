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

## Persistent Updates

Every sent JunctionNow post stores its Discord message ID.

When the source fingerprint changes, the bot edits that same message.

## Expansion

Future functionality should be added as Python modules without introducing new
infrastructure unless scale or product requirements actually require it.
