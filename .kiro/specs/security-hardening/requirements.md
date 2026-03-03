# security-hardening — 安全加固

> **来源**: 2026-03-03 全方位审计
> **优先级**: P0/P1（安全缺陷可导致数据泄露或系统被控制）

---

## 背景

审计发现多处安全薄弱环节：SKILL.md 注入、工具结果未消毒、Webhook 管理接口无鉴权、MCP 无认证、eval 使用等。

---

## REQ-S1：SKILL.md 内容注入系统提示前必须消毒

- **现状**：`knowledge.py:174` 直接注入 SKILL.md 全文，无任何过滤
- **风险**：恶意 SKILL.md 可注入 "ignore previous instructions" 等指令
- **验收**：SKILL.md 中的 prompt injection 模式被检测并移除/标记

## REQ-S2：工具调用结果回传 LLM 前必须消毒

- **现状**：`runtime.py:848` 直接 json.dumps(tool_result) 回传
- **风险**：恶意工具返回值可注入 LLM 指令
- **验收**：tool result 中的 injection 模式被消毒

## REQ-S3：工具调用参数传给 handler 前必须消毒

- **现状**：`runtime.py:881` LLM 输出直接传给 handler
- **风险**：LLM 幻觉可能生成恶意参数
- **验收**：handler 收到的参数经过 InputSanitizer

## REQ-S4：Webhook 管理接口必须鉴权

- **现状**：`webhook/http/app.py:226-306` POST/PUT/DELETE 无鉴权
- **风险**：任何人可创建/修改/删除 webhook
- **验收**：管理接口需要 API key 或 Bearer token

## REQ-S5：MCP Server 必须有认证层

- **现状**：`mcp/server.py` 使用 stdio，无认证
- **风险**：任何有进程访问权的人可调用所有工具
- **验收**：MCP 初始化时验证 token

## REQ-S6：Webhook transformer 禁用 eval

- **现状**：`webhook/transformer.py:210-218` 使用 ast.parse + eval
- **风险**：即使有 AST 白名单，eval 本质不安全
- **验收**：替换为安全表达式求值器

## REQ-S7：XML 解析防 XXE

- **现状**：`webhook/transformer.py:38` 使用 ElementTree.fromstring
- **风险**：XXE 攻击
- **验收**：使用 defusedxml 或禁用外部实体

## REQ-S8：Webhook 请求体大小限制

- **现状**：`webhook/http/app.py:123` 无限读取 request.body()
- **风险**：DoS 攻击
- **验收**：超过 1MB 返回 413

## REQ-S9：InputSanitizer 增加 Unicode 归一化

- **现状**：纯正则匹配，可被 Unicode 混淆绕过
- **风险**：注入绕过
- **验收**：输入先 NFKC 归一化再匹配

## REQ-S10：SecurityAuditLog 持久化

- **现状**：仅内存存储，重启丢失
- **验收**：支持文件/DB 后端

## REQ-S11：Console API 鉴权

- **现状**：`web/mount.py` 挂载无鉴权
- **验收**：Console API 需要 api_token

## REQ-S12：Webhook auth_token 存储哈希化

- **现状**：`webhook/persistence/models.py:27` 明文存储
- **验收**：存储 hash，运行时验证

## REQ-S13：CORS 配置修复

- **现状**：`allow_credentials=True` + `allow_origins=["*"]` 违反 CORS 规范
- **验收**：credentials 模式下使用显式 origin
