# API 端点注册指南

## 装饰器风格

```python
from owlclaw import OwlClaw

app = OwlClaw("my-agent")
app.configure(
    triggers={
        "api": {
            "auth_type": "api_key",
            "api_keys": ["dev-key"],
            "host": "0.0.0.0",
            "port": 8080,
        }
    }
)

@app.api(path="/api/v1/analysis", method="POST", response_mode="sync")
async def fallback(payload: dict) -> dict:
    return {"fallback": True, "payload": payload}
```

## 函数调用风格

```python
from owlclaw.triggers import api_call

app.trigger(api_call(
    path="/api/v1/order",
    method="POST",
    event_name="order_request",
    response_mode="async",
))
```

## 生命周期

- `await app.start(...)` 会启动 API trigger server（若已注册端点）
- `await app.stop()` 会停止 server
