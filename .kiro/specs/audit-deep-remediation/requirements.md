# audit-deep-remediation — 深度审计修复

> **来源**: `docs/review/DEEP_AUDIT_REPORT.md`（2026-03-05 四维度深度审计）
> **目标**: 收口 2 个 P1 + 4 个 Low 发现，满足 SHIP WITH CONDITIONS
> **优先级**: P1（2 项）+ Low（4 项）
> **预估工作量**: 2-3 天

---

## 1. 背景与动机

### 1.1 当前问题
- 深度审计报告产出 6 项发现：2 个 P1（Skill 环境变量注入无边界、Console tenant_id 客户端可控）、4 个 Low（缓存策略、Heartbeat 耦合、LLM 错误信息泄露风险、engine 异常映射）。
- 上述问题尚未纳入可执行任务清单与分配。

### 1.2 设计目标
- 将报告中的每项发现转化为可验收的 task，并按 worktree 边界分配。
- P1 在发布前或发布后首轮迭代修复；Low 按推荐顺序排期。

---

## 2. 功能需求

### 2.1 P1-1：Skill 环境变量注入安全边界
- **问题**：`owlclaw_config.env` 的 key 直接写入 `os.environ`，无 allowlist/前缀，恶意或错误 skill 可影响进程。
- **需求**：仅允许符合安全边界的 key 注入（前缀 `OWLCLAW_SKILL_` 或显式 allowlist）；其余忽略并可选日志。

### 2.2 P1-2：Console tenant_id 多租户指导与可选加固
- **问题**：`x-owlclaw-tenant` 由客户端提供且无服务端校验，多租户场景下存在越权风险。
- **需求**：文档明确当前行为适用于「tenant 为非安全标签」的自托管场景；多租户部署时须从认证上下文推导 tenant_id；可选：在 deps 中支持从 session/JWT 读取 tenant 并覆盖 header。

### 2.3 Low-3：Runtime 缓存 LRU 策略
- **问题**：可见工具与 skills 上下文缓存为简单 dict，逐出任意。
- **需求**：改为 LRU（或等价策略），逐出最近最少使用项。

### 2.4 Low-4：Heartbeat 与 Ledger 解耦
- **问题**：HeartbeatChecker 通过 `getattr(ledger, "_session_factory")` 依赖 Ledger 私有实现。
- **需求**：Ledger 暴露只读 session 工厂接口；Heartbeat 通过该接口或配置注入获取，不再访问私有属性。

### 2.5 Low-5：LLM 失败时错误信息脱敏
- **问题**：异常消息 `str(exc)` 直接追加到对话，存在潜在敏感信息泄露。
- **需求**：追加前脱敏或使用通用文案（如 "LLM call failed"），避免原始异常内容进入 LLM 上下文。

### 2.6 Low-6：db/engine 异常映射收窄
- **问题**：非 ConfigurationError 的异常被统一映射为连接/认证错误，误导排查。
- **需求**：仅将连接/认证类异常映射；其余保留原类型或包装为通用 EngineError。

### 2.7 Low-7（Phase 2）：capabilities provider 无 DB 不 500
- **问题**：DefaultCapabilitiesProvider._collect_capability_stats 未捕获 ConfigurationError，无 DB 时 GET /capabilities 返回 500，与 /ledger、/triggers 行为不一致。
- **需求**：捕获 ConfigurationError，返回空 stats，使 list_capabilities 返回 200 + items（零统计）。

### 2.8 Low-8（Phase 2）：health_status 不依赖私有属性
- **问题**：app.py health_status() 读取 db_change_manager._states、api_trigger_server._configs，内部实现变更易断裂。
- **需求**：改为公开 API 或只读属性，或在文档中明确该耦合。

### 2.9 Low-9（Phase 3）：Ledger 异常时 batch 不丢失
- **问题**：_background_writer 在捕获到非 Timeout/Cancelled 的 Exception 时仅打日志，当前 batch 未写入 DB 或 fallback，已出队记录可丢失。
- **需求**：在 except Exception 分支中将当前 batch 写入 fallback 再继续循环。

### 2.10 Low-10（Phase 3）：Ledger 写队列有界
- **问题**：_write_queue 无 maxsize，持续高负载下队列与内存可无限增长。
- **需求**：设 maxsize 或背压（put 超时/丢弃策略），并文档化上限。

### 2.11 Low-11（Phase 3）：Webhook 非 UTF-8 body 返回 400
- **问题**：receive_webhook 中 raw_body_bytes.decode("utf-8") 未捕获 UnicodeDecodeError，非 UTF-8 请求体导致 500。
- **需求**：捕获 UnicodeDecodeError，返回 400 及明确提示（如 "Request body must be UTF-8"）。

---

## 3. 验收标准（DoD）

- [ ] P1-1：技能仅能设置带 `OWLCLAW_SKILL_` 前缀或 allowlist 中的 env；有单测或集成验证。
- [ ] P1-2：文档已更新（Console/多租户）；若实现「从 auth 推导」则 deps 有测试。
- [ ] Low-3：缓存使用 LRU 或等效实现；行为可测。
- [ ] Low-4：Ledger 有公开 API；Heartbeat 无 `_session_factory` 引用。
- [ ] Low-5：LLM 失败分支不向消息追加原始 exc 字符串。
- [ ] Low-6：engine 仅对连接/认证类异常做映射；其他异常类型不变或 EngineError。
- [ ] Low-7：无 DB 时 GET /capabilities 返回 200 + 空/零统计；有单测或手验。
- [ ] Low-8：health_status 无私有属性访问或文档注明；health 相关测试通过。
- [ ] Low-9：Ledger 异常路径将当前 batch 写 fallback；有单测或集成验证。
- [ ] Low-10：Ledger 队列有界或背压；文档化上限。
- [ ] Low-11：Webhook 非 UTF-8 body 返回 400；有单测或手验。
