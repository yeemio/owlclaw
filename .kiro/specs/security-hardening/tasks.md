# security-hardening — 任务清单

> **审计来源**: 2026-03-03-deep-audit-report-v4.md
> **优先级**: P0 (阻塞发布)
> **最后更新**: 2026-03-04

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

---

## Phase 1：P0 安全漏洞（阻塞发布）

### Task 1：工具结果消毒（REQ-S2）【P0 - Finding #2】
> 工具输出未消毒直接注入 LLM 提示词，可导致 prompt injection
- [x] 1.1 `runtime.py` tool_result 回传前调用 `InputSanitizer.sanitize()`（通过 `_sanitize_tool_result()` 在 decision loop 消毒序列化结果）
- [x] 1.2 新增 `_sanitize_tool_result()` 方法
- [x] 1.3 单元测试：恶意 tool result 被消毒，无法注入 system prompt（`tests/unit/agent/test_runtime.py`）
- [x] 1.4 集成测试：HTTP binding 返回恶意数据时被拦截（`tests/integration/test_bindings_skills_loader_integration.py`）

### Task 2：工具参数 Schema 校验（REQ-S3）【P0 - Finding #3】
> LLM 生成的工具参数未校验，可传递任意值给 handler
- [x] 2.1 `runtime.py` 在 invoke 前调用 schema 验证（`_validate_tool_arguments()`）
- [x] 2.2 `_capability_schemas()` 读取 SKILL.md 的 `metadata.tools_schema`
- [x] 2.3 默认设置 `additionalProperties: false`，并按 `properties` 过滤 `required`
- [x] 2.4 单元测试：非法参数被拒绝，返回错误 dict（`tests/unit/agent/test_runtime.py`）
- [x] 2.5 集成测试：SSRF via URL 参数被 schema 校验拦截（`tests/integration/test_agent_runtime_e2e.py`）

### Task 3：CORS 安全修复（REQ-S13）【P0 - Finding #1, #4, #15】
> 多处 CORS 默认 `["*"]` + credentials，违反 CORS 规范
- [x] 3.1 `middleware.py` 验证 `*` 与 `allow_credentials=true` 不兼容（冲突时强制降级为 `false`）
- [x] 3.2 `parse_cors_origins()` 默认改为 `[]`
- [x] 3.3 `triggers/api/server.py` CORS 默认改为 `[]`
- [x] 3.4 **新增** `triggers/webhook/http/app.py` CORS 默认改为 `[]`
- [x] 3.5 添加启动时 CORS 配置校验警告（console middleware）
- [x] 3.6 单元测试：`*` + credentials 输出警告，默认闭合 CORS 已覆盖测试

---

## Phase 2：P1 安全加固

### Task 4：HTTP Executor SSRF 防护（REQ-S14）【P1 - Finding #5】
> URL 模板替换无 allowlist，可访问内网/云元数据
- [x] 4.1 `http_executor.py` 添加 URL allowlist 校验
- [x] 4.2 默认阻止私有 IP 段：`10.x`, `172.16-31.x`, `169.254.x`, `127.x`（含 loopback/link-local/private/reserved）
- [x] 4.3 配置化允许域名/IP 列表（`HTTPBindingConfig.allowed_hosts` + `allow_private_network`）
- [x] 4.4 单元/集成测试：SSRF 尝试被阻止（`test_bindings_http_executor*`）

### Task 5：Unicode 归一化（REQ-S9）【P1 - Finding #6】
> Sanitizer 可被 Unicode 同形字符绕过
- [x] 5.1 `sanitizer.py` 使用 `unicodedata.normalize('NFKC', text)`（已存在实现）
- [x] 5.2 单元测试：Unicode 混淆攻击被归一化后匹配（新增全角注入回归）

### Task 6：SKILL.md 注入防护（REQ-S1）
- [x] 6.1 `knowledge.py` 对 skill 内容调用 sanitizer（`get_skills_knowledge_report()`）
- [x] 6.2 单元测试：含 injection 的 SKILL.md 被消毒（`tests/unit/test_knowledge.py`）

---

## Phase 3：其他安全任务

### Task 7：Webhook 管理鉴权（REQ-S4）
- [x] 7.1 添加 admin token 中间件（未配置 token 时管理接口返回 500，已配置后强制校验）
- [x] 7.2 单元/集成测试：无 token 返回 401，未配置返回 500

### Task 8：MCP 认证（REQ-S5）
- [x] 8.1 `mcp/server.py` 添加 token 验证（初始化时 `OWLCLAW_MCP_TOKEN` + initialize token 握手）
- [x] 8.2 单元/集成测试通过（`tests/unit/test_mcp_server.py` + `tests/integration/test_mcp_server_integration.py`）

### Task 9：eval 替换（REQ-S6）
- [x] 9.1 transformer 使用 AST 安全解释器（`_safe_eval_ast`）替代 `eval`
- [x] 9.2 单元测试通过（`tests/unit/triggers/test_webhook_transformer.py`）

### Task 10：XXE 防护（REQ-S7）
- [x] 10.1 XML 解析使用 `defusedxml.ElementTree.fromstring`
- [x] 10.2 `defusedxml` 依赖已存在（`pyproject.toml`）并有 XXE 用例覆盖

### Task 11：请求体限制（REQ-S8）
- [x] 11.1 添加 max_content_length 中间件（header + body 双路径限制）
- [x] 11.2 单元测试：超大请求返回 413（webhook gateway 覆盖）

### Task 12：SecurityAuditLog 持久化（REQ-S10）
- [ ] 12.1 实现 FileSecurityAuditBackend
- [ ] 12.2 配置选择后端
- [ ] 12.3 单元测试

### Task 13：Console API 鉴权（REQ-S11）
- [ ] 13.1 添加 api_token 中间件
- [ ] 13.2 单元测试

### Task 14：auth_token 哈希存储（REQ-S12）
- [ ] 14.1 模型改用 hash 字段
- [ ] 14.2 验证逻辑改用 hash 比较
- [ ] 14.3 迁移脚本

---

## Task 15：回归测试
- [ ] 15.1 全量 pytest 通过
- [ ] 15.2 安全相关测试覆盖所有 P0/P1 finding
