# OwlClaw Java Golden Path (Baseline)

## Prerequisites

- JDK 17
- Maven 3.9+

## Build

```bash
mvn -q -DskipTests package
```

## Core Flows Included

- trigger call via `POST /v1/agent/trigger`
- status query via `GET /v1/agent/status/{run_id}`

