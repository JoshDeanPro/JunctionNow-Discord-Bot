from pathlib import Path


def test_no_docker():
    assert not Path("Dockerfile").exists()
    assert not Path("docker-compose.yml").exists()


def test_no_api_layer():
    assert not Path("app/api").exists()


def test_no_database_layer():
    assert not Path("app/db").exists()


def test_dependencies_are_lightweight():
    text = Path("pyproject.toml").read_text(encoding="utf-8").lower()

    banned = (
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "asyncpg",
        "postgres",
        "redis",
    )

    for dependency in banned:
        assert dependency not in text
