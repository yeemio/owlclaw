# Incremental Review Round 17 (2026-03-03)

## Scope
- Branch reviewed: `codex-gpt-work` (`review-work..codex-gpt-work`)
- Focus: Phase 12 `runtime-robustness` + `governance-hardening` incremental changes

## Validation Performed
- Targeted regression suite on coding branch (`D:\AI\owlclaw-codex-gpt`):
  - `poetry run pytest tests/unit/test_app.py tests/unit/agent/test_runtime.py tests/unit/agent/test_runtime_performance.py tests/unit/agent/memory/test_inmemory_store.py tests/unit/test_registry.py tests/unit/test_hatchet.py tests/unit/integrations/test_langfuse.py tests/unit/triggers/test_db_change.py tests/unit/triggers/test_api.py tests/unit/triggers/test_cron_execution.py tests/unit/governance/test_ledger.py tests/unit/governance/test_quality_store.py tests/unit/test_db_engine_properties.py tests/unit/test_db_session_properties.py tests/unit/test_migration_governance_hardening.py tests/unit/capabilities/test_bindings_queue_executor.py tests/unit/triggers/test_queue_idempotency.py tests/unit/triggers/test_webhook_repositories.py -q`
  - Result: `1 failed, 320 passed`

## Verdict
`review(governance-hardening): FIX_NEEDED — ssl_mode whitespace input is silently accepted`

Dimensions: Spec ✅ | Quality ⚠️ | Tests ❌ | Architecture ✅ | Security ⚠️ | Cross-spec ✅

## Findings
1. [P1] Invalid `ssl_mode` value `" "` is normalized to empty and bypasses validation.
   - Failure evidence:
     - `tests/unit/test_db_engine_properties.py::test_property_invalid_ssl_mode_raises_configuration_error`
     - Falsifying example from Hypothesis: `mode=' '`
   - Root cause:
     - `owlclaw/db/engine.py` `_normalize_ssl_mode()` uses `.strip().lower()` and returns empty string for whitespace-only values.
     - `_resolve_ssl_connect_args()` treats empty mode as unset (`{}`) instead of invalid.
   - Impact:
     - Caller-provided invalid value can silently disable strict SSL mode validation path.
   - Required fix:
     - Treat explicit non-`None` whitespace-only `ssl_mode` as invalid and raise `ConfigurationError` (or distinguish between "unset" and "explicit but invalid").
     - Keep environment-variable unset behavior unchanged.
     - Re-run failing property test and include command output.

## Merge Decision
- Not merged into `review-work` (FIX_NEEDED).
