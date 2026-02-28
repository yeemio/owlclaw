from __future__ import annotations

from hatchet_sdk import Hatchet

hatchet = Hatchet()

@hatchet.task(name="mionyee-task-2", on_crons=["0 12 * * 1-5"])
async def MionyeeTask2Workflow_run(input_data, ctx):
    """Generated from APScheduler job: mionyee.scheduler.risk_review"""
    return {
        "status": "ok",
        "source": "mionyee.scheduler.risk_review",
        "input": input_data,
    }
