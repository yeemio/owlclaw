# Thinking Models — How to Analyze Specific Code Patterns

> This file teaches you HOW TO THINK when you encounter specific code patterns.
> Each section is a mini-tutorial: what the pattern is, what can go wrong,
> how to analyze it step by step, and what to look for.

---

## 1. Loops and Iteration

### What Can Go Wrong
- Infinite loop (no termination condition, or condition never becomes true)
- Off-by-one (processes N-1 or N+1 items instead of N)
- Resource accumulation (each iteration allocates but never frees)
- Performance cliff (O(n²) hidden in nested iteration)

### How to Analyze

**Step 1**: Identify the termination condition.
```python
while condition:     # ← What makes `condition` become False?
    do_something()
```
Ask: "Is there a code path through the loop body that does NOT make progress
toward termination?" If yes → potential infinite loop.

**Step 2**: Check the worst case.
```python
for item in collection:  # ← What if collection has 10 million items?
    process(item)        # ← What if process() takes 30 seconds?
```
Multiply: 10M × 30s = 300M seconds. Is there a size limit on `collection`?

**Step 3**: Check resource lifecycle within the loop.
```python
while has_work():
    conn = get_connection()   # ← Acquired
    result = conn.execute(q)  # ← What if this throws?
    conn.close()              # ← Never reached on exception
```
If an exception can occur between acquire and release → resource leak.

**Step 4**: Check retry loops specifically.
```python
while True:
    try:
        result = call_external_service()
        break
    except ServiceError:
        time.sleep(1)  # ← No max retries? No backoff? No jitter?
```
Checklist for retry loops:
- [ ] Maximum retry count exists
- [ ] Backoff strategy (exponential, not fixed)
- [ ] Jitter (to prevent thundering herd)
- [ ] Different handling for retriable vs non-retriable errors
- [ ] Timeout on the overall retry sequence (not just individual attempts)

---

## 2. State Machines and Lifecycle

### What Can Go Wrong
- Invalid state transitions (calling `start()` when already started)
- Partial initialization (some components initialized, others not)
- Zombie state (appears alive but functionally dead)
- Resource leak on state transition failure

### How to Analyze

**Step 1**: Map the states and transitions.
```
CREATED → CONFIGURED → STARTED → RUNNING → STOPPING → STOPPED
                                    ↑                    │
                                    └────────────────────┘ (restart?)
```

**Step 2**: For each transition, ask:
- What happens if this transition is called twice?
- What happens if this transition fails halfway?
- What resources are acquired? What happens if acquisition fails?
- What is the rollback strategy?

**Step 3**: Check for zombie detection.
```python
class Runtime:
    def start(self):
        self._running = True
        self._start_heartbeat()  # ← What if heartbeat thread dies silently?
```
Ask: "If the internal mechanism dies, does the outer state reflect it?"
If `_running` stays `True` but heartbeat is dead → zombie state.

**Step 4**: Check shutdown completeness.
```python
async def stop(self):
    self._running = False
    # ← Are in-flight requests completed?
    # ← Are background tasks cancelled?
    # ← Are connections closed?
    # ← Are files flushed and closed?
    # ← Is the shutdown order correct? (dependents before dependencies)
```

---

## 3. Configuration Propagation

### What Can Go Wrong
- Value set but never read (dead config)
- Value read from wrong source (env var shadows config file)
- Default value overrides user value (parameter default in function signature)
- Value transformed/truncated during propagation
- Value cached and stale after update

### How to Analyze — The Propagation Trace

This is the single most important analysis technique for configuration bugs.

**Step 1**: Pick a configuration value (e.g., `model`).

**Step 2**: Trace it forward through every hop:

```
User sets: owlclaw.configure(model="deepseek/deepseek-chat")
  ↓
Stored: self._config.model = "deepseek/deepseek-chat"         ✓ stored
  ↓
Factory: create_agent_runtime(config=self._config)
  ↓
Constructor: AgentRuntime(model=config.model)                  ← CHECK: does
  ↓                                                              the constructor
Used: litellm.acompletion(model=self.model, ...)                 actually receive
                                                                 and use this?
```

