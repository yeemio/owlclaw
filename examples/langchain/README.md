# LangChain Integration Examples

This directory provides five runnable-oriented integration examples:

1. `basic_runnable_registration.py`: register a runnable directly.
2. `decorator_registration.py`: register via `@app.handler(..., runnable=...)`.
3. `fallback_and_retry.py`: fallback capability and exponential backoff retry.
4. `transformers.py`: custom input/output transformer hooks.
5. `tracing_with_langfuse.py`: tracing and privacy masking configuration.

Install optional dependencies first:

```bash
pip install "owlclaw[langchain]"
```
