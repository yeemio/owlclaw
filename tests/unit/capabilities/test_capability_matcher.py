"""Unit tests for capability semantic matcher."""

from owlclaw.capabilities.capability_matcher import CapabilityMatcher, parse_available_tools


def test_parse_available_tools_deduplicates_and_sorts() -> None:
    tools = parse_available_tools("send-email, get-inventory,send-email")
    assert tools == ["get-inventory", "send-email"]


def test_capability_matcher_exact_match_wins() -> None:
    matcher = CapabilityMatcher(enable_llm_confirmation=False)
    matches = matcher.resolve(
        tool_intents=["Please send-email when low stock"],
        available_tools=["send-email", "query-stock"],
    )
    assert matches
    assert matches[0].tool_name == "send-email"
    assert matches[0].method == "exact"


def test_capability_matcher_embedding_match() -> None:
    matcher = CapabilityMatcher(embedding_threshold=0.1, enable_llm_confirmation=False)
    matches = matcher.resolve(
        tool_intents=["check inventory levels"],
        available_tools=["inventory-checker", "notify-admin"],
    )
    assert any(item.tool_name == "inventory-checker" for item in matches)