**Step 3**: At each hop, check:
- Is the value actually passed? (Not a different variable)
- Is there a default parameter that shadows it?
  ```python
  def create_runtime(model="gpt-4o-mini"):  # ← This default wins if
      ...                                    #    model is not explicitly passed
  ```
- Is there an environment variable that overrides it?
  ```python
  model = os.getenv("MODEL", config.model)  # ← Env var wins silently
  ```
- Is there a transformation that changes it?
  ```python
  model = model.lower().strip()  # ← "DeepSeek/Chat" → "deepseek/chat"
  ```

**Step 4**: Check the reverse — can you change the value after initialization?
```python
runtime = create_runtime(model="gpt-4")
app.configure(model="deepseek")  # ← Does this update the runtime?
                                 #    Or is the old value cached?
```

---

## 4. Error Handling and Exception Safety

### What Can Go Wrong
- Exception swallowed silently (`except: pass`)
- Wrong exception type caught (too broad or too narrow)
- Error handler itself can throw
- Resource leak in error path
- Error message exposes sensitive information
- Error not propagated to caller

### How to Analyze

**Step 1**: For every `try/except`, classify the handler:

| Handler Type | Pattern | Risk |
|-------------|---------|------|
| Swallow | `except: pass` | Bug hidden forever |
| Log-and-continue | `except: log(e)` | May continue in invalid state |
| Log-and-raise | `except: log(e); raise` | Good, but check log content |
| Transform | `except X: raise Y(...)` | Check if context is preserved |
| Retry | `except: retry()` | Check retry limits |
| Fallback | `except: return default` | Check if default is safe |

**Step 2**: Check exception type specificity.
```python
try:
    result = db.execute(query)
except Exception:  # ← Catches EVERYTHING including:
    log(e)         #    - KeyboardInterrupt (user wants to stop!)
    return None    #    - MemoryError (system is dying!)
                   #    - TypeError (your code has a bug!)
```
Rule: Never catch `Exception` or `BaseException` unless you re-raise.
Catch the specific exception type you expect.

**Step 3**: Check the error path for resource safety.
```python
conn = pool.get_connection()
try:
    result = conn.execute(query)
    conn.commit()
except DatabaseError:
    conn.rollback()  # ← Good: explicit rollback
    raise
finally:
    pool.return_connection(conn)  # ← Good: always return
```
vs.
```python
conn = pool.get_connection()
result = conn.execute(query)  # ← If this throws, conn is leaked
conn.commit()
pool.return_connection(conn)
```

**Step 4**: Check error message content.
```python
except AuthError as e:
    return {"error": f"Auth failed for {username} with key {api_key}"}
    #                                              ^^^^^^^^^^^^^^^^
    #                                              CREDENTIAL IN ERROR RESPONSE
```

---

## 5. Concurrency and Thread Safety

### What Can Go Wrong
- Race condition (check-then-act without atomicity)
- Deadlock (circular lock dependency)
- Starvation (one thread monopolizes resource)
- Data corruption (unsynchronized shared state mutation)
- Lost update (two threads read-modify-write simultaneously)

### How to Analyze

**Step 1**: Identify all shared mutable state.
```python
class Registry:
    def __init__(self):
        self._handlers = {}      # ← Shared? Mutable? → YES, YES
        self._lock = Lock()      # ← Is it used consistently?

    def register(self, name, handler):
        self._handlers[name] = handler  # ← Is _lock acquired here?

    def get(self, name):
        return self._handlers.get(name)  # ← And here?
```

**Step 2**: For each shared variable, check ALL access points.
It's not enough that SOME accesses are locked — ALL must be.

