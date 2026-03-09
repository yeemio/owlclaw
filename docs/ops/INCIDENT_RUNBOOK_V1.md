# OwlClaw 故障手册 v1（SOP）

> 覆盖四类高频故障：启动失败、MCP 异常、Webhook 异常、LLM 超时。  
> 目标：按步骤执行即可定位，避免“靠经验救火”。

---

## 0) 通用排查顺序（先执行）

1. `poetry run owlclaw --help` 确认 CLI 与虚拟环境可用
2. `poetry run owlclaw start --help` 确认入口参数可解析
3. 检查环境变量：`OWLCLAW_DATABASE_URL`、`OWLCLAW_CONSOLE_AUTH_TOKEN`、`OWLCLAW_MCP_TOKEN`
4. 执行核心回归：`poetry run pytest tests/unit/test_configuration.py tests/unit/test_mcp_server.py -q`
5. 记录本次排查 `run_id/trace_id`（便于复盘）

---

## 1) 启动失败

**症状**
- 进程无法启动，或启动后立即退出

**SOP**
1. `poetry run owlclaw start --help`
2. `poetry run owlclaw db status`（如依赖数据库）
3. `poetry run pytest tests/unit/test_configuration.py -q`
4. 若依赖缺失：`poetry install` 后重试

**判定与恢复**
- 命令可正常启动且 health 可用视为恢复
- 若仍失败，优先回滚最近配置变更

---

## 2) MCP 异常

**症状**
- `initialize` 失败、`tools/list` 为空、`tools/call` 错误码异常

**SOP**
1. `poetry run pytest tests/unit/test_mcp_server.py -q`
2. 核对 `OWLCLAW_MCP_TOKEN`（服务端与客户端必须一致）
3. 最小链路验证：`initialize -> tools/list -> tools/call`
4. 检查 Skills 挂载目录是否存在可解析 `SKILL.md`

**判定与恢复**
- `initialize` 返回协议版本
- `tools/list` 包含预期能力
- `tools/call` 返回结构化响应且不泄露敏感信息

---

## 3) Webhook 异常

**症状**
- 回调未入站、入站后失败、重试不收敛

**SOP**
1. 核对 webhook 密钥/鉴权头与配置一致
2. `poetry run pytest tests/unit/triggers/test_webhook_http_gateway.py -q`
3. 检查请求体是否超限（413）与编码是否合法（UTF-8）
4. 确认事件查询入口受鉴权保护（`/events` 不应匿名可读）
5. 检查日志头脱敏（`authorization/x-api-key/x-admin-token`）

**快速止损**
- 队列拥塞时临时降级为更保守策略并记录事件 ID
- 保留原始请求 ID，便于重放与审计追踪

---

## 4) LLM 超时/不稳定

**症状**
- 响应显著变慢、timeout 升高、fallback 频繁

**SOP**
1. 检查 runtime 与 `integrations.llm` 超时配置
2. 执行回归：`poetry run pytest tests/unit/agent tests/unit/integrations -q`
3. 检查预算/限流/熔断是否被触发并导致级联失败
4. 验证 fallback 模型可用性与配额

**处置策略**
- 降低并发、缩小输入体积
- 启用更短超时 + 有界重试
- 错误信息保持脱敏，不回传 provider 原始异常

---

## 5) 复盘模板（故障后必填）

- 故障时间窗口：
- 影响范围：
- 触发条件：
- 根因：
- 临时处置：
- 永久修复：
- 新增回归测试：

---

## 6) Queue 租户签名密钥轮换（启用签名校验时）

**适用前提**
- `trust_tenant_header=true`
- 已配置 `tenant_signature_secret_env` 或 `tenant_signature_secret_envs`

**SOP**
1. 在密钥管理系统生成新密钥（禁止写入仓库）
2. 消费端先进入重叠窗口：`tenant_signature_secret_envs=[NEW_ENV,OLD_ENV]` 并滚动重启
3. 灰度更新生产者签名到新密钥，观察签名失败日志
4. 执行失败注入回归：`pwsh ./scripts/regression-failure-paths.ps1`
5. 稳定后移除旧密钥，收敛为 `tenant_signature_secret_env=NEW_ENV`（或仅保留 `tenant_signature_secret_envs=[NEW_ENV]`）

**回滚**
- 立即恢复旧密钥并重启生产者
- 不要关闭 tenant 签名校验（避免降级到无来源真实性）

