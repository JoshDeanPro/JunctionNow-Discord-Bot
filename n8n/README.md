# JunctionNow n8n Reference

This folder is optional.

The Python bot does not depend on n8n.

The intended n8n workflow has one purpose:

    JunctionNow feed
        -> detect new/changed post
        -> send/edit Discord webhook message

It should use only built-in n8n nodes:

- Schedule Trigger
- RSS Read
- HTTP Request
- Code

No community nodes are required.

The Python daemon remains the primary implementation.