**Step 3**: Check for TOCTOU (Time-of-Check-to-Time-of-Use).
```python
if name not in self._handlers:      # ← Check
    self._handlers[name] = handler  # ← Act
# Between check and act, another thread could have registered `name`
```
Fix: The check and act must be atomic (inside the same lock).

**Step 4**: For async code, check await points.
```python
async def process(self):
    data = self._shared_state       # ← Read state
    await external_call()           # ← YIELD POINT: other coroutines run here
    self._shared_state = transform(data)  # ← Write stale state
```
Every `await` is a potential interleaving point. State read before `await`
may be stale after `await`.

**Step 5**: Check lock ordering for deadlock potential.
```python
# Thread 1:          # Thread 2:
lock_a.acquire()     lock_b.acquire()     # ← Different order!
lock_b.acquire()     lock_a.acquire()     # ← DEADLOCK
```
Rule: All code paths must acquire locks in the same order.

---

## 6. Authentication and Authorization

### What Can Go Wrong
- Endpoint missing auth entirely
- Auth check present but bypassable
- Authorization check uses wrong identity
- Privilege escalation via parameter manipulation
- Session fixation / token reuse

### How to Analyze

**Step 1**: Enumerate ALL endpoints/entry points.
```
GET  /api/agents          → auth required? → [check]
POST /api/agents          → auth required? → [check]
GET  /api/admin/config    → auth required? → [check]  ← ADMIN endpoint
WS   /ws/agent/{id}       → auth required? → [check]  ← WebSocket
```
Every endpoint must be checked. Don't assume "it's probably protected."

**Step 2**: For each protected endpoint, trace the auth flow:
```
Request arrives
  → Middleware extracts token from header/cookie
    → Token is validated (signature, expiry, issuer)
      → User identity is extracted
        → Authorization check: does this user have permission for this action?
          → On this specific resource? (not just "is admin" but "owns this agent")
```

**Step 3**: Check for authorization bypass patterns:
```python
# BAD: tenant_id from user input
@app.get("/api/agents")
def list_agents(tenant_id: str = Query(...)):  # ← User controls tenant_id!
    return db.query(Agent).filter(Agent.tenant_id == tenant_id).all()

# GOOD: tenant_id from authenticated session
@app.get("/api/agents")
def list_agents(current_user: User = Depends(get_current_user)):
    return db.query(Agent).filter(Agent.tenant_id == current_user.tenant_id).all()
```

**Step 4**: Check WebSocket auth specifically.
WebSocket connections often authenticate only at connection time. If the token
expires during a long-lived connection, is the connection terminated?

---

## 7. Database Operations

### What Can Go Wrong
- SQL injection (string concatenation)
- Connection leak (not returned to pool on error)
- N+1 query (loop that issues one query per item)
- Missing index (full table scan on common query)
- Transaction isolation issues (dirty read, phantom read)
- Migration data loss (column drop, type change)

### How to Analyze

**Step 1**: Check every query construction.
```python
# BAD: String concatenation
query = f"SELECT * FROM users WHERE name = '{name}'"

# GOOD: Parameterized
query = "SELECT * FROM users WHERE name = :name"
session.execute(query, {"name": name})

# ALSO GOOD: ORM
session.query(User).filter(User.name == name)
```

**Step 2**: Check session/connection lifecycle.
```python
# BAD: Session created but never closed on error
session = Session()
result = session.execute(query)  # ← If this throws?
session.close()                  # ← Never reached

# GOOD: Context manager
with Session() as session:
    result = session.execute(query)  # ← Session closed even on error
```

**Step 3**: Check for N+1 queries.
```python
agents = session.query(Agent).all()       # Query 1
for agent in agents:
    caps = agent.capabilities              # Query 2, 3, 4, ... N+1
    #     ^^^^^^^^^^^^^^^^^^^^
    #     Lazy load triggers one query per agent
```
Fix: Eager loading with `joinedload()` or `selectinload()`.

