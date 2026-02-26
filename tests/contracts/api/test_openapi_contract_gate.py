"""OpenAPI contract diff gate checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_contract_gate(args: list[str]) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[3]
    wrapper = repo / "scripts" / "contract_diff" / "run_contract_diff.py"
    return subprocess.run(
        [sys.executable, str(wrapper), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_openapi_additive_change_passes_blocking_mode() -> None:
    base = Path("tests/contracts/api/openapi_before.json")
    additive = Path("tests/contracts/api/openapi_after_additive.json")
    result = _run_contract_gate(
        [
            "--before",
            str(base),
            "--after",
            str(additive),
            "--mode",
            "blocking",
        ]
    )
    assert result.returncode == 0, result.stderr
    assert '"change_level": "additive"' in result.stdout
    assert '"gate_decision": "pass"' in result.stdout


def test_openapi_breaking_change_blocks_without_migration() -> None:
    base = Path("tests/contracts/api/openapi_before.json")
    breaking = Path("tests/contracts/api/openapi_after_breaking.json")
    result = _run_contract_gate(
        [
            "--before",
            str(base),
            "--after",
            str(breaking),
            "--mode",
            "blocking",
        ]
    )
    assert result.returncode == 2
    assert '"change_level": "breaking"' in result.stdout
    assert '"gate_decision": "block"' in result.stdout
