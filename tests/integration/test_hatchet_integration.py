"""Integration tests for Hatchet (use mock_run when no server).

Requires: .env with HATCHET_API_TOKEN and HATCHET_SERVER_URL (or set in env).
One test is skipped in mock_run: durable_sleep needs a real Hatchet worker (durable event listener).
"""

import os
from datetime import timedelta

import pytest

from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig

pytestmark = pytest.mark.integration


def _has_hatchet_token() -> bool:
    token = os.environ.get("HATCHET_API_TOKEN", "").strip()
    return bool(token and token.startswith("ey"))


@pytest.mark.asyncio
async def test_hatchet_task_mock_run_e2e():
    """E2E: connect, register task, run via mock_run (no Hatchet server)."""
    if not _has_hatchet_token():
        pytest.skip("HATCHET_API_TOKEN not set or invalid JWT; skipping Hatchet integration")

    config = HatchetConfig(api_token=os.environ["HATCHET_API_TOKEN"])
    client = HatchetClient(config)
    try:
        client.connect()
    except Exception:
        pytest.skip("Could not connect to Hatchet (server may be down)")

    try:
        @client.task(name="integration-echo")
        async def echo_task(input, ctx):
            return {"status": "ok"}

        standalone = client._workflows["integration-echo"]
        result = await standalone.aio_mock_run({})
        assert result == {"status": "ok"}
    finally:
        client.disconnect()


@pytest.mark.asyncio
async def test_hatchet_durable_task_aio_sleep_for_mock():
    """Task 7.2.1: Create task using ctx.aio_sleep_for(); verify via mock_run."""
    if not _has_hatchet_token():
        pytest.skip("HATCHET_API_TOKEN not set; skipping durable sleep test")

    config = HatchetConfig(api_token=os.environ["HATCHET_API_TOKEN"])
    client = HatchetClient(config)
    try:
        client.connect()
    except Exception:
        pytest.skip("Could not connect to Hatchet (server may be down)")

    try:
        @client.durable_task(name="integration-durable-sleep", timeout=30)
        async def durable_sleep_task(input, ctx):
            await ctx.aio_sleep_for(timedelta(seconds=0))  # 0s for fast mock
            return {"slept": True}

        standalone = client._workflows["integration-durable-sleep"]
        try:
            result = await standalone.aio_mock_run({})
            assert result == {"slept": True}
        except ValueError as e:
            if "durable event listener" in str(e).lower() or "Durable event listener" in str(e):
                pytest.skip("aio_sleep_for not supported in mock_run (no durable event listener); run with real worker for 7.2.3/7.2.4")
            raise
    finally:
        client.disconnect()
