"""Unit tests for natural-language SKILL parser cache path."""

from pathlib import Path

from owlclaw.capabilities.skill_nl_parser import detect_parse_mode, parse_natural_language_skill


def test_detect_parse_mode() -> None:
    assert detect_parse_mode({"name": "a"}) == "natural_language"
    assert detect_parse_mode({"name": "a", "owlclaw": {"task_type": "x"}}) == "structured"


def test_parse_natural_language_skill_writes_and_reuses_cache(tmp_path: Path) -> None:
    cache_root = tmp_path / ".owlclaw" / "cache"
    frontmatter = {"name": "inventory", "description": "每天早上 9 点检查库存"}
    body = "如果库存不足，告诉我补货建议。"

    first = parse_natural_language_skill(
        skill_name="inventory",
        frontmatter=frontmatter,
        body=body,
        cache_root=cache_root,
    )
    assert first.from_cache is False
    assert first.trigger_config == {"type": "cron", "expression": "0 9 * * *"}

    second = parse_natural_language_skill(
        skill_name="inventory",
        frontmatter=frontmatter,
        body=body,
        cache_root=cache_root,
    )
    assert second.from_cache is True
    assert second.trigger_config == first.trigger_config
