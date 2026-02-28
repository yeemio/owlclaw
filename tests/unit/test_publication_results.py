"""Tests for content publication evidence recording."""

from __future__ import annotations

from scripts.content.record_publication_results import evaluate


def test_publication_evidence_passes_with_en_and_zh_channels() -> None:
    result = evaluate(
        [
            {
                "channel": "reddit",
                "url": "https://reddit.com/example",
                "language": "en",
                "title": "English post",
                "published_at": "2026-03-01T09:00:00Z",
            },
            {
                "channel": "juejin",
                "url": "https://juejin.cn/post/example",
                "language": "zh",
                "title": "Chinese post",
                "published_at": "2026-03-01T10:00:00Z",
            },
        ]
    )
    assert result["meets_task_2_6"] is True
    assert result["meets_task_2_7"] is True
    assert result["meets_task_5_1"] is True
    assert result["all_required_passed"] is True


def test_publication_evidence_fails_when_missing_chinese_channel() -> None:
    result = evaluate(
        [
            {
                "channel": "hackernews",
                "url": "https://news.ycombinator.com/item?id=123",
                "language": "en",
                "title": "Show HN",
                "published_at": "2026-03-01T09:00:00Z",
            },
            {
                "channel": "reddit",
                "url": "https://reddit.com/example",
                "language": "en",
                "title": "Reddit post",
                "published_at": "2026-03-01T10:00:00Z",
            },
        ]
    )
    assert result["meets_task_2_6"] is True
    assert result["meets_task_2_7"] is False
    assert result["all_required_passed"] is False
