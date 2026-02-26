# Java Golden Path

Last updated: 2026-02-26

## Goal

Provide a low-friction Java and curl integration path for protocol validation.

## Prerequisites

1. JDK 17
2. Maven 3.9+
3. Reachable gateway endpoint
4. Optional API token (`OWLCLAW_API_TOKEN`)

## Java Baseline

Project location:

`examples/cross_lang/java`

Quick compile check:

```bash
cd examples/cross_lang/java
mvn -q -DskipTests package
```

## curl Baseline

Scripts:

1. `scripts/cross_lang/trigger_agent.sh`
2. `scripts/cross_lang/query_status.sh`
3. `scripts/cross_lang/error_scenario.sh`

Example:

```bash
export OWLCLAW_GATEWAY_BASE_URL=http://localhost:8000
./scripts/cross_lang/trigger_agent.sh
```

## Scenario Mapping

| Scenario | Java | curl |
|---|---|---|
| Trigger agent | `GatewayClient` (project baseline) | `trigger_agent.sh` |
| Query status | extend baseline client | `query_status.sh` |
| Error contract | baseline plus invalid request case | `error_scenario.sh` |

## Verification

Use:

`scripts/verify_cross_lang.ps1`

The script validates the presence of required Java and curl artifacts.
