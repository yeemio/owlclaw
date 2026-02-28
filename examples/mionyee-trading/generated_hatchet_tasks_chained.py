from __future__ import annotations

from hatchet_sdk import Hatchet

hatchet = Hatchet()

@hatchet.task(name="mionyee-task-3", on_crons=["30 14 * * 1-5"])
async def MionyeeTask3Workflow_run(input_data, ctx):
    """Generated from APScheduler job: mionyee.scheduler.position_adjust"""
    return {
        "status": "ok",
        "source": "mionyee.scheduler.position_adjust",
        "input": input_data,
    }
