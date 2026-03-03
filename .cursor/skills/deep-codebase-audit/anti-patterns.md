# Anti-Patterns Catalog — What Auditors Miss and Why

> This catalog documents real-world anti-patterns that are commonly missed
> during code review. Each entry explains WHY it's missed (the cognitive
> trap) and HOW to detect it (the analysis technique).

---

## Category 1: The Silent Failures

These bugs are dangerous because the system appears to work correctly.

### 1.1 The Phantom Config

**Pattern**: User sets a configuration value, the system acknowledges it,
but the value is never actually used.

```python
class App:
    def configure(self, model: str = "gpt-4o-mini"):
        self._config.model = model  # ✓ Stored

    def _create_runtime(self):
        return Runtime(model="gpt-4o-mini")  # ✗ Hardcoded default!
        #              ^^^^^^^^^^^^^^^^^^^^
        #              Should be: model=self._config.model
```

**Why it's missed**: The `configure()` method looks correct. The bug is in a
different method, possibly in a different file. Reviewers check the method
they're looking at, not the downstream consumers.

**Detection technique**: Configuration Propagation Trace (see thinking-models.md §3).
Pick every config value, trace it from storage to point of use.

### 1.2 The Dead Safety Net

**Pattern**: A safety mechanism exists (circuit breaker, rate limiter,
validator) but is configured in a way that it never triggers.

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 1000000):
        #                                      ^^^^^^^^^
        #                                      Effectively disabled
        self.threshold = failure_threshold
```

**Why it's missed**: The code is syntactically correct. The class exists,
the methods work, the tests pass (because tests use small numbers). The
problem is in the default value, which is a number that looks like "a lot"
but is actually "never in practice."

**Detection technique**: For every safety mechanism, ask: "Under what
realistic conditions does this trigger?" If the answer is "never" or
"only if the system is already dead" → it's a dead safety net.

### 1.3 The Zombie Process

**Pattern**: A background process (heartbeat, worker, watcher) starts but
enters a state where it does nothing useful, while the system reports it
as "running."

```python
class Heartbeat:
    async def run(self):
        while self._running:
            has_events = await self.check_events()
            if has_events:
                await self.process_events()
            await asyncio.sleep(self._interval)

    async def check_events(self):
        if not self._event_sources:  # ← Always empty in lite mode
            return False             # ← Always returns False → zombie
```

**Why it's missed**: The heartbeat is "running" — it loops, it sleeps, it
checks. It just never finds anything to do. Logs show it starting
successfully. No errors are raised.

**Detection technique**: For every background loop, trace the condition that
makes it do useful work. Is that condition achievable in all deployment modes?

---

## Category 2: The Security Blind Spots

### 2.1 The Trusted Proxy

**Pattern**: External data passes through an internal function, and the
internal function is trusted because "it's internal."

```python
def handle_tool_result(result: dict) -> str:
    """Format tool result for LLM context."""
    return json.dumps(result)  # ← result comes from external tool
                               #    but is treated as trusted internal data

# Later:
messages.append({"role": "tool", "content": format_tool_result(result)})
# The LLM now sees unsanitized external content as trusted tool output
```

**Why it's missed**: Each function in isolation looks correct. The
`handle_tool_result` function correctly formats JSON. The message builder
correctly adds tool messages. The bug is in the trust boundary — external
data crosses into a trusted context without sanitization.

**Detection technique**: Taint analysis. Mark every piece of data that
originates from outside the system (user input, API response, tool output,
file content, database query result). Trace it to every sink (LLM prompt,
SQL query, shell command, HTML template, log message). At each sink, check:
is the data sanitized for this specific sink type?

### 2.2 The Forgotten Endpoint

**Pattern**: A management/debug/health endpoint is added during development
and never gets authentication.

```python
# In the main app setup:
app.add_middleware(AuthMiddleware)  # ← Protects routes added AFTER this

# But earlier in the file:
@app.get("/health")
def health(): return {"status": "ok"}  # ← Added before middleware → no auth

@app.get("/debug/config")
def debug_config(): return app.config.dict()  # ← Exposes all config!
```

**Why it's missed**: Reviewers check that auth middleware exists. They don't
check the ORDER of route registration vs middleware registration. They also
don't enumerate all endpoints to verify each one is protected.

**Detection technique**: List ALL endpoints. For each one, verify auth is
enforced. Don't trust middleware ordering — test it.

### 2.3 The Injection Relay

**Pattern**: Input is validated at the entry point but a downstream function
constructs a dangerous operation using the "validated" input in a new context.

```python
@app.post("/query")
def query(request: QueryRequest):
    validate_query(request.query)  # ← Validates for SQL injection
    result = execute_query(request.query)
    return format_result(result)

