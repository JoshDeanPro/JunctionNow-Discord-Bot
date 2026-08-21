# Local Management

The `jnbot` console runs on the bot host. It is the operator Dashboard.

It can:

- pause or resume the feed
- view and manage installed servers
- turn photo requests on or off for an article
- withdraw or restore posts
- send a confirmed Broadcast without mentions
- check and install safe updates from GitHub main

The console uses a small command bridge to the Python code. It does not use an
HTTP server and does not need the Discord token.

Photo delivery may use an optional private Discord server and channel. If it is
configured, the bot creates or reuses:

- `jn-photo-submissions`

Without that destination, photo submission is unavailable. The destination can
be changed later in private configuration.
