# Runner — The Stateless Orchestrator

**Source:** [`runners.py`](../adk-python/src/google/adk/runners.py)

---

## What It Is

`Runner` is the outermost layer that connects everything. It owns the lifecycle of a single user request:

1. Fetch or create a `Session`
2. Build an `InvocationContext`
3. Call the root agent's `run_async()`
4. Stream `Event`s back to the caller
5. Persist events to the session service
6. Optionally compact old events (summarize history)

`Runner` is **stateless** — it holds no conversation state itself. All state lives in `Session` (via `session_service`). This means the same `Runner` instance can handle many concurrent invocations safely.

---

## Construction

```python
runner = Runner(
    agent=root_agent,                      # the root agent to run
    app_name='my_app',
    session_service=InMemorySessionService(),

    # optional:
    artifact_service=...,
    memory_service=...,
    credential_service=...,
    auto_create_session=False,             # raise if session not found
)

# Preferred: pass an App instead of agent+app_name
runner = Runner(
    app=my_app,                            # App bundles agent + plugins + config
    session_service=...,
)
```

---

## Key Methods

### [ ] `run_async` — Text/Chat Mode

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
  → agent reasoning events (partial=True streaming chunks)
  → function call events
  → function response events
  → final agent response event (partial=False)
```

### [ ] `run_live` — Audio/Video Mode

```python
async def run_live(
    user_id: str,
    session_id: str,
    live_request_queue: LiveRequestQueue,
    run_config: Optional[RunConfig] = None,
) -> AsyncGenerator[Event, None]:
```

Bidirectional streaming for real-time audio/video (Gemini Live API). Uses a queue instead of a single message.

### [ ] `run` — Sync Wrapper

```python
def run(...) -> Generator[Event, None, None]:
```

Synchronous wrapper over `run_async`. Runs the event loop in a background thread via `create_thread`. Useful for scripts and CLIs.

---

## Internal Flow (run_async)

```
Runner.run_async(user_id, session_id, new_message)
│
├─ 1. _get_or_create_session(user_id, session_id)
│      → session_service.get_session(...)
│      → auto-creates if auto_create_session=True, else raises
│
├─ 2. _setup_context_for_new_invocation(session, new_message, run_config)
│      → Appends user message Event to session
│      → Creates InvocationContext with invocation_id, branch, services
│
├─ 3. agent.run_async(invocation_context)
│      → Delegate to the root agent
│      → Yields Events as they stream out
│
├─ 4. For each event:
│      → session_service.append_event(session, event)   (persist)
│      → yield event                                    (stream to caller)
│
└─ 5. Post-invocation:
       → _run_compaction_for_sliding_window(...)  (if App has compaction config)
       → Close plugin contexts
```

---

## Session Auto-Creation

By default (`auto_create_session=False`), passing an unknown `session_id` raises `SessionNotFoundError` with a helpful message. This makes bugs obvious.

Set `auto_create_session=True` when you want the Runner to silently create a new session on first use (useful in demos and lightweight scripts).

---

## RunConfig

`RunConfig` is an optional per-invocation configuration:

```python
class RunConfig:
    streaming_mode: StreamingMode   # SSE, NONE
    max_llm_calls: int              # safety cap on LLM calls per invocation
    save_input_blobs_as_artifacts: bool
    support_cfc: bool               # client function calling
    custom_metadata: dict           # attached to all events from this run
```

---

## Plugins

Runner initializes a `PluginManager` from the plugin list. Plugins hook into:
- `before_agent_callback` / `after_agent_callback` (at the Runner level, runs for every agent)
- Session lifecycle

Plugins are provided via the `App` object (preferred) or the deprecated `plugins=` argument.

---

## Event Compaction

After an invocation completes, Runner can trigger **sliding window compaction** if configured in `App.events_compaction_config`:

- After every N invocations, old events get summarized into a single compacted Event
- `overlap_size` controls how many recent invocations are kept verbatim for context
- The summarizer is pluggable (`BaseEventsSummarizer`)

This prevents `Session.events` from growing unboundedly in long conversations.

---

## Related Files

- [`runners.py`](../adk-python/src/google/adk/runners.py) — `Runner` class
- [`apps/app.py`](../adk-python/src/google/adk/apps/app.py) — `App` (preferred way to configure Runner)
- [`agents/invocation_context.py`](../adk-python/src/google/adk/agents/invocation_context.py) — context object Runner creates
- [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) — session persistence
- [`apps/compaction.py`](../adk-python/src/google/adk/apps/compaction.py) — event compaction logic
