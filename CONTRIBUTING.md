# Contributing

Keep this project simple.

The bot has one main job:

> Send JunctionNow posts to Discord and keep those posts up to date.

## Before You Change Code

Make sure the change helps that job.

Do not add a new service just because it may be useful later.

If the project needs something later, we can add it later.

## Keep Private Data Out

Never commit:

- Discord tokens
- webhook secrets
- passwords
- private keys
- `.env`
- real server addresses
- personal file paths
- local state files

Use `.env.example` for setting names.

Leave secret values blank.

## Commit Messages

Use short and clear commit messages.

Good:

    Add role picker to config
    Fix article update detection
    Improve JSON state safety
    Remove unused API code
    Update setup guide

Avoid:

    stuff
    changes
    fix things
    final
    more updates
    work

A commit message should explain what changed.

## Change Notes

For a larger change, explain three things:

1. What changed
2. Why it changed
3. How it was tested

Keep the wording simple.

## Code Style

Prefer:

- small functions
- clear names
- plain Python
- few dependencies
- one clear job per module

Avoid clever code when simple code works.

## Documentation

Write for a reader who is new to the project.

Use:

- short sentences
- common words
- short sections
- examples when useful

Aim for a 6th to 8th grade reading level.

Do not use machine-specific paths in documentation.

Use paths like:

    ./data/state.json
    ./scripts/install_daemon.sh
    <project-root>

## Before Pushing

Run:

    python scripts/check_repo_safety.py
    ruff check app tests scripts
    pytest -q

Then review:

    git status
    git diff --cached
