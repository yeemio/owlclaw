# PostgreSQL NOTIFY 触发器设置指南

## 1. 生成模板

```bash
owlclaw trigger template db-change --output .
```

默认生成文件：`notify_trigger_position_changes.sql`。

## 2. 套用到业务表

按需修改模板中的：
- channel（例如 `position_changes`）
- 表名（例如 `positions`）
- 函数名与触发器名

然后在业务库执行：

```bash
psql "$BUSINESS_DB_URL" -f notify_trigger_position_changes.sql
```

## 3. 应用侧注册

```python
from owlclaw import OwlClaw
from owlclaw.triggers import db_change

app = OwlClaw("trading-agent")

app.trigger(db_change(
    channel="position_changes",
    event_name="position_changed",
    agent_id="trading-agent",
))
```

## 4. 运行要求

- `OWLCLAW_DATABASE_URL` 指向可执行 LISTEN 的 PostgreSQL。
- 监听用户需具备连接数据库与访问目标通道权限。
- NOTIFY payload 建议控制在 8KB 内（默认保护阈值 7900 bytes）。
