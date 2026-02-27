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

@hatchet.task(name="mionyee-task-2", on_crons=["0 12 * * 1-5"])
async def MionyeeTask2Workflow_run(input_data, ctx):
    """Generated from APScheduler job: mionyee.scheduler.risk_review"""
    return {
        "status": "ok",
        "source": "mionyee.scheduler.risk_review",
        "input": input_data,
    }

@hatchet.task(name="mionyee-task-3", on_crons=["30 14 * * 1-5"])
async def MionyeeTask3Workflow_run(input_data, ctx):
    """Generated from APScheduler job: mionyee.scheduler.position_adjust"""
    return {
        "status": "ok",
        "source": "mionyee.scheduler.position_adjust",
        "input": input_data,
    }
