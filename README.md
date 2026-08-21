# JunctionNow Discord Bot

JunctionNow sends official feed posts to configured Discord servers and keeps
each Discord message up to date.

## How It Works

Posts and Post Updates each default to 30 minutes and can be changed under
**Features → Posts → Settings**. They share one scheduler. Posts uses the
lightweight feed; Post Updates also checks article pages for edits. New posts are
delivered once. Changed articles edit the existing Discord message by its saved
message ID. Unchanged posts do not cause Discord message lookups.

Restarting the bot does not force every check. Saved timestamps let it run only
the work that is due. **Update All Now** is the explicit full check.

The bot recreates a delivery when Discord reports that its message was deleted,
unless the post was deliberately withdrawn. discord.py handles Discord rate
limits. Article text cannot create mentions, and edits do not ping roles again.

Server managers use only:

    /setup
    /edit

Both commands require **Manage Server** permission. `/setup` guides first-time
setup. After that, `/edit` changes the channel or mention roles and can stop or
resume posts. Optional roles are mentioned only on the first new post after
they are selected; several roles may be selected at once.

## jnbot

`jnbot` is the JunctionNow Discord Bot Manager and the supported place to manage
the bot. Running `./bin/jnbot` safely installs the command when it is missing.
Its menus contain:

- **Overview** for counts and delivery state
- **Servers** for installed-server controls and delivery state
- **Features** for Posts and tracked Broadcasts
- **Manage Bot** for enable/disable state, internal configuration, logs, and invites
- **Storage** for feature usage, destinations, maintenance, retention, and local archives
- **Settings** for updates and manager uninstall

Post scheduling lives under **Features → Posts → Settings**. Data retention has one
home under **Storage → Preferences**.

Server managers normally choose their posting channel through `/setup`. The Bot
Manager can also select a sendable channel from Discord's Gateway cache, with
manual channel ID entry available as a fallback.

Posts contains its own controls and Add-ons. Request Photos and its destination
live only under **Features → Posts → Add-ons**. Request Photos stays unavailable
until the private destination is configured. Broadcast messages retain their
Discord message IDs so an operator can withdraw them later.

Esc is the only menu key that exits the console. Ctrl-C also works. Menu movement
wraps at the top and bottom.

Menus keep each choice on one line. The arrow shows keyboard focus, while plain
text states such as Enabled, Paused, or Inactive appear to the right. Multi-select
screens use checkboxes with Space to select and Enter to submit.

Private values are saved atomically in the gitignored `.env` file with private
file permissions. Tokens are masked during entry and are never shown again.
Runtime state stays in `data/state.json`, with process locking, atomic writes,
bounded backups, and bounded activity history.

JSON is always active. Optional MySQL and PostgreSQL destinations can mirror
selected feature data. The manager verifies each connection before saving it.
Database credentials stay in `private/storage.json`, are readable only by the
local account, and are never returned to the UI after saving.

Photo requests belong to individual posts. When enabled, delivered messages get
a **Submit Photos** button. Users confirm ownership before uploading. Submissions
go only to the optional private photo destination. Configure either a Discord
server and channel ID together, or a private Discord webhook. Photo settings are
active as soon as they are saved. Token and Application ID changes are durable
immediately and take effect after the bot restarts.

## Install

Requirements are Python 3.12 and Node 22.

    python3.12 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
    npm --prefix ui ci
    ./scripts/install_cli.sh
    jnbot

Open **Manage Bot → Configuration**, save the Discord token and Application ID,
then enable the bot from **Manage Bot**. Linux hosts may install the boot service
after setup:

    sudo ./scripts/install_daemon.sh

The default setup needs no Docker, database server, HTTP API, Redis, or external telemetry.

## Validate

    .venv/bin/python scripts/check_repo_safety.py
    .venv/bin/ruff check app tests scripts
    .venv/bin/pytest -q
    npm --prefix ui run check

## Safety

Keep `.env`, tokens, webhook URLs, database passwords, private IDs, local state,
and personal paths out of Git. If a secret is exposed, revoke it before removing
it from history. Run the safety scanner before every push. Updates accept only a
clean, fast-forward change from this project's GitHub `main` branch.
