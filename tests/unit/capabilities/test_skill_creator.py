"""Unit tests for conversational SkillCreatorAgent."""

from owlclaw.capabilities.skill_creator import SkillConversationState, SkillCreatorAgent


def test_skill_creator_collects_required_fields() -> None:
    agent = SkillCreatorAgent(available_capabilities=["get-inventory", "send-email"])
    state = SkillConversationState()
    agent.update_state_from_user_input(state, "我想检查库存")
    assert state.core_intent
    assert agent.is_complete(state) is False
    agent.update_state_from_user_input(state, "每天早上9点执行并邮件通知我")
    assert agent.is_complete(state) is True
    rendered = agent.generate_skill_markdown(state)
    assert "name:" in rendered
    assert "Trigger:" in rendered


def test_skill_creator_recommends_capabilities() -> None:
    agent = SkillCreatorAgent(available_capabilities=["get-inventory-levels", "send-email"])
    state = SkillConversationState()
    agent.update_state_from_user_input(state, "库存不足就发邮件")
    suggestions = agent.recommend_capabilities(state)
    assert isinstance(suggestions, list)
