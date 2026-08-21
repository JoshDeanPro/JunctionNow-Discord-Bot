# Local Management

The `jnbot` console runs on the bot host. It is the operator Dashboard.

It can:

- save the private Discord token and Application ID
- start or stop the bot
- pause or resume the feed
- view and manage installed servers
- turn photo requests on or off for an article
- withdraw or restore posts
- send a confirmed Broadcast without mentions
- check and install safe updates from GitHub main

The console uses a small command bridge to the Python code. It does not use an
HTTP server. The token is sent only to that local bridge when the owner saves
it, and it is never returned to the screen.

Photo delivery may use an optional private Discord server and channel. If it is
configured, the bot creates or reuses:

- `jn-photo-submissions`

Without that destination, photo submission is unavailable. The destination can
be changed later in private configuration.
