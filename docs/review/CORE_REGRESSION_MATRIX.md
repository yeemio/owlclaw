# 核心链路回归测试矩阵（One-Command）

> 目标：把“可跑通”升级为“可证明稳定”。  
> 覆盖链路：启动、能力注册、触发器（API/Webhook/Queue/Signal/db_change）、MCP、Web API。

---

## 1) 一键回归命令（发布前必跑）

```powershell
pwsh ./scripts/regression-core.ps1
```

或手动执行：

```powershell
poetry run pytest ^
  tests/unit/triggers/test_api.py ^
  tests/unit/triggers/test_webhook_http_gateway.py ^
  tests/unit/triggers/test_queue_trigger.py ^
  tests/unit/triggers/test_signal.py ^
  tests/unit/triggers/test_db_change.py ^
  tests/integration/test_api_trigger_integration.py ^
  tests/unit/test_mcp_server.py ^
  tests/unit/web/test_middleware.py ^
  tests/unit/web/test_overview.py ^
  tests/unit/web/test_governance.py -q
```

---

## 2) 回归矩阵（核心路径）

| 模块 | 典型风险 | 关键用例 | 通过标准 |
|---|---|---|---|
| 启动与生命周期 | 启停泄漏、依赖未释放 | `test_api.py` + integration API trigger | 无 hanging task，初始化/停止可重复 |
| 能力注册 | handler/schema 漂移 | `test_mcp_server.py` | `tools/list` 与注册 schema 一致 |
| API Trigger | 鉴权绕过、run 查询越权 | `test_api.py` + integration | 未授权为 401，结果读取绑定身份 |
| Webhook Trigger | 内存 DoS、事件日志泄露 | `test_webhook_http_gateway.py` | 大包 413，敏感 header 脱敏，`/events` 受鉴权 |
| Queue Trigger | 重试风暴、DLQ 语义错误、tenant 注入 | `test_queue_trigger.py` | 重试有界，ack/nack 行为符合策略，tenant 仅在受信生产者/签名条件下透传 |
| Signal Trigger | 人工信号越权与状态漂移 | `test_signal.py` | pause/resume/instruct 状态一致 |
| db_change Trigger | 事件解析漂移、监听失效 | `test_db_change.py` | 监听与事件分发行为稳定 |
| MCP | token 校验、协议错误码偏差 | `test_mcp_server.py` | initialize/token/error code 正确 |
| Web API | fail-open、异常泄露 | `test_middleware.py`/`test_overview.py`/`test_governance.py` | 鉴权闭合，错误信息受控 |

---

## 3) 失败注入与异常路径（建议每周）

```powershell
pwsh ./scripts/regression-failure-paths.ps1
```

或手动执行：

```powershell
poetry run pytest ^
  tests/unit/triggers/test_api.py ^
  tests/unit/triggers/test_webhook_http_gateway.py ^
  tests/unit/triggers/test_queue_trigger_properties.py ^
  tests/unit/triggers/test_queue_kafka_adapter.py ^
  tests/unit/triggers/test_queue_log_security.py -q
```

覆盖重点：
- 超时：`asyncio.wait_for` 或上游调用超时后的可恢复性
- 空响应：依赖返回空 payload / 空 body 时的边界行为
- 依赖不可用：runtime/governance/adapter 报错时的降级路径
- 并发冲突：幂等与重试冲突下的一致性
- 安全边界：鉴权失败、租户绑定、敏感信息脱敏

---

## 4) 执行记录模板（可直接复制）

- 执行时间：
- 执行人：
- Commit/Branch：
- 命令：
- 通过/失败：
- 失败用例与根因：
- 处置结果（修复/降级/阻塞）：

## 5) 最近执行快照

- 核心回归矩阵：`116 passed`
- 失败注入专项：`55 passed`
- 当前状态：关键链路与异常路径均通过，输出已达发布前门禁标准

