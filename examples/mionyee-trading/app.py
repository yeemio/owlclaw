"""Runnable mionyee trading flow example based on owlclaw.e2e components.

Run:
  poetry run python examples/mionyee-trading/app.py --all --json
  poetry run python examples/mionyee-trading/app.py --task-id 2 --symbol TSLA --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from owlclaw.e2e.execution_engine import ExecutionEngine
from owlclaw.e2e.orchestrator import TestOrchestrator


def _build_orchestrator() -> TestOrchestrator:
    async def cron_trigger(payload: dict[str, object]) -> dict[str, object]:
        return {"triggered": True, "task_id": payload.get("task_id")}

    async def agent_runtime(payload: dict[str, object]) -> dict[str, object]:
        return {"processed": True, "task_id": payload.get("task_id")}

    async def skills_system(payload: dict[str, object]) -> dict[str, object]:
        task_id = str(payload.get("task_id"))
        if task_id == "1":
            return {"skills": ["entry-monitor"]}
        if task_id == "2":
            return {"skills": ["morning-decision"]}
        return {"skills": ["knowledge-feedback"]}

    async def governance_layer(_: dict[str, object]) -> dict[str, object]:
        return {"checks": ["permission_ok", "budget_ok"]}

    async def hatchet_integration(payload: dict[str, object]) -> dict[str, object]:
        return {"workflow_id": f"wf-{payload.get('task_id', 'x')}"}

    engine = ExecutionEngine()
    engine.configure_mionyee_components(
        cron_trigger=cron_trigger,
        agent_runtime=agent_runtime,
        skills_system=skills_system,
        governance_layer=governance_layer,
        hatchet_integration=hatchet_integration,
    )
    return TestOrchestrator(primary_engine=engine)


async def _run_task(task_id: str, symbol: str) -> dict[str, Any]:
    orchestrator = _build_orchestrator()
    payload = {"symbol": symbol}
    return await orchestrator.run_mionyee_task(task_id, payload)


async def _run_all(symbol: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for task_id in ("1", "2", "3"):
        results.append(await _run_task(task_id, symbol))
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mionyee trading example flow.")
    parser.add_argument("--task-id", choices=["1", "2", "3"], help="Run one task only.")
    parser.add_argument("--all", action="store_true", help="Run all three tasks.")
    parser.add_argument("--symbol", default="AAPL", help="Demo symbol payload value.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    return parser.parse_args()


async def _main_async() -> int:
    args = _parse_args()
    if not args.all and not args.task_id:
        args.all = True

    if args.all:
        results = await _run_all(args.symbol)
        if args.json:
            print(json.dumps({"results": results}, ensure_ascii=False))
        else:
            for item in results:
                print(
                    f"task={item['scenario_id']} status={item['status']} "
                    f"workflow={item['output'].get('hatchet_workflow_id')}"
                )
        return 0 if all(item["status"] == "passed" for item in results) else 1

    result = await _run_task(args.task_id, args.symbol)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(
            f"task={result['scenario_id']} status={result['status']} "
            f"workflow={result['output'].get('hatchet_workflow_id')}"
        )
    return 0 if result["status"] == "passed" else 1


def main() -> None:
    raise SystemExit(asyncio.run(_main_async()))


if __name__ == "__main__":
    main()
