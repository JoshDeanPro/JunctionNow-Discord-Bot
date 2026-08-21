from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_FILE = ROOT / "private" / "storage.json"
FEATURES = {"servers", "posts", "deliveries", "photos", "broadcasts", "activity"}


def ensure_driver(kind: str) -> None:
    module = "asyncmy" if kind == "mysql" else "psycopg"

    try:
        __import__(module)
        return
    except ImportError:
        pass

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", f"{ROOT}[{kind}]"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode:
        raise RuntimeError(f"The {kind} storage driver could not be installed.")


def load_destinations() -> list[dict]:
    if not PRIVATE_FILE.exists():
        return []

    data = json.loads(PRIVATE_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def save_destinations(items: list[dict]) -> None:
    PRIVATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".storage-", dir=PRIVATE_FILE.parent)

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(items, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, PRIVATE_FILE)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def public_destinations() -> list[dict]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "kind": item["kind"],
            "features": item["features"],
            "status": item.get("status", "inactive"),
            "last_synced_at": item.get("last_synced_at"),
            "last_error": item.get("last_error"),
        }
        for item in load_destinations()
    ]


def feature_payloads(state: dict, features: list[str]) -> dict[str, object]:
    selected = set(features) & FEATURES
    payloads = {}

    if "servers" in selected:
        payloads["servers"] = state.get("guilds", {})
    if "posts" in selected:
        payloads["posts"] = state.get("posts", {})
    if "deliveries" in selected:
        payloads["deliveries"] = state.get("deliveries", {})
    if "broadcasts" in selected:
        payloads["broadcasts"] = state.get("broadcasts", {})
    if "activity" in selected:
        payloads["activity"] = state.get("analytics", {})
    if "photos" in selected:
        payloads["photos"] = {
            "requests": {
                key: value
                for key, value in state.get("posts", {}).items()
                if value.get("photo_requested")
            },
            "submissions": [
                item
                for item in state.get("analytics", {}).get("events", [])
                if item.get("type") == "photo_submission"
            ],
        }

    return payloads


async def write_destination(destination: dict, payloads: dict[str, object]) -> None:
    if destination["kind"] == "mysql":
        import asyncmy

        connection = await asyncmy.connect(
            host=destination["host"],
            port=int(destination["port"]),
            user=destination["username"],
            password=destination["password"],
            db=destination["database"],
            connect_timeout=5,
            ssl=ssl.create_default_context() if destination.get("tls", True) else None,
        )

        try:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS junctionnow_mirror ("
                    "feature VARCHAR(32) PRIMARY KEY, payload JSON NOT NULL, "
                    "updated_at VARCHAR(40) NOT NULL)"
                )
                stamp = datetime.now(UTC).isoformat()

                for feature, payload in payloads.items():
                    await cursor.execute(
                        "INSERT INTO junctionnow_mirror (feature, payload, updated_at) "
                        "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE "
                        "payload=VALUES(payload), updated_at=VALUES(updated_at)",
                        (feature, json.dumps(payload, ensure_ascii=False), stamp),
                    )

            await connection.commit()
        finally:
            connection.close()
        return

    if destination["kind"] == "postgresql":
        import psycopg

        connection = await psycopg.AsyncConnection.connect(
            host=destination["host"],
            port=int(destination["port"]),
            user=destination["username"],
            password=destination["password"],
            dbname=destination["database"],
            connect_timeout=5,
            sslmode="require" if destination.get("tls", True) else "disable",
        )

        async with connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS junctionnow_mirror ("
                    "feature TEXT PRIMARY KEY, payload JSONB NOT NULL, "
                    "updated_at TIMESTAMPTZ NOT NULL)"
                )
                stamp = datetime.now(UTC)

                for feature, payload in payloads.items():
                    await cursor.execute(
                        "INSERT INTO junctionnow_mirror (feature, payload, updated_at) "
                        "VALUES (%s, %s::jsonb, %s) ON CONFLICT (feature) DO UPDATE SET "
                        "payload=EXCLUDED.payload, updated_at=EXCLUDED.updated_at",
                        (feature, json.dumps(payload, ensure_ascii=False), stamp),
                    )
        return

    raise ValueError("Unsupported storage destination.")


async def add_destination(data: dict, state: dict) -> dict:
    kind = str(data.get("kind", ""))
    features = [str(value) for value in data.get("features", []) if str(value) in FEATURES]

    if kind not in {"mysql", "postgresql"} or not features:
        raise ValueError("Choose a database type and at least one feature.")

    ensure_driver(kind)

    destination = {
        "id": uuid.uuid4().hex[:12],
        "name": str(data.get("name", "")).strip(),
        "kind": kind,
        "host": str(data.get("host", "")).strip(),
        "port": int(data.get("port", 3306 if kind == "mysql" else 5432)),
        "database": str(data.get("database", "")).strip(),
        "username": str(data.get("username", "")).strip(),
        "password": str(data.get("password", "")),
        "tls": bool(data.get("tls", True)),
        "features": features,
        "status": "active",
    }

    if not all(destination[key] for key in ("name", "host", "database", "username", "password")):
        raise ValueError("Complete every database field.")

    await write_destination(destination, feature_payloads(state, features))
    destination["last_synced_at"] = datetime.now(UTC).isoformat()
    items = load_destinations()
    items.append(destination)
    save_destinations(items)
    return {"id": destination["id"], "name": destination["name"]}


async def sync_destination(destination_id: str, state: dict) -> dict:
    items = load_destinations()
    destination = next((item for item in items if item.get("id") == destination_id), None)

    if not destination:
        raise ValueError("Storage destination not found.")

    try:
        await write_destination(
            destination,
            feature_payloads(state, destination.get("features", [])),
        )
        destination["status"] = "active"
        destination["last_synced_at"] = datetime.now(UTC).isoformat()
        destination.pop("last_error", None)
    except Exception as exc:
        destination["status"] = "inactive"
        destination["last_error"] = type(exc).__name__
        save_destinations(items)
        raise

    save_destinations(items)
    return {"name": destination["name"], "last_synced_at": destination["last_synced_at"]}


def remove_destination(destination_id: str) -> None:
    items = load_destinations()
    kept = [item for item in items if item.get("id") != destination_id]

    if len(kept) == len(items):
        raise ValueError("Storage destination not found.")

    save_destinations(kept)
