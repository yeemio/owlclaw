"""Tests for e2e CLI and configuration loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from owlclaw.e2e.cli import run_cli
from owlclaw.e2e.configuration import load_e2e_config


class _StubOrchestrator:
    async def run_full_validation(self, scenarios: list[object], *, timeout_seconds: int, fail_fast: bool) -> dict[str, Any]:
        return {
            "mode": "full",
            "scenario_count": len(scenarios),
            "timeout_seconds": timeout_seconds,
            "fail_fast": fail_fast,
        }

    async def run_mionyee_task(self, task_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"mode": "mionyee", "task_id": task_id, "params": params or {}}

    async def run_decision_comparison(self, scenarios: list[object]) -> dict[str, Any]:
        return {"mode": "comparison", "scenario_count": len(scenarios)}

    async def run_integration_tests(self, scenarios: list[object]) -> dict[str, Any]:
        return {"mode": "integration", "scenario_count": len(scenarios)}


def test_load_e2e_config_supports_env_overrides() -> None:
    config = load_e2e_config(
        environ={
            "OWLCLAW_E2E_MODE": "mionyee",
            "OWLCLAW_E2E_TASK_ID": "3",
            "OWLCLAW_E2E_TIMEOUT_SECONDS": "42",
            "OWLCLAW_E2E_FAIL_FAST": "true",
        }
    )
    assert config.mode == "mionyee"
    assert config.task_id == "3"
    assert config.timeout_seconds == 42
    assert config.fail_fast is True


def test_run_cli_mionyee_mode() -> None:
    result = run_cli(["--mode", "mionyee", "--task-id", "2"], orchestrator=_StubOrchestrator())
    assert result == {"mode": "mionyee", "task_id": "2", "params": {}}


def test_run_cli_full_mode_with_scenario_file_and_output(tmp_path: Path) -> None:
    scenario_file = tmp_path / "scenarios.json"
    scenario_file.write_text(
        json.dumps(
            [
                {"scenario_id": "s1", "name": "s1", "scenario_type": "integration"},
                {"scenario_id": "s2", "name": "s2", "scenario_type": "performance"},
            ]
        ),
        encoding="utf-8",
    )
    output_file = tmp_path / "out" / "result.json"

    result = run_cli(
        [
            "--mode",
            "full",
            "--scenario-file",
            str(scenario_file),
            "--timeout-seconds",
            "90",
            "--fail-fast",
            "--output-file",
            str(output_file),
        ],
        orchestrator=_StubOrchestrator(),
    )

    assert result["mode"] == "full"
    assert result["scenario_count"] == 2
    assert result["timeout_seconds"] == 90
    assert result["fail_fast"] is True
    saved = json.loads(output_file.read_text(encoding="utf-8"))
    assert saved["scenario_count"] == 2

