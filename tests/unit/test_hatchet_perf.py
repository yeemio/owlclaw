"""Light performance tests for Hatchet integration (no server)."""

import time

import pytest

from owlclaw.integrations.hatchet import HatchetConfig, HatchetClient


def test_config_from_yaml_perf(tmp_path):
    """Config load from YAML is fast (< 50ms for single load)."""
    (tmp_path / "c.yaml").write_text("hatchet:\n  server_url: http://localhost:7077\n", encoding="utf-8")
    start = time.perf_counter()
    for _ in range(100):
        HatchetConfig.from_yaml(tmp_path / "c.yaml")
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, "100 config loads should complete in under 2s"


def test_schedule_task_validation_perf():
    """schedule_task validation (unregistered task) is fast."""
    import asyncio
    client = HatchetClient(HatchetConfig())

    async def run_many():
        for _ in range(200):
            try:
                await client.schedule_task("x", delay_seconds=1)
            except ValueError:
                pass

    start = time.perf_counter()
    asyncio.run(run_many())
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, "200 validation failures should complete in under 2s"
