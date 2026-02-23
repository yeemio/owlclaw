# Cron Triggers Guide

## API Reference

### `@app.cron(...)`

Registers a cron trigger and optional fallback handler.

```python
@app.cron(
    "0 * * * *",
    event_name="hourly_inventory",
    focus="inventory",
    max_daily_runs=24,
    cooldown_seconds=60,
    retry_on_failure=True,
    max_retries=3,
)
async def fallback_inventory_job():
    return {"status": "fallback_done"}
```

Arguments:

- `expression`: 5-field cron expression.
- `event_name`: optional unique name, defaults to function name.
- `focus`: optional skill focus tag.
- `description`: optional human-readable description.
- `fallback`: optional explicit fallback callable.
- `**kwargs`: `CronTriggerConfig` fields (`max_daily_runs`, `max_daily_cost`, `cooldown_seconds`, `retry_on_failure`, `max_retries`, `priority`, etc.).

### `CronTriggerRegistry` public methods

- `register(event_name, expression, focus=None, fallback_handler=None, **kwargs)`
- `get_trigger(event_name)`
- `list_triggers()`
- `start(hatchet_client, agent_runtime=None, ledger=None, tenant_id="default")`
- `pause_trigger(event_name)`
- `resume_trigger(event_name)`
- `trigger_now(event_name, **kwargs)`
- `get_trigger_status(event_name)`
- `get_execution_history(event_name, limit=10, tenant_id=None)`
- `get_health_status()`
- `wait_for_all_tasks(timeout_seconds=10.0)`
- `apply_settings(settings)` (applies `config.triggers` defaults to future registrations)

## Configuration

`owlclaw.yaml`:

```yaml
triggers:
  cron:
    enabled: true
    max_concurrent: 20
    default_timeout_seconds: 300
  governance:
    max_daily_runs: 48
    max_daily_cost: 20.0
    cooldown_seconds: 60
  retry:
    retry_on_failure: true
    max_retries: 3
    retry_delay_seconds: 60
  notifications:
    enabled: true
    channels: ["slack"]

integrations:
  hatchet:
    server_url: "http://localhost:7077"
    api_token: "${HATCHET_API_TOKEN}"
    namespace: "default"
```

Environment variable equivalents:

- `OWLCLAW_TRIGGERS__CRON__ENABLED`
- `OWLCLAW_TRIGGERS__CRON__MAX_CONCURRENT`
- `OWLCLAW_TRIGGERS__GOVERNANCE__MAX_DAILY_RUNS`
- `OWLCLAW_TRIGGERS__RETRY__MAX_RETRIES`
- `OWLCLAW_TRIGGERS__NOTIFICATIONS__ENABLED`
- `OWLCLAW_INTEGRATIONS__HATCHET__SERVER_URL`
- `OWLCLAW_INTEGRATIONS__HATCHET__API_TOKEN`

Priority: runtime overrides > environment variables > YAML > model defaults.

## Deployment

Docker Compose:

```bash
docker compose -f deploy/docker-compose.cron.yml up -d
```

Kubernetes:

```bash
kubectl apply -f deploy/k8s/cron-deployment.yaml
kubectl apply -f deploy/k8s/cron-service.yaml
```

## Migration Guide

1. Inventory existing cron jobs and classify by risk/cost.
2. Register each job with `@app.cron`, keep old job as fallback initially (`migration_weight < 1.0`).
3. Enable governance limits (`max_daily_runs`, `max_daily_cost`, `cooldown_seconds`).
4. Monitor execution history and success rate.
5. Increase `migration_weight` to 1.0 and remove legacy crontab entries.

Migration checklist:

- [ ] cron expression validated
- [ ] fallback strategy decided
- [ ] governance limits configured
- [ ] manual trigger tested (`trigger_now`)
- [ ] pause/resume verified

## Troubleshooting

### Trigger not firing

- Check registration: `app.cron_registry.list_triggers()`
- Check expression validity.
- Check trigger enabled state via `get_trigger_status()`.

### Trigger keeps being skipped

- Inspect governance reason in logs (`cron_governance_skip`).
- Verify cooldown, daily run, and daily cost thresholds.

### Manual trigger fails

- Ensure `app.start(..., hatchet_client=...)` was called.
- Ensure Hatchet client supports `run_task_now`.

### Health degraded

- `app.health_status()` and `app.cron_registry.get_health_status()`
- Validate Hatchet connectivity and open circuit breaker count.