def format_result(result):
    summary = f"Query returned {len(result)} rows: {result[0]}"
    log.info(summary)  # ← Log injection if result contains newlines
    return llm.summarize(summary)  # ← Prompt injection if result
                                   #    contains LLM instructions
```

**Why it's missed**: The input was validated! But it was validated for SQL
injection, not for log injection or prompt injection. Different sinks
require different sanitization.

**Detection technique**: For each piece of external data, check sanitization
at EVERY sink, not just the first one. Data that is safe for SQL may be
dangerous for LLM prompts.

---

## Category 3: The Resource Traps

### 3.1 The Error Path Leak

**Pattern**: Resources are properly managed on the happy path but leaked
on error paths.

```python
async def process_batch(items):
    connections = []
    for item in items:
        conn = await pool.acquire()
        connections.append(conn)
        await conn.execute(process(item))  # ← If this throws on item 3,
                                           #    connections 1-3 are leaked
    for conn in connections:
        await pool.release(conn)  # ← Never reached
```

**Why it's missed**: The happy path is clean — acquire, use, release. The
bug only manifests when `process(item)` throws, which might not happen in
testing.

**Detection technique**: For every resource acquisition, ask: "What if the
NEXT line throws?" If the resource isn't in a `try/finally` or context
manager, it's a potential leak.

### 3.2 The Unbounded Accumulator

**Pattern**: A collection grows without limit, eventually consuming all
available memory.

```python
class AuditLog:
    def __init__(self):
        self._entries = []  # ← No max size

    def log(self, event):
        self._entries.append({
            "timestamp": time.time(),
            "event": event,
            "context": self._get_full_context()  # ← Could be large
        })
```

**Why it's missed**: In testing, the list has 10-100 entries. In production,
it has 10 million. The OOM happens days after deployment.

**Detection technique**: For every `append()`, `add()`, or `[key] = value`
on a long-lived collection, ask: "Is there a size limit? What happens when
it's reached?"

### 3.3 The Timeout Void

**Pattern**: An external call has no timeout, causing the calling thread
to block indefinitely when the external service is slow or down.

```python
def get_embedding(text: str) -> list[float]:
    response = requests.post(
        self.embedding_url,
        json={"input": text}
        # ← No timeout parameter!
    )
    return response.json()["embedding"]
```

**Why it's missed**: It works in testing because the service responds quickly.
The bug manifests only when the service is slow or unreachable, which is
exactly when you need your system to be resilient.

**Detection technique**: Search for every external call (HTTP, DB, SDK).
Check for explicit timeout parameter. If missing → finding.

---

## Category 4: The Concurrency Traps

### 4.1 The Async Yield Trap

**Pattern**: State is read before an `await` and used after, but another
coroutine may have modified it in between.

```python
async def update_counter(self):
    current = self._counter           # ← Read
    await self._notify_observers()    # ← YIELD: other coroutines run
    self._counter = current + 1       # ← Write stale value
```

**Why it's missed**: In single-threaded async, there's no "real" parallelism,
so developers assume safety. But `await` is a yield point where other
coroutines execute, and they may modify `self._counter`.

**Detection technique**: For every `await`, check: is any variable read
before the `await` and written after it? If yes, could another coroutine
modify it during the `await`?

### 4.2 The Lock Scope Mismatch

**Pattern**: A lock protects some accesses to shared state but not all.

```python
class Registry:
    def register(self, name, handler):
        with self._lock:
            self._handlers[name] = handler  # ← Protected

    def list_handlers(self):
        return list(self._handlers.values())  # ← NOT protected!
        #          ^^^^^^^^^^^^^^^^^^^^^^^^
        #          Can see partially-updated dict during concurrent register()
```

**Why it's missed**: The `register` method correctly uses the lock. Reviewers
see the lock and assume the data is protected. They don't check every other
access point.

**Detection technique**: For every locked variable, search for ALL references
to that variable in the codebase. Every reference must be inside the same
lock (or proven safe by other means).

---

## Category 5: The Architecture Drift

### 5.1 The Spec-Code Divergence

**Pattern**: The architecture document describes a capability, but the
implementation is incomplete, incorrect, or missing.

```
Architecture doc says: "Circuit breaker with 5-failure threshold and 60s recovery"
Code says:
    class CircuitBreaker:
        def __init__(self):
            self.threshold = 5
            self.recovery_time = 60
        def record_failure(self):
            self.failures += 1
            # ← Never actually opens the circuit!
            # ← record_failure increments counter but nothing checks it
