"""Standalone Hatchet worker runner used by integration tests.

This script is launched in a subprocess so tests can terminate/restart the
worker process and validate durable-timer recovery behavior.
"""

from __future__ import annotations

import os
from datetime import timedelta

from owlclaw.integrations.hatchet import HatchetClient, HatchetConfig


def main() -> int:
    token = os.environ.get("HATCHET_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HATCHET_API_TOKEN is required for _hatchet_worker_runner")

    task_name = os.environ.get("HATCHET_E2E_TASK_NAME", "integration-durable-restart")
    sleep_seconds = float(os.environ.get("HATCHET_E2E_SLEEP_SECONDS", "8"))

    client = HatchetClient(HatchetConfig(api_token=token))
    client.connect()

    @client.durable_task(name=task_name, timeout=max(int(sleep_seconds * 4), 30))
    async def _durable_task(input, ctx):
        await ctx.aio_sleep_for(timedelta(seconds=sleep_seconds))
        return {"status": "ok", "task": task_name}

    client.start_worker()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
