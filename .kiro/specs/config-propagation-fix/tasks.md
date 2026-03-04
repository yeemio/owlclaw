# config-propagation-fix — 任务清单

> **审计来源**: 2026-03-03-deep-audit-report-v4.md
> **优先级**: P1 (生产环境安全)
> **最后更新**: 2026-03-03

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

---

## Phase 1：P1 认证问题（审计发现）

### Task 1：Auth 中间件空 Token 绕过【P1 - Finding #7】
> 当 OWLCLAW_CONSOLE_TOKEN 为空时，请求直接放行，无警告
- [ ] 1.1 `middleware.py:42-44` 添加 `OWLCLAW_REQUIRE_AUTH=true` 环境变量支持
- [ ] 1.2 当 `REQUIRE_AUTH=true` 且 token 为空时返回 500 "auth not configured"
- [ ] 1.3 启动时日志警告 token 为空的情况
- [ ] 1.4 单元测试：空 token + REQUIRE_AUTH=true 返回 500

---

## Phase 2：配置传播修复

### Task 2：LLMIntegrationConfig 补字段（REQ-CP1）
- [ ] 2.1 `config/models.py` 添加 `mock_mode: bool` 和 `mock_responses: dict`
- [ ] 2.2 单元测试：验证 lite() 配置的 mock_mode 在 _config 中可见

### Task 3：create_agent_runtime() 传递配置（REQ-CP2）
- [ ] 3.1 `app.py` create_agent_runtime() 读取 llm config 传递 model
- [ ] 3.2 单元测试：configure(model=X) 后 runtime.model == X

### Task 4：Router default_model 派生（REQ-CP3）
- [ ] 4.1 `governance/router.py` 接受 default_model 参数
- [ ] 4.2 `app.py` _ensure_governance() 传入 llm model
- [ ] 4.3 单元测试：Router 使用 app 配置的 model

### Task 5：Router 返回 None（REQ-CP4）
- [ ] 5.1 `router.py` select_model() 未配置时返回 None
- [ ] 5.2 `runtime.py` 处理 Router 返回 None
- [ ] 5.3 单元测试：无路由规则时 Runtime 保持 self.model

### Task 6：ConfigManager 优先级（REQ-CP5）
- [ ] 6.1 确认/调整 merge 顺序
- [ ] 6.2 文档化优先级

### Task 7：configure() 防护（REQ-CP6）
- [ ] 7.1 `app.py` configure() 检查 _runtime
- [ ] 7.2 单元测试

### Task 8：DEFAULT_RUNTIME_CONFIG 清理（REQ-CP7）
- [ ] 8.1 移除硬编码 model
- [ ] 8.2 单元测试

---

## Task 9：回归测试
- [ ] 9.1 全量 pytest 通过
- [ ] 9.2 真实 LLM 端到端验证
