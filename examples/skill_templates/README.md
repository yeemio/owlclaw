# SKILL.md 模板库示例

本目录演示如何使用 `owlclaw.templates.skills` 模板库创建、渲染和验证 SKILL.md 文件。

## 1. 使用 CLI 创建监控类 Skill（5 分钟内完成）

```bash
# 列出可用模板
owlclaw skill templates

# 使用监控模板创建 Skill（非交互式）
owlclaw skill init --template monitoring/health-check --param "skill_name=My Health Check,skill_description=Monitor API health,endpoints=/health,/ready" --output capabilities
```

## 2. 使用 Python API 渲染模板

```python
from pathlib import Path
from owlclaw.templates.skills import (
    TemplateRegistry,
    TemplateRenderer,
    get_default_templates_dir,
)

registry = TemplateRegistry(get_default_templates_dir())
renderer = TemplateRenderer(registry)

params = {
    "skill_name": "API Health Monitor",
    "skill_description": "Monitor API endpoint health",
    "endpoints": "/health,/ready",
}
content = renderer.render("monitoring/health-check", params)

output_dir = Path("capabilities/api-health-monitor")
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "SKILL.md").write_text(content, encoding="utf-8")
```

## 3. 验证生成的文件

```bash
owlclaw skill validate capabilities/
```
