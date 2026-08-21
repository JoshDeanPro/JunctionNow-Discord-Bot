#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_TRACKED = {
    ".env",
    ".env.local",
    "credentials.json",
    "data/state.json",
    "private/storage.json",
}

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
}

ENV_STYLE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "environment",
    "environment.conf",
}

ENV_STYLE_SUFFIXES = {
    ".env",
    ".ini",
    ".conf",
    ".properties",
}

PATTERNS = (
    (
        "Discord webhook",
        re.compile(
            r"https://(?:canary\.|ptb\.)?"
            r"discord(?:app)?\.com/api/webhooks/"
            r"\d+/[A-Za-z0-9._-]{20,}"
        ),
    ),
    (
        "Discord token",
        re.compile(
            r"\b[A-Za-z0-9_-]{20,}"
            r"\.[A-Za-z0-9_-]{6,}"
            r"\.[A-Za-z0-9_-]{20,}\b"
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
        "AWS access key",
        re.compile(
            r"\bAKIA[0-9A-Z]{16}\b"
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
        "personal macOS home path",
        re.compile(
            r"/Users/(?!name(?:/|$)|user(?:/|$)|<)"
            r"[A-Za-z0-9._-]+/"
        ),
    ),
    (
        "personal Linux home path",
        re.compile(
            r"/home/(?!name(?:/|$)|user(?:/|$)|<)"
            r"[A-Za-z0-9._-]+/"
        ),
    ),
)

ENV_SECRET_ASSIGNMENT = re.compile(
    r"(?im)^[ \t]*"
    r"(?:DISCORD_TOKEN|PASSWORD|API_KEY|SECRET)"
    r"[ \t]*=[ \t]*"
    r"([^#\r\n]*)$"
)

PLACEHOLDERS = {
    "",
    "__TOKEN__",
    "<TOKEN>",
    "<SECRET>",
    "<PASSWORD>",
    "REPLACE_ME",
    "REPLACE-ME",
    "CHANGEME",
    "PLACEHOLDER",
}


def tracked_files() -> list[str]:
    return subprocess.check_output(
        ["git", "ls-files"],
        text=True,
    ).splitlines()


def is_env_style(path: Path) -> bool:
    if path.name in ENV_STYLE_NAMES:
        return True

    if path.suffix.lower() in ENV_STYLE_SUFFIXES:
        return True

    if path.name.startswith(".env."):
        return True

    return False


def main() -> int:
    files = set(tracked_files())
    problems: list[str] = []

    for name in sorted(
        files & FORBIDDEN_TRACKED
    ):
        problems.append(
            f"{name}: private runtime file is tracked"
        )

    for name in sorted(files):
        path = Path(name)

        if not path.is_file():
            continue

        if path.suffix.lower() in SKIP_SUFFIXES:
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

        if is_env_style(path):
            for match in ENV_SECRET_ASSIGNMENT.finditer(
                text
            ):
                value = (
                    match.group(1)
                    .strip()
                    .strip("\"'")
                )

                if value.upper() not in PLACEHOLDERS:
                    problems.append(
                        f"{name}: possible secret assignment"
                    )

    if problems:
        print("Repository safety check FAILED.")
        print()

        for problem in sorted(set(problems)):
            print(f"- {problem}")

        print()
        print(
            "Remove or replace the flagged value before pushing."
        )

        return 1

    print("Repository safety check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
