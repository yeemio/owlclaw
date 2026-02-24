"""Unit tests for owlclaw db revision helper functions."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from owlclaw.cli.db_revision import _find_newest_revision_file


def test_find_newest_revision_file_skips_unreadable(monkeypatch, tmp_path: Path) -> None:
    versions_dir = tmp_path / "migrations" / "versions"
    versions_dir.mkdir(parents=True)
    bad = versions_dir / "bad.py"
    good = versions_dir / "good.py"
    bad.write_text("x", encoding="utf-8")
    good.write_text('revision = "abc123"', encoding="utf-8")

    original_read_text = Path.read_text

    def _patched_read_text(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        if self == bad:
            raise OSError("cannot read")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _patched_read_text)
    cfg = Config()
    cfg.set_main_option("script_location", str(tmp_path / "migrations"))
    resolved = _find_newest_revision_file(cfg, "abc123")
    assert resolved == good


def test_find_newest_revision_file_returns_none_when_no_versions(tmp_path: Path) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(tmp_path / "migrations"))
    assert _find_newest_revision_file(cfg, "abc123") is None


def test_find_newest_revision_file_matches_single_quoted_revision(tmp_path: Path) -> None:
    versions_dir = tmp_path / "migrations" / "versions"
    versions_dir.mkdir(parents=True)
    p = versions_dir / "x.py"
    p.write_text("revision = 'abc123'\n", encoding="utf-8")
    cfg = Config()
    cfg.set_main_option("script_location", str(tmp_path / "migrations"))
    assert _find_newest_revision_file(cfg, "abc123") == p
