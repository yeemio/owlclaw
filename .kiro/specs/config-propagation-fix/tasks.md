# config-propagation-fix — 任务清单

---

## Task 0：Spec 文档 ✅
- [x] 0.1 requirements.md ✅
- [x] 0.2 design.md ✅
- [x] 0.3 tasks.md ✅

## Task 1：LLMIntegrationConfig 补字段（REQ-CP1）
- [x] 1.1 `config/models.py` 添加 `mock_mode: bool` 和 `mock_responses: dict`
- [x] 1.2 单元测试：验证 lite() 配置的 mock_mode 在 _config 中可见

## Task 2：create_agent_runtime() 传递配置（REQ-CP2）
- [x] 2.1 `app.py` create_agent_runtime() 读取 llm config 传递 model
- [x] 2.2 单元测试：configure(model=X) 后 runtime.model == X

## Task 3：Router default_model 派生（REQ-CP3）
- [x] 3.1 `governance/router.py` 接受 default_model 参数
- [x] 3.2 `app.py` _ensure_governance() 传入 llm model
- [x] 3.3 单元测试：Router 使用 app 配置的 model

## Task 4：Router 返回 None（REQ-CP4）
- [x] 4.1 `router.py` select_model() 未配置时返回 None
- [x] 4.2 `runtime.py` 处理 Router 返回 None
- [x] 4.3 单元测试：无路由规则时 Runtime 保持 self.model

## Task 5：ConfigManager 优先级（REQ-CP5）
- [x] 5.1 确认/调整 merge 顺序
- [x] 5.2 文档化优先级

## Task 6：configure() 防护（REQ-CP6）
- [x] 6.1 `app.py` configure() 检查 _runtime
- [x] 6.2 单元测试

## Task 7：DEFAULT_RUNTIME_CONFIG 清理（REQ-CP7）
- [x] 7.1 移除硬编码 model
- [x] 7.2 单元测试

## Task 8：回归测试
- [x] 8.1 全量 pytest 通过
- [ ] 8.2 真实 LLM 端到端验证
