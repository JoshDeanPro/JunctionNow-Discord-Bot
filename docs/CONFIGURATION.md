# Configuration

Required:

    DISCORD_TOKEN
    DISCORD_APPLICATION_ID

Feed:

    JUNCTIONNOW_FEED_URL=https://junctionnow.com/feed/

Default poll interval:

    SYNC_INTERVAL_SECONDS=300

## Discord

/config allows an administrator to:

- select an existing channel
- create a JunctionNow channel
- optionally choose roles to mention
- clear mentions
- enable or disable delivery

/status shows the saved configuration.

Article content itself is never permitted to create Discord mentions.

Edits to existing messages do not re-ping roles.
