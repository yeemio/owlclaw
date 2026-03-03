# security-hardening — 设计文档

> **来源**: `requirements.md` REQ-S1 ~ REQ-S13

---

## D-S1：SKILL.md 消毒

在 `KnowledgeInjector.get_skills_knowledge_report()` 中，对 `skill.load_full_content()` 返回值调用 `InputSanitizer.sanitize(content, source="skill")`。

## D-S2：工具结果消毒

在 `runtime.py` `_decision_loop` 中，tool_result 回传前调用 `_input_sanitizer.sanitize(json.dumps(result), source="tool_result")`。

## D-S3：工具参数消毒

在 `_execute_tool()` 中，对 LLM 生成的 arguments 调用 `_input_sanitizer.sanitize()`。

## D-S4：Webhook 管理鉴权

在 `webhook/http/app.py` 的管理路由上添加 `Depends(require_admin_token)` 中间件。

## D-S5：MCP 认证

在 `mcp/server.py` 初始化时读取 `OWLCLAW_MCP_TOKEN` 环境变量，首次请求验证。

## D-S6：替换 eval

使用 `simpleeval` 库或自定义 AST 解释器替换 `eval()`。

## D-S7：defusedxml

替换 `ElementTree.fromstring` 为 `defusedxml.ElementTree.fromstring`。

## D-S8：请求体限制

在 Webhook HTTP app 中添加 `max_content_length` 中间件。

## D-S9：Unicode 归一化

在 `InputSanitizer.sanitize()` 开头添加 `unicodedata.normalize("NFKC", text)`。

## D-S10：SecurityAuditLog 持久化

添加 `FileSecurityAuditBackend` 和 `DBSecurityAuditBackend`，通过配置选择。

## D-S11：Console API 鉴权

在 `create_api_app()` 中添加 `api_token` 中间件。

## D-S12：auth_token 哈希

使用 `hashlib.sha256` 存储，验证时比较 hash。

## D-S13：CORS 修复

`parse_cors_origins` 空值时返回 `["http://localhost:3000"]` 而非 `["*"]`。

---

## 影响文件

| 文件 | 修改 |
|------|------|
| `owlclaw/capabilities/knowledge.py` | SKILL 消毒 |
| `owlclaw/agent/runtime/runtime.py` | 工具结果/参数消毒 |
| `owlclaw/triggers/webhook/http/app.py` | 鉴权 + 体积限制 |
| `owlclaw/triggers/webhook/transformer.py` | eval 替换 + XXE |
| `owlclaw/mcp/server.py` | MCP 认证 |
| `owlclaw/security/sanitizer.py` | Unicode 归一化 |
| `owlclaw/security/audit.py` | 持久化后端 |
| `owlclaw/web/mount.py` | Console 鉴权 |
| `owlclaw/web/api/middleware.py` | CORS 修复 |
| `owlclaw/triggers/webhook/persistence/models.py` | hash 存储 |
