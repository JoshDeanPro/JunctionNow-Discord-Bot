# Writing Style

Project writing should be simple and clear.

## Reading Level

Aim for a 6th to 8th grade reading level.

A new reader should not need expert knowledge to understand the basic docs.

## Use Plain English

Prefer:

    The bot checks the feed every five minutes.

Instead of:

    The service performs periodic source reconciliation at five-minute intervals.

Prefer:

    Pick the Discord channel where posts should go.

Instead of:

    Select the destination channel used for message publication.

## Keep Sentences Short

Try to explain one idea at a time.

Break long sections into smaller sections.

## Explain Technical Terms

Technical words are fine when they are needed.

Explain them the first time they appear.

Example:

> A fingerprint is a short value made from the post content. The bot uses it to tell when a post changed.

## Paths

Never place a person's home folder in project docs.

Do not write:

    /Users/name/project
    /home/name/project

Use:

    <project-root>

or a path relative to the project:

    ./data/state.json

## Examples

Examples must never contain real:

- tokens
- passwords
- webhook URLs
- email addresses
- private server names
