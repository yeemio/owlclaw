"""
Durable sleep — a task that sleeps across process restarts (Hatchet durable execution).

Uses ctx.aio_sleep_for() so that if the worker crashes, the sleep completes after restart.
Requires Hatchet server and a durable task (SDK durable_task). This example shows the pattern;
full durable_task support is in the Hatchet SDK (DurableContext).
"""

# This example documents the pattern; OwlClaw's HatchetClient wraps the SDK task() decorator.
# For durable sleep you would use the SDK's durable_task and DurableContext.aio_sleep_for()
# inside the task. Example (pseudo):
#
#   from hatchet_sdk import Hatchet, DurableContext
#   hatchet = Hatchet(config=...)
#
#   @hatchet.durable_task(name="heartbeat")
#   async def heartbeat(ctx: DurableContext):
#       await ctx.aio_sleep_for(timedelta(minutes=30))
#       return await do_work()
#
# See design doc: .kiro/specs/integrations-hatchet/design.md

print("See design doc and Hatchet SDK docs for durable_task + DurableContext.aio_sleep_for().")
