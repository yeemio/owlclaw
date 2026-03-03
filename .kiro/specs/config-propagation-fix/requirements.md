# config-propagation-fix — 配置传播链路修复

> **来源**: 2026-03-03 全方位审计
> **优先级**: P0（配置不生效导致核心功能失效）

---

## 背景

配置从 `app.configure()` 到 `AgentRuntime` 到 `LLM 调用` 的传播链路存在多处断裂，导致用户配置的 model、mock_mode 等关键参数不生效。

---

## REQ-CP1：LLMIntegrationConfig 必须包含 mock_mode/mock_responses 字段

- **现状**：`config/models.py` 的 `LLMIntegrationConfig` 缺少这两个字段，Pydantic `extra="ignore"` 直接丢弃
- **验收**：`OwlClaw.lite()` 配置的 mock_mode 在 `self._config` 中可见

## REQ-CP2：create_agent_runtime() 必须传递 LLM 配置到 Runtime

- **现状**：`app.py:970` 创建 Runtime 时不传 model/config
- **验收**：`app.configure(model="deepseek/deepseek-chat")` 后 `runtime.model == "deepseek/deepseek-chat"`

## REQ-CP3：Router default_model 必须从 integrations.llm.model 派生

- **现状**：Router 硬编码 `default_model="gpt-4o-mini"`，与 app config 脱节
- **验收**：配置 `model="deepseek/deepseek-chat"` 后 Router 默认也用 deepseek

## REQ-CP4：Router 对未配置 task_type 返回 None

- **现状**：返回 default_model，静默覆盖用户配置
- **验收**：无路由规则时 Runtime 使用 self.model

## REQ-CP5：ConfigManager 优先级必须明确且正确

- **现状**：merge 顺序可能让 YAML/ENV 覆盖 `configure()` 传入的值
- **验收**：`configure()` > ENV > YAML > 默认值

## REQ-CP6：configure() 不得在 start() 之后调用

- **现状**：无保护，调用后不影响已启动组件
- **验收**：start() 后调用 configure() 抛出 RuntimeError

## REQ-CP7：DEFAULT_RUNTIME_CONFIG 的 model 应从 app config 派生

- **现状**：硬编码 `gpt-4o-mini`，与 app config 脱节
- **验收**：Runtime 默认 model 来自 app 配置
