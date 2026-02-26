# Quick Start（10 分钟）

> 目标：10 分钟内从安装到看到 OwlClaw Agent 的决策输出。  
> 模式：`Lite Mode`，零外部依赖（无需 PostgreSQL / Hatchet / LLM API Key）。

---

## 1. 前置条件

- Python `>= 3.10`
- 可用的 `pip` 或 `poetry`

---

## 2. 安装

```bash
pip install owlclaw
# 或
poetry add owlclaw
```

---

## 3. 准备项目结构

```text
quick-start-demo/
├── app.py
├── SOUL.md
├── IDENTITY.md
└── skills/
    └── inventory-check/
        └── SKILL.md
```

### `SOUL.md`

```markdown
# SOUL

You are an inventory operations assistant.
```

### `skills/inventory-check/SKILL.md`

```yaml
---

### `IDENTITY.md`

```markdown
# IDENTITY

- Domain: inventory operations
- Allowed actions:
  - inventory-check
```

---
name: inventory-check
description: Check stock level and decide whether to reorder.
owlclaw:
  spec_version: "1.0"
  task_type: operations
---
```

---

## 4. 编写 `app.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from owlclaw import OwlClaw

APP_DIR = Path(__file__).resolve().parent

app = OwlClaw.lite(
    "inventory-agent",
    skills_path=str(APP_DIR / "skills"),
    heartbeat_interval_minutes=1,
)

@app.handler("inventory-check")
async def inventory_check(session: dict[str, Any]) -> dict[str, Any]:
    available = int(session.get("available", 6))
    threshold = int(session.get("threshold", 10))
    if available < threshold:
        return {"action": "reorder", "sku": "WIDGET-42", "quantity": 100}
    return {"action": "hold"}

if __name__ == "__main__":
    app.run(app_dir=str(APP_DIR))
```

代码说明（关键点）：
- `OwlClaw.lite(...)`：启用 Lite Mode（mock LLM + in-memory memory + in-memory ledger）
- `skills_path`：挂载业务技能目录，自动扫描 `SKILL.md`
- `@app.handler("inventory-check")`：注册业务处理函数
- `app.run(...)`：阻塞启动，按 `Ctrl+C` 安全退出

---

## 5. 运行

```bash
python app.py
```

预期会看到类似日志：

```text
OwlClaw 'inventory-agent' created in Lite Mode ...
Starting OwlClaw application 'inventory-agent'
OwlClaw 'inventory-agent' is running ...
```

停止方式：
- 按 `Ctrl+C` 退出（exit code `0`）

---

## 6. 直接运行仓库内最小示例

```bash
python examples/quick_start/app.py
```

如果你想快速验证（非阻塞）：

```bash
python examples/quick_start/app.py --once
```

---

## 7. 下一步

- 架构总览：[ARCHITECTURE_ANALYSIS.md](./ARCHITECTURE_ANALYSIS.md)
- 示例索引：[examples/README.md](../examples/README.md)
- 完整开发文档：[DEVELOPMENT.md](./DEVELOPMENT.md)
