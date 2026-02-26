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

Run scenario examples:

```bash
export OWLCLAW_GATEWAY_BASE_URL=http://localhost:8000
export OWLCLAW_API_TOKEN=<token>

# Trigger scenario
java -cp target/classes io.owlclaw.examples.crosslang.Main trigger

# Query scenario
java -cp target/classes io.owlclaw.examples.crosslang.Main query <run_id>

# Error contract scenario
java -cp target/classes io.owlclaw.examples.crosslang.Main error
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
| Trigger agent | `Main trigger` -> `GatewayClient.triggerAgent` | `trigger_agent.sh` |
| Query status | `Main query` -> `GatewayClient.queryRunStatus` | `query_status.sh` |
| Error contract | `Main error` -> invalid payload path | `error_scenario.sh` |

## Verification

Use:

`scripts/verify_cross_lang.ps1`

The script validates the presence of required Java and curl artifacts.

Field alignment check:

`python scripts/cross_lang/compare_response_fields.py --java-json examples/cross_lang/fixtures/java_trigger_response.json --curl-json examples/cross_lang/fixtures/curl_trigger_response.json`
