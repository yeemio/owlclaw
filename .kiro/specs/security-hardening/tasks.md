# security-hardening — 任务清单

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

## Task 1：SKILL.md 注入防护（REQ-S1）
- [x] 1.1 `knowledge.py` 对 skill 内容调用 sanitizer
- [x] 1.2 单元测试：含 injection 的 SKILL.md 被消毒

## Task 2：工具结果消毒（REQ-S2）
- [x] 2.1 `runtime.py` tool_result 回传前消毒
- [x] 2.2 单元测试：恶意 tool result 被消毒

## Task 3：工具参数消毒（REQ-S3）
- [x] 3.1 `runtime.py` _execute_tool 参数消毒
- [x] 3.2 单元测试

## Task 4：Webhook 管理鉴权（REQ-S4）
- [x] 4.1 添加 admin token 中间件
- [x] 4.2 单元测试：无 token 返回 401

## Task 5：MCP 认证（REQ-S5）
- [x] 5.1 `mcp/server.py` 添加 token 验证
- [x] 5.2 单元测试

## Task 6：eval 替换（REQ-S6）
- [x] 6.1 替换 transformer.py 中的 eval
- [x] 6.2 单元测试

## Task 7：XXE 防护（REQ-S7）
- [x] 7.1 替换为 defusedxml
- [x] 7.2 添加 defusedxml 依赖

## Task 8：请求体限制（REQ-S8）
- [x] 8.1 添加 max_content_length 中间件
- [x] 8.2 单元测试：超大请求返回 413

## Task 9：Unicode 归一化（REQ-S9）
- [x] 9.1 sanitizer.py 添加 NFKC 归一化
- [x] 9.2 单元测试：Unicode 混淆被归一化

## Task 10：SecurityAuditLog 持久化（REQ-S10）
- [x] 10.1 实现 FileSecurityAuditBackend
- [x] 10.2 配置选择后端
- [x] 10.3 单元测试

## Task 11：Console API 鉴权（REQ-S11）
- [x] 11.1 添加 api_token 中间件
- [x] 11.2 单元测试

## Task 12：auth_token 哈希存储（REQ-S12）
- [x] 12.1 模型改用 hash 字段
- [x] 12.2 验证逻辑改用 hash 比较（仅 hash 校验，不再走明文 token 分支）
- [x] 12.3 迁移脚本

## Task 13：CORS 修复（REQ-S13）
- [x] 13.1 修复 parse_cors_origins 默认值
- [x] 13.2 修复 api trigger server CORS
- [x] 13.3 单元测试

## Task 14：回归测试
- [x] 14.1 全量 pytest 通过