**Step 4**: Check migrations for safety.
```python
# DANGEROUS: Irreversible
op.drop_column('users', 'email')

# SAFE: Reversible
op.add_column('users', sa.Column('email_new', sa.String))
# ... migrate data ...
# ... in next migration, drop old column after verification ...
```

---

## 8. External Service Integration

### What Can Go Wrong
- Missing timeout (blocks forever on network issue)
- Missing retry (transient error causes permanent failure)
- Missing circuit breaker (keeps hammering a dead service)
- Credential leak in logs/errors
- Response not validated (trusting external data)

### How to Analyze

**Step 1**: For every external call, check the "failure pentagon":

```
         Timeout?
        /        \
   Retry?        Circuit Breaker?
      |              |
   Fallback?    Error Logging?
```

All five must be present for a production-ready integration.

**Step 2**: Check timeout values.
```python
response = requests.get(url, timeout=30)  # ← Is 30s appropriate?
                                          #    For a health check? Too long.
                                          #    For a file download? Maybe OK.
```
Rule of thumb: timeout = 2× expected response time, minimum 5s, maximum 60s.

**Step 3**: Check what happens when the service returns unexpected data.
```python
response = llm_client.complete(prompt)
model_name = response.model          # ← What if response has no .model?
usage = response.usage.total_tokens  # ← What if .usage is None?
```
Every field access on external response data should be defensive.

**Step 4**: Check credential handling.
```python
# BAD: Credential in URL (appears in logs, browser history, server logs)
url = f"https://api.example.com?key={api_key}"

# BAD: Credential in error message
except APIError as e:
    logger.error(f"Failed with key {self.api_key}: {e}")

# GOOD: Credential in header, masked in logs
headers = {"Authorization": f"Bearer {api_key}"}
logger.error(f"API call failed: {e}")  # No key in message
```

---

## 9. CLI and User Interface

### What Can Go Wrong
- Arguments not validated (path traversal, injection)
- Error messages unhelpful (stack trace instead of guidance)
- Silent failure (command appears to succeed but does nothing)
- Inconsistent behavior (same flag means different things in different commands)
- Missing help text (user can't discover features)

### How to Analyze

**Step 1**: Test every command with bad input.
```bash
owlclaw configure --model ""           # Empty string
owlclaw configure --model "../../etc"  # Path traversal
owlclaw skill list --path "/nonexistent"  # Invalid path
owlclaw agent run                      # Missing required args
```

**Step 2**: Check error output quality.
```
# BAD:
Traceback (most recent call last):
  File "...", line 42, in ...
    raise ValueError("invalid")
ValueError: invalid

# GOOD:
Error: Invalid model name "../../etc". Expected format: provider/model-name
  Example: owlclaw configure --model deepseek/deepseek-chat
  Run 'owlclaw configure --help' for more options.
```

**Step 3**: Check for silent failures.
```python
def run_command(args):
    if not args.config:
        return  # ← Silent return! User sees nothing.
                #    Should print: "Error: No configuration found. Run 'owlclaw configure' first."
```

---

## 10. Memory and Resource Management

### What Can Go Wrong
- Unbounded growth (list/dict grows without limit)
- Circular references (prevent garbage collection)
- Large object retention (holding references longer than needed)
- File descriptor exhaustion (too many open files/sockets)

### How to Analyze

**Step 1**: For every collection that grows at runtime, check:
- Is there a maximum size?
- Is there eviction/rotation?
- What happens when the limit is reached?

```python
class MemoryStore:
    def __init__(self):
        self._memories = []  # ← Grows forever?

    def add(self, memory):
        self._memories.append(memory)  # ← No size check!
```

**Step 2**: For every file/socket/connection opened, check:
- Is it closed in a `finally` block or context manager?
- What if the process crashes — is there cleanup on restart?
- Is there a limit on concurrent open resources?

**Step 3**: For caches, check:
- Is there a TTL?
- Is there a max size?
- Is eviction thread-safe?
- Can stale cache entries cause incorrect behavior?
