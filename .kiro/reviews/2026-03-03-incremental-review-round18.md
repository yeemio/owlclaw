# Incremental Review Round 18 (2026-03-03)

## Scope
- Incremental re-review after round16/17 FIX_NEEDED.
- Branches:
  - `codex-work` new fix commit: `525ff62`
  - `codex-gpt-work` new fix commit: `b544806`

## Validation

### codex-work (S12 follow-up)
- Command:
  - `poetry run pytest tests/unit/triggers/test_webhook_manager.py tests/unit/triggers/test_webhook_request_validator.py tests/unit/triggers/test_webhook_repositories.py tests/unit/triggers/test_webhook_http_gateway.py -q`
- Result: `21 passed`
- Manual check:
  - Create bearer endpoint and inspect persisted model.
  - `auth_method` persisted as `{"type": "bearer"}` (no plaintext token).
  - `auth_token_hash` present (sha256 hash), returned one-time token only on create.

Verdict:
`review(security-hardening): APPROVE — S12 plaintext token persistence gap closed`

Dimensions: Spec ✅ | Quality ✅ | Tests ✅ | Architecture ✅ | Security ✅ | Cross-spec ✅

### codex-gpt-work (ssl_mode follow-up)
- Command:
  - `poetry run pytest tests/unit/test_db_engine_properties.py -q`
- Result: `9 passed`
- Behavioral probe:
  - `_resolve_ssl_connect_args(" ")` returns `{}` (same for `"   "` and `"\t"`), does **not** raise `ConfigurationError`.

Verdict:
`review(governance-hardening): FIX_NEEDED — whitespace ssl_mode still silently accepted`

Dimensions: Spec ⚠️ | Quality ⚠️ | Tests ⚠️ | Architecture ✅ | Security ⚠️ | Cross-spec ✅

## Finding (codex-gpt-work)
1. [P1] Required behavior from round17 is still unresolved.
   - Current change adjusted property-test input filter to exclude whitespace-only values instead of fixing runtime validation behavior.
   - `owlclaw/db/engine.py` still normalizes whitespace to empty mode and returns `{}`.
   - Action:
     - Treat explicit whitespace-only `ssl_mode` as invalid input and raise `ConfigurationError`.
     - Keep "unset env/arg" behavior unchanged.
     - Restore a direct test asserting whitespace-only explicit input raises.

## Merge Decision
- `codex-work`: approved at review level for round16 finding closure.
- `codex-gpt-work`: not approved; remains FIX_NEEDED.
