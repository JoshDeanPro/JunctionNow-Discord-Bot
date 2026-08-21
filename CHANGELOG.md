# Changelog

## Unreleased

### Reliability

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
