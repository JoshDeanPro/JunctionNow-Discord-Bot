# Configuration

Open **Setup** in `jnbot` to save the required private settings:

    DISCORD_TOKEN
    DISCORD_APPLICATION_ID

The token is hidden while it is entered and is never shown again. `jnbot` is
the only supported place to change private runtime settings.

Feed:

    JUNCTIONNOW_FEED_URL=https://junctionnow.com/feed/

Default poll interval:

    SYNC_INTERVAL_SECONDS=300

The bot checks the feed on this schedule. It only creates or edits Discord
messages when stored state shows that work is needed. discord.py handles Discord
rate limits automatically.

## Discord

/config allows a member with Manage Server permission to:

- select an existing channel
- create a JunctionNow channel
- optionally choose roles to mention
- clear mentions
- enable or disable delivery

/status shows the saved configuration.

Article content itself is never permitted to create Discord mentions.

Edits to existing messages do not re-ping roles.
