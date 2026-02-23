"""Property tests for owlclaw.db session transaction behavior."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from owlclaw.db import session as db_session


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


@pytest.mark.asyncio
@given(raise_error=st.booleans())
async def test_property_session_transaction_management(raise_error: bool) -> None:
    """Property: success commits once, failure rolls back once."""
    fake = _FakeSession()

    def fake_factory(_: Any) -> Any:
        class _Factory:
            def __call__(self) -> _FakeSessionContext:
                return _FakeSessionContext(fake)

        return _Factory()

    original_factory = db_session.create_session_factory
    original_get_engine = db_session.get_engine
    db_session.create_session_factory = fake_factory  # type: ignore[assignment]
    db_session.get_engine = lambda: object()  # type: ignore[assignment]
    try:
        if raise_error:
            with pytest.raises(RuntimeError):
                async with db_session.get_session():
                    raise RuntimeError("boom")
            assert fake.commit_count == 0
            assert fake.rollback_count == 1
        else:
            async with db_session.get_session():
                pass
            assert fake.commit_count == 1
            assert fake.rollback_count == 0
    finally:
        db_session.create_session_factory = original_factory  # type: ignore[assignment]
        db_session.get_engine = original_get_engine  # type: ignore[assignment]
