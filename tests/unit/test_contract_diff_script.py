"""Tests for scripts/contract_diff.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_contract_diff(
    repo: Path,
    before: Path,
    after: Path,
    mode: str = "warning",
    migration_plan: str | None = None,
    exemption_ticket: str | None = None,
    audit_log: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    script = repo / "scripts" / "contract_diff.py"
    cmd = [
        sys.executable,
        str(script),
        "--before",
        str(before),
        "--after",
        str(after),
        "--mode",
        mode,
    ]
    if migration_plan:
        cmd.extend(["--migration-plan", migration_plan])
    if exemption_ticket:
        cmd.extend(["--exemption-ticket", exemption_ticket])
    if audit_log:
        cmd.extend(["--audit-log", str(audit_log)])
    return subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_contract_diff_classifies_additive_and_warn_mode_passes(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({"paths": {"GET /v1/ping": {"summary": "ping"}}}), encoding="utf-8")
    after.write_text(
        json.dumps(
            {
                "paths": {
                    "GET /v1/ping": {"summary": "ping"},
                    "GET /v1/status": {"summary": "status"},
                }
            }
        ),
        encoding="utf-8",
    )

    result = _run_contract_diff(repo, before, after, mode="warning")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["change_level"] == "additive"
    assert payload["gate_decision"] == "pass"


def test_contract_diff_classifies_breaking_and_blocks_without_migration(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text(
        "paths:\n  GET /v1/ping:\n    summary: ping\n  GET /v1/status:\n    summary: status\n",
        encoding="utf-8",
    )
    after.write_text("paths:\n  GET /v1/ping:\n    summary: ping\n", encoding="utf-8")

    result = _run_contract_diff(repo, before, after, mode="blocking")
    payload = json.loads(result.stdout)
    assert payload["change_level"] == "breaking"
    assert payload["gate_decision"] == "block"
    assert result.returncode == 2


def test_contract_diff_breaking_with_migration_plan_passes_blocking_mode(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({"version": "v1", "paths": {"GET /v1/ping": {"summary": "ping"}}}), encoding="utf-8")
    after.write_text(json.dumps({"version": "v2", "paths": {"GET /v1/ping": {"summary": "pong"}}}), encoding="utf-8")

    result = _run_contract_diff(repo, before, after, mode="blocking", migration_plan="docs/migration.md")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["change_level"] == "breaking"
    assert payload["gate_decision"] == "pass"


def test_contract_diff_breaking_with_exemption_records_audit(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    audit_log = tmp_path / "audit" / "gate.jsonl"
    before.write_text(json.dumps({"paths": {"GET /v1/ping": {"summary": "ping"}}}), encoding="utf-8")
    after.write_text(json.dumps({"paths": {"GET /v1/ping": {"summary": "pong"}}}), encoding="utf-8")

    result = _run_contract_diff(
        repo,
        before,
        after,
        mode="blocking",
        exemption_ticket="EX-2026-0001",
        audit_log=audit_log,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["gate_decision"] == "warn"
    assert audit_log.exists()
    audit_rows = audit_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(audit_rows) == 1
    audit_payload = json.loads(audit_rows[0])
    assert audit_payload["exemption_ticket"] == "EX-2026-0001"
