# Incremental Review Round 16 (2026-03-03)

## Scope
- Branch reviewed: `codex-work` (`review-work..codex-work`)
- Commits:
  - `6019269` fix(agent): complete phase12 cp1-cp7 and security s1-s3-s9
  - `1552541` fix(triggers): complete security-hardening and webhook token hashing
  - `5d75e47` docs(agent): record cp8.2 real-llm validation as blocked
  - `5cadd4a` test(integrations): complete cp8.2 with deepseek real-llm validation

## Validation Performed
- Targeted tests on coding branch (`D:\AI\owlclaw-codex`):
  - `poetry run pytest tests/unit/triggers/test_webhook_http_gateway.py tests/unit/triggers/test_webhook_request_validator.py tests/unit/triggers/test_webhook_manager.py tests/unit/triggers/test_webhook_repositories.py tests/unit/test_mcp_server.py tests/unit/security/test_audit.py tests/unit/security/test_sanitizer.py tests/unit/agent/test_runtime.py -q`
  - Result: `136 passed`
- Manual runtime check:
  - Created bearer endpoint via `WebhookEndpointManager`.
  - Confirmed persisted model still stores plaintext bearer token in `auth_method.token` while also writing `auth_token_hash`.

## Verdict
`review(security-hardening): FIX_NEEDED — S12 objective not met; bearer token still persisted in plaintext`

Dimensions: Spec ⚠️ | Quality ✅ | Tests ⚠️ | Architecture ✅ | Security ❌ | Cross-spec ✅

## Findings
1. [P1] Plaintext bearer token remains persisted after "hash storage" change.
   - Evidence:
     - `owlclaw/triggers/webhook/manager.py`: `create_endpoint()` and `update_endpoint()` still write `auth_method["token"] = config.auth_method.token`.
     - `owlclaw/triggers/webhook/validator.py`: bearer auth prioritizes plaintext `auth_method.token` path when present.
   - Impact:
     - Security-hardening `S12` claims token hash storage, but sensitive bearer token is still present in DB JSON payload.
     - Compromised DB can still extract usable bearer token directly.
   - Required fix:
     - Do not persist plaintext bearer token in `auth_method` for bearer mode.
     - Persist only hash (`auth_token_hash`) and validate via hash compare path.
     - Add regression test asserting repository model `auth_method.token` is empty/absent after create/update for bearer endpoints.

## Merge Decision
- Not merged into `review-work` (FIX_NEEDED).
