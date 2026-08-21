from types import SimpleNamespace

import pytest

from app import updates


def test_update_status_accepts_only_fast_forward(monkeypatch):
    values = {
        ("git", "branch", "--show-current"): "main",
        ("git", "remote", "get-url", "origin"): updates.EXPECTED_ORIGIN,
        ("git", "rev-parse", "HEAD"): "a" * 40,
        ("git", "rev-parse", "origin/main"): "b" * 40,
    }

    monkeypatch.setattr(
        updates,
        "run",
        lambda *args, **kwargs: values.get(args, ""),
    )
    monkeypatch.setattr(updates, "installed_version", lambda: "1.0.0")
    monkeypatch.setattr(
        updates.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )

    status = updates.update_status()

    assert status["update_available"] is True
    assert status["fast_forward"] is True


def test_update_rejects_dirty_tracked_files(monkeypatch):
    monkeypatch.setattr(
        updates,
        "update_status",
        lambda **kwargs: {
            "update_available": True,
            "fast_forward": True,
        },
    )
    monkeypatch.setattr(updates, "run", lambda *args, **kwargs: " M app/main.py")

    with pytest.raises(RuntimeError, match="local changes"):
        updates.install_update()


def test_update_rejects_non_github_origin(monkeypatch):
    def fake_run(*args, **kwargs):
        if args == ("git", "branch", "--show-current"):
            return "main"
        return "https://github.com.example.invalid/org/project.git"

    monkeypatch.setattr(updates, "run", fake_run)

    with pytest.raises(RuntimeError, match="not the JunctionNow repository"):
        updates.verify_repository()


def test_update_rejects_different_github_repository(monkeypatch):
    def fake_run(*args, **kwargs):
        if args == ("git", "branch", "--show-current"):
            return "main"
        return "https://github.com/example/different.git"

    monkeypatch.setattr(updates, "run", fake_run)

    with pytest.raises(RuntimeError, match="not the JunctionNow repository"):
        updates.verify_repository()


def test_failed_update_restores_code_and_runtime_dependencies(monkeypatch):
    monkeypatch.setattr(
        updates,
        "update_status",
        lambda **kwargs: {
            "update_available": True,
            "fast_forward": True,
        },
    )
    run_calls = []

    def fake_run(*args, **kwargs):
        run_calls.append(args)

        if args == ("git", "status", "--porcelain", "--untracked-files=no"):
            return ""
        if args == ("git", "rev-parse", "HEAD"):
            return "a" * 40
        if args[:3] == (str(updates.ROOT / ".venv/bin/python"), "-m", "pip"):
            raise RuntimeError("install failed")
        return ""

    subprocess_calls = []

    def fake_subprocess(command, **kwargs):
        subprocess_calls.append(tuple(command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(updates, "run", fake_run)
    monkeypatch.setattr(updates.subprocess, "run", fake_subprocess)

    with pytest.raises(RuntimeError, match="was rolled back"):
        updates.install_update()

    assert ("git", "reset", "--hard", "a" * 40) in subprocess_calls
    assert any(call[-3:] == ("install", "-e", ".") for call in subprocess_calls)
    assert ("npm", "--prefix", "ui", "ci", "--omit=dev") in subprocess_calls
