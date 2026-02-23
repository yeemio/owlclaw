# OwlClaw 安全配置说明

## 配置入口

安全配置统一位于 `owlclaw.yaml` 的 `security` 段：

```yaml
security:
  sanitizer:
    enabled: true
    custom_rules: []
  risk_gate:
    enabled: true
    confirmation_timeout_seconds: 300
    default_risk_level: low
  data_masker:
    enabled: true
    rules: []
```

## 各配置项说明

### `security.sanitizer`

- `enabled`: 是否启用输入净化
- `custom_rules`: 自定义净化规则列表（正则 + 动作）

### `security.risk_gate`

- `enabled`: 是否启用风险门控
- `confirmation_timeout_seconds`: 高风险操作确认超时时间
- `default_risk_level`: 默认风险级别（建议 `low`）

### `security.data_masker`

- `enabled`: 是否启用输出脱敏
- `rules`: 自定义脱敏规则（字段匹配与掩码策略）

## 审计日志

安全审计事件由 `SecurityAuditLog` 统一记录，覆盖：

- `sanitization`（输入净化触发）
- `risk gate`（执行、暂停、确认、拒绝、超时）
- `data masking`（发生脱敏时）

## 环境变量覆盖示例

- `OWLCLAW_SECURITY__SANITIZER__ENABLED=false`
- `OWLCLAW_SECURITY__RISK_GATE__CONFIRMATION_TIMEOUT_SECONDS=120`

## 热更新说明

`security.*` 属于热更新白名单，执行：

```bash
owlclaw reload
```

后可即时生效，并在输出中查看 `applied/skipped` 报告。

