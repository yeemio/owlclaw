"""CLI entrypoint for e2e validation workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from owlclaw.e2e.configuration import E2EConfig, load_e2e_config
from owlclaw.e2e.models import ScenarioType, TestScenario
from owlclaw.e2e.orchestrator import TestOrchestrator


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for e2e validation commands."""
    parser = argparse.ArgumentParser(prog="owlclaw-e2e", description="Run OwlClaw e2e validation flows.")
    parser.add_argument(
        "--mode",
        choices=["full", "mionyee", "comparison", "integration", "performance", "concurrency"],
        default=None,
        help="Validation mode to run.",
    )
    parser.add_argument("--scenario-file", default=None, help="Path to scenario JSON file.")
    parser.add_argument("--task-id", default=None, help="Mionyee task id used by --mode mionyee.")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="Timeout for each scenario execution.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failed/error scenario.")
    parser.add_argument("--output-file", default=None, help="Optional JSON output file path.")
    parser.add_argument("--config", default=None, help="Optional e2e config JSON path.")
    return parser


def run_cli(argv: list[str] | None = None, *, orchestrator: TestOrchestrator | None = None) -> dict[str, Any]:
    """Run e2e validation CLI with optional injected orchestrator."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_e2e_config(config_path=args.config)
    effective = _merge_runtime_args(config, args)
    runtime = orchestrator or TestOrchestrator()
    result = asyncio.run(_execute_mode(runtime, effective))

    if effective.output_file:
        _write_output(effective.output_file, result)
    return result


def _merge_runtime_args(config: E2EConfig, args: argparse.Namespace) -> E2EConfig:
    payload: dict[str, Any] = config.model_dump()
    for field in ("mode", "scenario_file", "task_id", "timeout_seconds", "output_file"):
        value = getattr(args, field)
        if value is not None:
            payload[field] = value
    if args.fail_fast:
        payload["fail_fast"] = True
    return E2EConfig.model_validate(payload)


async def _execute_mode(orchestrator: TestOrchestrator, config: E2EConfig) -> dict[str, Any]:
    scenarios = _load_scenarios(config.scenario_file)
    if config.mode == "full":
        return await orchestrator.run_full_validation(
            scenarios,
            timeout_seconds=config.timeout_seconds,
            fail_fast=config.fail_fast,
        )
    if config.mode == "mionyee":
        return await orchestrator.run_mionyee_task(config.task_id, {})
    if config.mode == "comparison":
        return await orchestrator.run_decision_comparison(scenarios)
    if config.mode == "integration":
        return await orchestrator.run_integration_tests(_filter_scenarios(scenarios, ScenarioType.INTEGRATION))
    if config.mode == "performance":
        return await orchestrator.run_full_validation(
            _filter_scenarios(scenarios, ScenarioType.PERFORMANCE),
            timeout_seconds=config.timeout_seconds,
            fail_fast=config.fail_fast,
        )
    if config.mode == "concurrency":
        return await orchestrator.run_full_validation(
            _filter_scenarios(scenarios, ScenarioType.CONCURRENCY),
            timeout_seconds=config.timeout_seconds,
            fail_fast=config.fail_fast,
        )
    raise ValueError(f"unsupported mode: {config.mode}")


def _load_scenarios(scenario_file: str | None) -> list[TestScenario]:
    if not scenario_file:
        return []
    data = json.loads(Path(scenario_file).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("scenario file must be a JSON array")
    scenarios: list[TestScenario] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each scenario must be a JSON object")
        scenarios.append(TestScenario.model_validate(item))
    return scenarios


def _filter_scenarios(scenarios: list[TestScenario], scenario_type: ScenarioType) -> list[TestScenario]:
    return [scenario for scenario in scenarios if scenario.scenario_type == scenario_type]


def _write_output(output_file: str, result: dict[str, Any]) -> None:
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")

