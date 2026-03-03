# config-propagation-fix — 设计文档

> **来源**: `requirements.md` REQ-CP1 ~ REQ-CP7

---

## 设计方案

### D-CP1：LLMIntegrationConfig 补字段

在 `owlclaw/config/models.py` 的 `LLMIntegrationConfig` 中添加：
```python
mock_mode: bool = False
mock_responses: dict[str, Any] = Field(default_factory=dict)
```

### D-CP2：create_agent_runtime() 传递配置

从 `self._config["integrations"]["llm"]` 读取 model 并传递：
```python
llm_cfg = self._config.get("integrations", {}).get("llm", {})
model = llm_cfg.get("model", "gpt-4o-mini")
return AgentRuntime(..., model=model, config={"llm": llm_cfg})
```

### D-CP3：Router default_model 从 app config 派生

`_ensure_governance()` 创建 Router 时传入 `integrations.llm.model`：
```python
llm_model = self._config.get("integrations", {}).get("llm", {}).get("model", "gpt-4o-mini")
self._router = Router(router_cfg, default_model=llm_model)
```

### D-CP4：Router 返回 None

`select_model()` 对未配置 task_type 返回 None 而非 default_model。

### D-CP5：ConfigManager 优先级

调整 `_deep_merge` 顺序确保 runtime overrides 最后应用。

### D-CP6：configure() 防护

`configure()` 开头检查 `self._runtime is not None`。

### D-CP7：DEFAULT_RUNTIME_CONFIG 不硬编码 model

移除 `DEFAULT_RUNTIME_CONFIG` 中的 `model` 字段，由 app 传入。

---

## 影响文件

| 文件 | 修改 |
|------|------|
| `owlclaw/config/models.py` | 添加 mock 字段 |
| `owlclaw/app.py` | create_agent_runtime + configure 防护 |
| `owlclaw/governance/router.py` | default_model 参数化 + 返回 None |
| `owlclaw/agent/runtime/config.py` | 移除硬编码 model |
| `owlclaw/config/manager.py` | 优先级文档化 |
