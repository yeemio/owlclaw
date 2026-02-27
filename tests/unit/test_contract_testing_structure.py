"""Structure checks for contract-testing baseline assets."""

from __future__ import annotations

from pathlib import Path


def test_contract_testing_baseline_directories_exist() -> None:
    assert Path("tests/contracts/api").is_dir()
    assert Path("tests/contracts/mcp").is_dir()
    assert Path("scripts/contract_diff").is_dir()


def test_contract_diff_wrapper_exists() -> None:
    wrapper = Path("scripts/contract_diff/run_contract_diff.py")
    assert wrapper.exists()
    payload = wrapper.read_text(encoding="utf-8")
    assert "contract_diff.py" in payload
