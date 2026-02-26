"""Unit tests for progressive migration gate."""

from __future__ import annotations

from pathlib import Path

from owlclaw.governance.migration_gate import MigrationDecision, MigrationGate


def test_migration_gate_decision_boundaries() -> None:
    gate = MigrationGate(
        skill_weights={"obs": 0, "auto": 100, "mid": 70},
        random_fn=lambda: 0.2,
    )
    observe = gate.evaluate(skill_name="obs", action={})
    assert observe.decision == MigrationDecision.OBSERVE_ONLY

    auto = gate.evaluate(skill_name="auto", action={})
    assert auto.decision == MigrationDecision.AUTO_EXECUTE

    mid = gate.evaluate(
        skill_name="mid",
        action={"binding": {"method": "GET"}, "impact_scope": "single", "amount": 0},
    )
    assert mid.decision == MigrationDecision.AUTO_EXECUTE


def test_migration_gate_requires_approval_when_probability_not_hit() -> None:
    gate = MigrationGate(
        skill_weights={"mid": 30},
        random_fn=lambda: 0.95,
    )
    outcome = gate.evaluate(
        skill_name="mid",
        action={"binding": {"method": "POST"}, "impact_scope": "batch", "amount": 5000},
    )
    assert outcome.decision == MigrationDecision.REQUIRE_APPROVAL
    assert 0.0 <= outcome.execution_probability <= 1.0


def test_migration_gate_reads_and_hot_reloads_yaml_config(tmp_path: Path) -> None:
    cfg = tmp_path / "owlclaw.yaml"
    cfg.write_text(
        "skills:\n  inventory-check:\n    migration_weight: 30\n",
        encoding="utf-8",
    )
    gate = MigrationGate(config_path=cfg, random_fn=lambda: 0.0)
    assert gate.get_weight("inventory-check") == 30

    cfg.write_text(
        "skills:\n  inventory-check:\n    migration_weight: 80\n",
        encoding="utf-8",
    )
    gate.refresh_from_config()
    assert gate.get_weight("inventory-check") == 80


def test_migration_gate_skill_inline_weight_precedence() -> None:
    gate = MigrationGate(skill_weights={"inventory-check": 20}, random_fn=lambda: 0.0)
    outcome = gate.evaluate(
        skill_name="inventory-check",
        action={"binding": {"method": "GET"}},
        skill_owlclaw={"migration_weight": 60},
    )
    assert outcome.migration_weight == 60
