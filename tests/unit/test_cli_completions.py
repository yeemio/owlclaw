"""Tests for shell completion helper scripts."""

from __future__ import annotations

from pathlib import Path


def test_completion_scripts_exist_and_contain_owlclaw_entries() -> None:
    repo = Path(__file__).resolve().parents[2]
    bash = repo / "scripts" / "completions" / "owlclaw.bash"
    zsh = repo / "scripts" / "completions" / "owlclaw.zsh"
    fish = repo / "scripts" / "completions" / "owlclaw.fish"
    assert bash.exists()
    assert zsh.exists()
    assert fish.exists()
    assert "owlclaw" in bash.read_text(encoding="utf-8")
    assert "owlclaw" in zsh.read_text(encoding="utf-8")
    assert "owlclaw" in fish.read_text(encoding="utf-8")
