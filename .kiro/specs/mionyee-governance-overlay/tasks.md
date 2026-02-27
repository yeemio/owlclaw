# Mionyee 治理叠加 — 任务清单

> **Spec**: mionyee-governance-overlay
> **阶段**: Phase 8.1
> **前置**: governance ✅, integrations-llm ✅

---

## Task 0：Spec 文档与契约

- [ ] 0.1 requirements.md / design.md / tasks.md 三层齐全
- [ ] 0.2 与 SPEC_TASKS_SCAN.md Phase 8.1 对齐

## Task 1：GovernanceProxy 核心

- [ ] 1.1 实现 `owlclaw.governance.proxy.GovernanceProxy` 类
  - 文件：`owlclaw/governance/proxy.py`
  - 接口：`async acompletion(model, messages, caller, **kwargs) -> dict`
  - 内部调用链：budget_check → rate_limit_check → circuit_breaker_check → litellm.acompletion → ledger_record
- [ ] 1.2 实现 `GovernanceProxy.from_config(path)` 工厂方法
  - 从 owlclaw.yaml 加载治理配置
  - 复用 `owlclaw.config` 统一配置系统
- [ ] 1.3 实现降级模式（passthrough）
  - 治理层异常时直通 litellm，不阻塞业务
  - 记录降级事件到本地日志
- [ ] 1.4 单元测试：GovernanceProxy 的预算/限流/熔断/降级逻辑
  - 文件：`tests/unit/governance/test_proxy.py`
  - 覆盖：正常调用、预算拦截、限流拒绝、熔断触发、降级直通

## Task 2：Mionyee 接入胶水

- [ ] 2.1 在 Mionyee 的 LLM 调用入口替换为 GovernanceProxy
  - 目标文件：`mionyee/mionyee/ai/client.py`（或等效入口）
  - 改动量：5-10 行
- [ ] 2.2 编写 Mionyee 侧的 owlclaw.yaml 配置
  - 预算上限、限流 QPS、熔断阈值
- [ ] 2.3 集成测试：Mionyee LLM 调用经过治理代理
  - 文件：`tests/integration/test_mionyee_governance.py`
  - 验证：预算拦截、限流、熔断、审计记录

## Task 3：Ledger 审计查询

- [ ] 3.1 确认 Ledger 已有能力满足审计需求（复用 governance spec 实现）
- [ ] 3.2 补充 CLI 查询命令（如需）：`owlclaw ledger query --caller mionyee.*`
- [ ] 3.3 验收：所有 LLM 调用/拦截事件可通过 CLI 查询

## Task 4：性能验证

- [ ] 4.1 治理判定延迟基准测试：p99 < 10ms
- [ ] 4.2 端到端验收：预算拦截 100%、限流生效、熔断生效、审计完整
