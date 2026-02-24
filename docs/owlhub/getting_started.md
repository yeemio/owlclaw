# OwlHub Getting Started

## 1. Build and Run API (Docker)

```bash
docker compose -f deploy/docker-compose.owlhub-api.yml up -d --build
```

## 2. Health Check

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## 3. Search and Install from Local Index

```bash
owlclaw skill search --index-url ./index.json --query monitor
owlclaw skill install entry-monitor --index-url ./index.json
owlclaw skill installed
```

## 4. Search and Publish in API Mode

```bash
owlclaw skill search --mode api --api-base-url http://localhost:8000 --query monitor
owlclaw skill publish ./my-skill --mode api --api-base-url http://localhost:8000 --api-token <token>
```
