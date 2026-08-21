# JSON State

The bot's only persistent application state is:

    data/state.json

The JSON state contains:

- guild configuration
- channel IDs
- selected role IDs
- article fingerprints
- Discord message IDs
- bounded counters/events

Writes use temporary files, fsync, and atomic replacement.

The format is schema-versioned so it can be migrated later.
