from __future__ import annotations

from hatchet_sdk import Hatchet

hatchet = Hatchet()

@hatchet.task(name="mionyee-task-1", on_crons=["30 9 * * 1-5"])
async def MionyeeTask1Workflow_run(input_data, ctx):
    """Generated from APScheduler job: mionyee.scheduler.entry_monitor"""
    return {
        "status": "ok",
        "source": "mionyee.scheduler.entry_monitor",
        "input": input_data,
    }
