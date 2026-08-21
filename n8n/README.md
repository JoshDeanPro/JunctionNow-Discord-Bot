# JunctionNow Posts for n8n

This package mirrors the public post delivery part of the Discord bot. It reads
the official feed, avoids a first-run history flood, tracks Discord message IDs,
creates new messages, and edits changed posts.

It does not include the Bot Manager, slash commands, photo uploads, broadcasts,
or operator controls. Those require the Discord Gateway and belong in the Python
bot.

## Setup

Use n8n 2.4 or newer.

1. Import `01-initialize.json` and `02-posts.json`.
2. Create an n8n variable named `DISCORD_CHANNEL_ID` with the destination channel ID.
3. Create an HTTP Header Auth credential named `JunctionNow Discord Bot`.
4. Set the credential header name to `Authorization` and its value to `Bot TOKEN`,
   replacing `TOKEN` with the private Discord bot token.
5. Select that credential on all three Discord HTTP Request nodes in `02-posts`.
6. Run `01-initialize` once. It records current articles without posting them.
7. Test `02-posts`, then publish it.

The bot needs View Channel, Send Messages, Embed Links, and Read Message History in
the selected channel. n8n keeps credentials outside exported workflow JSON. Never
paste the token into a node, variable, workflow name, or execution data.

The schedule checks every 30 minutes. Run `02-posts` manually for Update Posts Now.
Both paths check for new and changed posts in the same run. Discord requests are
sent one at a time with a short delay.

The workflow sends no message content and sets `allowed_mentions.parse` to an empty
list, so feed text cannot create mentions. The `JunctionNow Posts` Data Table is
the delivery state. Do not clear it while delivered messages still exist.

Official n8n references:

- [Discord node](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.discord/)
- [Data Table node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.datatable/)
- [RSS Read node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.rssfeedread/)
- [Schedule Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/)