```

**Why it's missed**: The class exists, the constructor matches the spec,
the method names are right. The bug is that the circuit-opening logic was
never implemented — the class is a skeleton.

**Detection technique**: For every architectural claim, find the implementing
code and verify it actually DOES what the doc says. Don't just check that
the class exists — check that the behavior is correct.

### 5.2 The Integration Leak

**Pattern**: An external service is supposed to be wrapped in an integration
layer, but some code calls it directly.

```python
# owlclaw/integrations/llm.py — the official wrapper
async def acompletion(model, messages):
    # Adds timeout, retry, cost tracking, observability
    ...

# owlclaw/agent/runtime/runtime.py — bypasses the wrapper
async def _call_llm(self):
    response = await litellm.acompletion(  # ← Direct call!
        model=self.model,                  #    Bypasses all governance
        messages=self.messages
    )
```

**Why it's missed**: Both calls use `litellm.acompletion`. The difference
is whether it goes through the wrapper (which adds governance) or directly
to the library. The function name is the same.

**Detection technique**: For every external library, search for ALL import
and usage sites. Verify they all go through the designated wrapper.

### 5.3 The Dead Feature

**Pattern**: A feature is documented and has UI/CLI support, but the
backend implementation is a no-op or stub.

```python
@cli.command()
def export_audit_log(output: str):
    """Export audit log to file."""
    # Implementation pending
    click.echo("Export complete.")  # ← Lies! Nothing was exported.
```

**Why it's missed**: The command exists, it runs without error, it prints
a success message. Only by checking the actual behavior (does the file
exist? does it contain data?) would you discover it's a stub.

**Detection technique**: For every user-facing feature, verify the end-to-end
behavior. Don't trust success messages — check the actual output/side effect.

---

## Category 6: The Testing Illusions

### 6.1 The Mock That Proves Nothing

**Pattern**: A test mocks out the exact thing it should be testing.

```python
def test_llm_completion():
    with mock.patch("owlclaw.integrations.llm.acompletion") as mock_llm:
        mock_llm.return_value = {"choices": [{"message": {"content": "ok"}}]}
        result = runtime.call_llm()
        assert result == "ok"  # ← This tests the mock, not the LLM integration
```

**Why it's missed**: The test passes, coverage increases, CI is green.
But the test proves nothing about whether `acompletion` actually works
with real parameters.

**Detection technique**: For every mock in a test, ask: "Is the mocked
function the thing being tested?" If yes → the test is testing the mock.

### 6.2 The Happy Path Only

**Pattern**: Tests only cover the success case, never the failure case.

```python
def test_create_agent():
    agent = create_agent(name="test", model="gpt-4")
    assert agent.name == "test"  # ← What about:
                                 #    create_agent(name="", model="")
                                 #    create_agent(name=None, model=None)
                                 #    create_agent(name="a"*10000, model="invalid")
```

**Why it's missed**: The test "covers" the function (100% line coverage on
happy path). Coverage tools don't measure branch coverage by default.

**Detection technique**: For every test, ask: "What inputs would make this
function fail?" Then check if those inputs are tested.

### 6.3 The Non-Asserting Test

**Pattern**: A test runs code but doesn't actually verify the result.

```python
def test_shutdown():
    runtime = create_runtime()
    runtime.start()
    runtime.stop()  # ← No assertion!
    # Test passes because no exception was raised.
    # But was the runtime actually stopped? Were resources released?
```

**Why it's missed**: The test "passes" and provides coverage. But it only
proves the code doesn't throw — not that it works correctly.

**Detection technique**: For every test function, count the assertions.
Zero assertions → the test proves nothing. One assertion on a trivial
property → the test proves almost nothing.

---

## How to Use This Catalog

1. **During audit**: When you encounter a code pattern, check this catalog
   for matching anti-patterns. If you find a match, investigate deeply.

2. **After audit**: Review your findings against this catalog. Did you miss
   any category? Go back and check specifically for those patterns.

3. **For teaching**: When training a less capable model, use these examples
   to illustrate the difference between "looks correct" and "is correct."
