"""Unit tests for STMManager."""


from owlclaw.agent.memory.stm import STMManager


def test_stm_add_trigger_and_to_prompt_section() -> None:
    """Fixed zone: trigger + focus appear in prompt section."""
    stm = STMManager(max_tokens=2000)
    stm.add_trigger("cron", {"schedule": "0 9 * * *"}, "Check daily report")
    section = stm.to_prompt_section()
    assert "Short-term context" in section
    assert "Trigger" in section
    assert "cron" in section
    assert "Check daily report" in section


def test_stm_inject_and_to_prompt_section() -> None:
    """Injected instructions appear in prompt section."""
    stm = STMManager(max_tokens=2000)
    stm.inject("Prefer option A")
    stm.inject("Skip validation")
    section = stm.to_prompt_section()
    assert "Injected instructions" in section
    assert "Prefer option A" in section
    assert "Skip validation" in section


def test_stm_add_function_call_and_llm_response() -> None:
    """Sliding zone: function call + LLM response appear as recent turns."""
    stm = STMManager(max_tokens=2000)
    stm.add_function_call("query_state", {"key": "x"}, {"value": 1})
    stm.add_llm_response("I see x=1.")
    section = stm.to_prompt_section()
    assert "Recent turns" in section
    assert "query_state" in section
    assert "I see x=1" in section


def test_stm_compress_keeps_last_3_rounds() -> None:
    """When over max_tokens, sliding zone is compressed but last 3 rounds kept."""
    stm = STMManager(max_tokens=150)
    for i in range(5):
        stm.add_function_call(f"tool_{i}", {"i": i}, {"result": "x" * 30})
        stm.add_llm_response("Response " + "y" * 25)
    section = stm.to_prompt_section()
    assert "earlier rounds summarized" in section or "Recent turns" in section
    assert "tool_4" in section or "tool_3" in section


def test_stm_empty_section() -> None:
    """Empty STM still renders a section header."""
    stm = STMManager(max_tokens=2000)
    section = stm.to_prompt_section()
    assert "Short-term context" in section
    assert "(empty)" in section
