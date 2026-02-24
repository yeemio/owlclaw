# Webhook Deployment Guide

## Runtime Requirements

- Python `>=3.10`
- Poetry environment
- PostgreSQL (for production persistence mode)

## Environment Variables

- `OWLCLAW_WEBHOOK_TIMEOUT_SECONDS`
- `OWLCLAW_WEBHOOK_MAX_RETRIES`
- `OWLCLAW_WEBHOOK_LOG_LEVEL`

## Database Migration

Run webhook migration through project migration flow:

```powershell
poetry run owlclaw db migrate
```

Webhook tables are introduced by migration `004_webhook`.

## Docker Build (Example)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install poetry && poetry install --only main
CMD ["poetry", "run", "python", "-m", "owlclaw"]
```

## Kubernetes Deployment (Example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: owlclaw-webhook
spec:
  replicas: 2
  selector:
    matchLabels:
      app: owlclaw-webhook
  template:
    metadata:
      labels:
        app: owlclaw-webhook
    spec:
      containers:
      - name: webhook
        image: owlclaw:latest
        ports:
        - containerPort: 8000
        env:
        - name: OWLCLAW_WEBHOOK_TIMEOUT_SECONDS
          value: "30"
        - name: OWLCLAW_WEBHOOK_MAX_RETRIES
          value: "3"
```
