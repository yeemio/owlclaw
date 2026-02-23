"""Unit tests for owlclaw.db exception classes."""

from owlclaw.db.exceptions import (
    AuthenticationError,
    DatabaseConnectionError,
    DatabaseError,
    PoolTimeoutError,
)


def test_database_connection_error_includes_host_port_and_message() -> None:
    err = DatabaseConnectionError(host="localhost", port=5432, message="connection refused")
    text = str(err)
    assert isinstance(err, DatabaseError)
    assert "localhost:5432" in text
    assert "connection refused" in text


def test_authentication_error_message_hides_password() -> None:
    err = AuthenticationError(user="owlclaw", database="owlclaw_db")
    text = str(err)
    assert isinstance(err, DatabaseError)
    assert "owlclaw" in text
    assert "owlclaw_db" in text
    assert "password" not in text.lower()
    assert "secret" not in text.lower()


def test_pool_timeout_error_contains_pool_settings() -> None:
    err = PoolTimeoutError(pool_size=20, max_overflow=10, timeout=30.0)
    text = str(err)
    assert isinstance(err, DatabaseError)
    assert "30.0s" in text
    assert "pool_size=20" in text
    assert "max_overflow=10" in text
