"""Unit tests for database configuration."""

import pytest

from configs.database import get_database_url


def test_database_url(monkeypatch):
    monkeypatch.setenv(
        "POSTGRES_PASSWORD",
        "test_password",
    )

    monkeypatch.setenv(
        "POSTGRES_USER",
        "test_user",
    )

    monkeypatch.setenv(
        "POSTGRES_DB",
        "test_database",
    )

    monkeypatch.setenv(
        "POSTGRES_HOST",
        "localhost",
    )

    monkeypatch.setenv(
        "POSTGRES_PORT",
        "5433",
    )

    url = get_database_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "test_user"
    assert url.database == "test_database"
    assert url.port == 5433


def test_missing_password(monkeypatch):
    monkeypatch.delenv(
        "POSTGRES_PASSWORD",
        raising=False,
    )

    with pytest.raises(RuntimeError):
        get_database_url()


def test_special_characters_in_password(monkeypatch):
    password = "test@password:#123"

    monkeypatch.setenv(
        "POSTGRES_PASSWORD",
        password,
    )

    url = get_database_url()

    assert url.password == password
