# security-hardening — 任务清单

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

## Task 1：SKILL.md 注入防护（REQ-S1）
- [ ] 1.1 `knowledge.py` 对 skill 内容调用 sanitizer
- [ ] 1.2 单元测试：含 injection 的 SKILL.md 被消毒

## Task 2：工具结果消毒（REQ-S2）
- [ ] 2.1 `runtime.py` tool_result 回传前消毒
- [ ] 2.2 单元测试：恶意 tool result 被消毒

## Task 3：工具参数消毒（REQ-S3）
- [ ] 3.1 `runtime.py` _execute_tool 参数消毒
- [ ] 3.2 单元测试

## Task 4：Webhook 管理鉴权（REQ-S4）
- [ ] 4.1 添加 admin token 中间件
- [ ] 4.2 单元测试：无 token 返回 401

## Task 5：MCP 认证（REQ-S5）
- [ ] 5.1 `mcp/server.py` 添加 token 验证
- [ ] 5.2 单元测试

## Task 6：eval 替换（REQ-S6）
- [ ] 6.1 替换 transformer.py 中的 eval
- [ ] 6.2 单元测试

## Task 7：XXE 防护（REQ-S7）
- [ ] 7.1 替换为 defusedxml
- [ ] 7.2 添加 defusedxml 依赖

## Task 8：请求体限制（REQ-S8）
- [ ] 8.1 添加 max_content_length 中间件
- [ ] 8.2 单元测试：超大请求返回 413

## Task 9：Unicode 归一化（REQ-S9）
- [ ] 9.1 sanitizer.py 添加 NFKC 归一化
- [ ] 9.2 单元测试：Unicode 混淆被归一化

## Task 10：SecurityAuditLog 持久化（REQ-S10）
- [ ] 10.1 实现 FileSecurityAuditBackend
- [ ] 10.2 配置选择后端
- [ ] 10.3 单元测试

## Task 11：Console API 鉴权（REQ-S11）
- [ ] 11.1 添加 api_token 中间件
- [ ] 11.2 单元测试

## Task 12：auth_token 哈希存储（REQ-S12）
- [ ] 12.1 模型改用 hash 字段
- [ ] 12.2 验证逻辑改用 hash 比较
- [ ] 12.3 迁移脚本

## Task 13：CORS 修复（REQ-S13）
- [ ] 13.1 修复 parse_cors_origins 默认值
- [ ] 13.2 修复 api trigger server CORS
- [ ] 13.3 单元测试

## Task 14：回归测试
- [ ] 14.1 全量 pytest 通过
