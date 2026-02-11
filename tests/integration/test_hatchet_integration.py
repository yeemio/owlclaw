"""Integration tests for Hatchet (use mock_run when no server)."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_hatchet_task_mock_run_e2e():
    """E2E: connect, register task, run via mock_run (no Hatchet server)."""
    import os
    from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig

    token = os.environ.get("HATCHET_API_TOKEN", "").strip()
    if not token or not token.startswith("ey"):
        pytest.skip("HATCHET_API_TOKEN not set or invalid JWT; skipping Hatchet integration")

    config = HatchetConfig(api_token=token)
    client = HatchetClient(config)
    client.connect()
    try:
        @client.task(name="integration-echo")
        async def echo_task(ctx):
            return {"status": "ok"}

        standalone = client._workflows["integration-echo"]
        result = await standalone.aio_mock_run({})
        assert result == {"status": "ok"}
    finally:
        client.disconnect()
