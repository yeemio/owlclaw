# 认证配置指南

`triggers.api.auth_type` 支持：

- `none`：不启用认证（仅内网调试）
- `api_key`：校验 `X-API-Key`
- `bearer`：校验 `Authorization: Bearer <token>`

示例：

```yaml
triggers:
  api:
    auth_type: api_key
    api_keys:
      - ${OWLCLAW_API_KEY}
```

```yaml
triggers:
  api:
    auth_type: bearer
    bearer_tokens:
      - ${OWLCLAW_BEARER_TOKEN}
```

认证失败统一返回 `401`。
