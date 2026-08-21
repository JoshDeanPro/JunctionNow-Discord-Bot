from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ORIGIN = "https://github.com/JoshDeanPro/JunctionNow-Discord-Bot.git"


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if check and result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed."
        raise RuntimeError(message)

    return result.stdout.strip()


def installed_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def verify_repository() -> None:
    if run("git", "branch", "--show-current") != "main":
        raise RuntimeError("Updates can only be installed from the main branch.")

    origin = run("git", "remote", "get-url", "origin")

    normalized = re.sub(r"^git@github\.com:", "https://github.com/", origin)

    if normalized.removesuffix(".git") != EXPECTED_ORIGIN.removesuffix(".git"):
        raise RuntimeError("The origin remote is not the JunctionNow repository.")


def update_status(*, fetch: bool = False) -> dict:
    verify_repository()

    if fetch:
        run("git", "fetch", "--quiet", "origin", "main")

    installed = run("git", "rev-parse", "HEAD")
    available = run("git", "rev-parse", "origin/main")
    safe = subprocess.run(
        ["git", "merge-base", "--is-ancestor", installed, available],
        cwd=ROOT,
        check=False,
    ).returncode == 0

    return {
        "version": installed_version(),
        "installed_revision": installed[:12],
        "available_revision": available[:12],
        "update_available": installed != available,
        "fast_forward": safe,
    }


def install_update() -> dict:
    status = update_status(fetch=True)

    if not status["update_available"]:
        return status

    if not status["fast_forward"]:
        raise RuntimeError("GitHub main is not a safe fast-forward update.")

    if run("git", "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Tracked files have local changes. Update was not installed.")

    previous = run("git", "rev-parse", "HEAD")
    run("git", "merge", "--ff-only", "origin/main")

    checks = (
        (str(ROOT / ".venv/bin/python"), "-m", "pip", "install", "-e", "."),
        ("npm", "--prefix", "ui", "ci", "--omit=dev"),
        (str(ROOT / ".venv/bin/python"), "scripts/check_repo_safety.py"),
        (str(ROOT / ".venv/bin/python"), "-m", "compileall", "-q", "app", "scripts"),
        ("npm", "--prefix", "ui", "run", "check"),
    )

    try:
        for command in checks:
            run(*command)
    except Exception as exc:
        rollback = subprocess.run(
            ["git", "reset", "--hard", previous],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        dependencies_restored = rollback.returncode == 0

        if dependencies_restored:
            for command in (
                (str(ROOT / ".venv/bin/python"), "-m", "pip", "install", "-e", "."),
                ("npm", "--prefix", "ui", "ci", "--omit=dev"),
            ):
                if subprocess.run(
                    command,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode:
                    dependencies_restored = False
                    break

        if not dependencies_restored:
            raise RuntimeError(f"Update failed and rollback failed: {exc}") from exc

        raise RuntimeError(f"Update failed and was rolled back: {exc}") from exc

    return update_status()
