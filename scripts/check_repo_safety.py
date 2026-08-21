#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN = {
    ".env",
    ".env.local",
    "credentials.json",
    "data/state.json",
}

SKIP = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
}

PATTERNS = (
    (
        "Discord webhook",
        re.compile(
            r"https://(?:canary\.|ptb\.)?"
            r"discord(?:app)?\.com/api/webhooks/"
            r"\d+/[A-Za-z0-9._-]+"
        ),
    ),
    (
        "GitHub token",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|"
            r"github_pat_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    (
        "private key",
        re.compile(
            r"-----BEGIN "
            r"(?:RSA |EC |OPENSSH )?"
            r"PRIVATE KEY-----"
        ),
    ),
    (
        "personal macOS path",
        re.compile(
            r"/Users/[A-Za-z0-9._-]+/"
        ),
    ),
)

ENV_SECRET = re.compile(
    r"^\s*(?:DISCORD_TOKEN|PASSWORD|API_KEY|SECRET)"
    r"\s*=\s*(\S+)\s*$",
    re.MULTILINE,
)


def tracked() -> list[str]:
    return subprocess.check_output(
        ["git", "ls-files"],
        text=True,
    ).splitlines()


def main() -> int:
    files = set(tracked())
    problems = []

    for name in sorted(files & FORBIDDEN):
        problems.append(
            f"{name}: private file is tracked"
        )

    for name in sorted(files):
        path = Path(name)

        if not path.is_file():
            continue

        if path.suffix.lower() in SKIP:
            continue

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        for label, pattern in PATTERNS:
            if pattern.search(text):
                problems.append(
                    f"{name}: possible {label}"
                )

        for match in ENV_SECRET.finditer(text):
            value = match.group(1).strip("\"'")

            if value:
                problems.append(
                    f"{name}: possible secret value"
                )

    if problems:
        print("Repository safety check FAILED.")
        print()

        for problem in sorted(set(problems)):
            print(f"- {problem}")

        return 1

    print("Repository safety check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
