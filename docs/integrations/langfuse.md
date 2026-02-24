# Langfuse Integration Guide

## Quick Start

1. Configure environment variables:

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://cloud.langfuse.com
```

2. Enable runtime config:

```yaml
langfuse:
  enabled: true
  public_key: ${LANGFUSE_PUBLIC_KEY}
  secret_key: ${LANGFUSE_SECRET_KEY}
  host: ${LANGFUSE_HOST}
```

3. Run Agent as usual. Runtime will create `agent_run` traces and append:
- LLM generation observations from `llm.acompletion()`
- Tool execution spans from runtime tool dispatcher

## Privacy

- Use `mask_inputs` and `mask_outputs` when tracing sensitive payloads.
- `PrivacyMasker` masks common PII (email/phone/SSN/card) and secrets (API key/Bearer/password).
- You can add `custom_mask_patterns` with regex.

## Troubleshooting

- If Langfuse SDK is unavailable or connection fails, tracing degrades gracefully.
- Failures are logged as warnings without leaking configured API keys.
- Runtime execution is not blocked by Langfuse errors.

