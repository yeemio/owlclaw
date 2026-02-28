"""Validation for consulting templates in content-launch spec."""

from __future__ import annotations

from pathlib import Path


def test_consulting_template_has_required_sections_and_placeholders() -> None:
    template = Path("docs/consulting/ai-transformation-template.md")
    assert template.exists()

    content = template.read_text(encoding="utf-8")
    required_sections = [
        "## 一、现状调研",
        "## 二、方案设计",
        "## 三、实施计划",
        "## 四、投资与回报",
        "## 五、风险与缓解",
        "## 六、验收标准",
    ]
    for section in required_sections:
        assert section in content

    placeholders = ["[CLIENT_NAME]", "[SYSTEM_TYPE]", "[SCENARIO_TYPE]", "[PROJECT_BUDGET]", "[MAINTENANCE_BUDGET]"]
    for token in placeholders:
        assert token in content

    assert "| 服务项 | 说明 | 参考价格 |" in content


def test_consulting_scenario_variants_exist() -> None:
    variants = [
        ("docs/consulting/scenario-report-insight.md", "报表解读"),
        ("docs/consulting/scenario-customer-followup.md", "客户跟进"),
        ("docs/consulting/scenario-inventory-alert.md", "库存预警"),
    ]
    for path, keyword in variants:
        file_path = Path(path)
        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        assert keyword in content
        assert "## 业务目标" in content
        assert "## 技术映射" in content
        assert "## 交付重点" in content

