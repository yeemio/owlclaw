"""Unit tests for natural-language trigger resolver."""

from owlclaw.capabilities.trigger_resolver import resolve_trigger_intent


def test_resolve_daily_chinese_time_to_cron() -> None:
    result = resolve_trigger_intent("每天早上 9 点检查库存")
    assert result.trigger_config == {"type": "cron", "expression": "0 9 * * *"}
    assert result.confidence >= 0.9


def test_resolve_weekday_to_cron() -> None:
    result = resolve_trigger_intent("每周一生成报告")
    assert result.trigger_config == {"type": "cron", "expression": "0 0 * * 1"}
    assert result.confidence >= 0.8


def test_resolve_event_webhook() -> None:
    result = resolve_trigger_intent("当收到新订单时执行")
    assert result.trigger_config == {"type": "webhook", "event": "order.created"}
    assert result.confidence >= 0.8
