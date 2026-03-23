# 03 — Runner: The Stateless Orchestrator

> **Official docs:** [Runtime](https://google.github.io/adk-docs/runtime/) | **Source:** [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) | **Prereqs:** [01-request-lifecycle.md](01-request-lifecycle.md), [02-when-to-build-what.md](02-when-to-build-what.md)

## At a Glance

```
┌──────────────────────────────────────────┐
│          Runner.run_async()               │
│  1. fetch/create Session                  │
│  2. build InvocationContext               │
│  3. call agent.run_async()                │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│          Agent.run_async()                │
│  yields Event stream                      │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│          Event Handling                   │
│  persist each event to session            │
│  yield each event to caller               │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│          Post-Invocation                  │
│  compaction (optional)                    │
│  close plugin contexts                    │
└──────────────────────────────────────────┘
```

`Runner` owns the lifecycle of a single user request: fetch or create a session, build an invocation context, call the root agent, stream events back to the caller, and persist them. Runner is stateless — all state lives in `Session` — so one Runner instance serves many concurrent users.

---

## Runner vs Agent vs Session

```
Runner (stateless)              Agent (stateless)              Session (stateful)
─────────────────               ─────────────────              ──────────────────
Owns: request lifecycle         Owns: behavior                 Owns: conversation history
Holds: service refs             Holds: config                  Holds: state + events
Creates: InvocationCtx          Creates: LlmRequest            Created by: SessionService
Dies after: run_async()         Lives forever                  Lives across invocations
```

---

## Key API

### `run_async` — Text/Chat Mode

```python
async def run_async(
    self,
    *,
    user_id: str,
    session_id: str,
    invocation_id: Optional[str] = None,
    new_message: Optional[types.Content] = None,
    state_delta: Optional[dict[str, Any]] = None,
    run_config: Optional[RunConfig] = None,
) -> AsyncGenerator[Event, None]:
```

Note: all parameters are **keyword-only** (after `*`). `new_message` is `Optional` (can be `None` for resumable invocations). `invocation_id` allows specifying a custom invocation ID, and `state_delta` allows injecting state changes at invocation time.

The main entry point. Yields Events as they are produced:

```
user message event
 ► agent reasoning events (partial=True streaming chunks)
   ► function call events
     ► function response events
       ► final agent response event (partial=False)
```

### `run_live` — Audio/Video Mode

```python
async def run_live(
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    live_request_queue: LiveRequestQueue,
    run_config: Optional[RunConfig] = None,
    session: Optional[Session] = None,
) -> AsyncGenerator[Event, None]:
```

Bidirectional streaming for Gemini Live API.

### `run` — Sync Wrapper

```python
def run(...) -> Generator[Event, None, None]:
```

Sync wrapper. Runs event loop in background thread. For scripts and CLIs.

---

## How It Works

### Construction

```python
runner = Runner(
    agent=root_agent, # the root agent to run
    app_name='my_app',
    session_service=InMemorySessionService(),

    # optional:
    artifact_service=...,
    memory_service=...,
    credential_service=...,
    auto_create_session=False, # raise if session not found
)

# For production: pass an App instead (adds plugins, compaction, caching — see 10-apps.md)
runner = Runner(
    app=my_app, # App bundles agent + plugins + config
    session_service=...,
)
```

### Internal Flow (run_async)

```
Runner.run_async(user_id, session_id, new_message)
│
├─ 1. _get_or_create_session(user_id, session_id)
│     ► session_service.get_session(...)
│     ► auto-creates if auto_create_session=True, else raises
│
├─ 2. _setup_context_for_new_invocation(session, new_message, run_config)
│     ► Appends user message Event to session
│     ► Creates InvocationContext with invocation_id, branch, services
│
├─ 3. agent.run_async(invocation_context)
│     ► Delegate to the root agent
│     ► Yields Events as they stream out
│
├─ 4. For each event:
│     ► session_service.append_event(session, event) (persist)
│     ► yield event (stream to caller)
│
└─ 5. Post-invocation:
      ► _run_compaction_for_sliding_window(...) (if App has compaction config)
      ► Close plugin contexts
```

### Session Auto-Creation

Set `auto_create_session=True` for demos/scripts; defaults to `False` (see Gotchas).

### RunConfig

`RunConfig` is an optional per-invocation configuration:

```python
class RunConfig:
    streaming_mode: StreamingMode # NONE, SSE, BIDI
    max_llm_calls: int = 500 # safety cap; <= 0 disables. Raises LlmCallsLimitExceededError
    get_session_config: Optional[GetSessionConfig] = None # partial session loading
    support_cfc: bool # client function calling
    custom_metadata: dict # attached to all events from this run
    # save_input_blobs_as_artifacts: bool  # DEPRECATED — use SaveFilesAsArtifactsPlugin
```

### Plugins

Runner initializes `PluginManager`. Plugins hook into:
- `before_agent_callback` / `after_agent_callback` (at the Runner level, runs for every agent)
- Session lifecycle

Provide via `App` (preferred). See [10-apps.md](10-apps.md) for `BasePlugin` interface and examples.

```python
app = App(root_agent=agent, plugins=[MyPlugin()])
runner = Runner(app=app, session_service=InMemorySessionService())
```

### Event Compaction

```
┌──────────────────────────────────────────┐
│       Sliding Window Compaction           │
│  inv 1, inv 2, inv 3, inv 4, inv 5       │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│       Old Invocations (inv 1, inv 2)      │
│  summarized into a single compacted Event │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│       Recent Invocations                  │
│  inv 3, inv 4, inv 5 kept verbatim        │
│  (overlap_size controls how many)         │
└──────────────────────────────────────────┘
```

Post-invocation **sliding window compaction** (if configured):

- After every N invocations, old events get summarized into a single compacted Event
- `overlap_size` controls how many recent invocations are kept verbatim for context
- The summarizer is pluggable (`BaseEventsSummarizer`)

Prevents unbounded event growth.

---

## Examples

```python
from google.genai import types

runner = Runner(
    agent=root_agent,
    app_name='my_app',
    session_service=InMemorySessionService(),
    auto_create_session=True,
)

# Text/chat mode
async for event in runner.run_async(
    user_id='user1',
    session_id='session1',
    new_message=types.Content(parts=[types.Part(text='Hello')]),
):
    print(event)

# Sync wrapper for scripts
for event in runner.run(
    user_id='user1',
    session_id='session1',
    new_message=types.Content(parts=[types.Part(text='Hello')]),
):
    print(event)
```

---

## Gotchas

- `auto_create_session` defaults to `False` — you get `SessionNotFoundError` if you forget to create a session first or set this flag.
- `run_async` parameters are all **keyword-only** — positional args raise `TypeError`.
- Each concurrent invocation must use a different `session_id` — sharing a session_id across concurrent calls causes undefined behavior because `Session` is stateful.

---

## Related

- [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) — `Runner` class
- [`apps/app.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/app.py) — `App` (preferred way to configure Runner)
- [`agents/invocation_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/invocation_context.py) — context object Runner creates
- [`sessions/base_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/base_session_service.py) — session persistence
- [`apps/compaction.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/compaction.py) — event compaction logic
- [18-session-lifecycle.md](18-session-lifecycle.md) — Session service call timeline and latency optimization
- [16-error-reference.md](16-error-reference.md) — Error reference (SessionNotFoundError, LlmCallsLimitExceededError)
