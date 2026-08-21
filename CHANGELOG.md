# Changelog

## Unreleased

### Reliability

- Changed automatic post checks to every 30 minutes.
- Added one Posts action to check all new and changed articles now.
- Replaced raw event timestamps with friendly local dates in `jnbot`.
- Made menu movement wrap and limited root-menu exit to Esc or Ctrl-C.
- Consolidated the project guides into the README.
- Added complete channel or webhook photo destinations in `jnbot`.
- Moved article photo requests under **Posts → Add-ons**.
- Organized the CLI as Bot Settings, Features, Activity, and Bot Manager.
- Added safe invite-link copy, minimum permissions, self-install, and uninstall.
- Replaced Discord `/config` and `/status` with friendly `/setup` and `/edit`.
- Renamed Dashboard to Overview and added Space/Enter article multi-selects.
- Added Settings scheduling with automatic local timezone detection.
- Promoted Servers, Bot, Storage, and Settings to the main manager menu.
- Made setup role mentions multi-role and first-delivery-only.
- Added tracked broadcast withdrawal.
- Hid standalone Photos and gated Request Photos on its internal destination.
- Renamed Bot to Manage Bot and grouped internal credentials under Configuration.
- Added Storage feature usage, backend status, and preferences views without adding database drivers.
- Added safe local cleanup and private JSON snapshot actions under Storage Maintenance.
- Moved bot enable/disable state into Manage Bot as one state-aware control.
- Moved scheduling and bounded data retention into Feature Settings.
- Added explicit Broadcast delivery timing: now or with the next post batch.
- Moved private Discord setup into `jnbot` and removed separate token scripts.
- Updated rendered posts when article-page metadata changes.
- Kept photo requests and withdrawals intact when feed content changes.
- Stopped banned servers from receiving deliveries after reconnects.
- Saved the required article and Discord context for photo submissions.
- Added confirmed, fast-forward-only updates to the local console.
- Added Node 22 console checks to CI.

### Operator Console

- Added the local `jnbot` operator console.
- Added feed pause and resume controls.
- Added manual feed sync.
- Added server status view.
- Kept operator controls separate from public Discord commands.
- Kept private settings out of GitHub.

### Runtime

- Kept the bot as one Python daemon.
- Removed unused web and database layers.
- Kept JSON as the only bot state store.

### Repository Safety

- Improved secret checks.
- Protected local state and credentials.
- Kept product docs free of personal machine paths.
