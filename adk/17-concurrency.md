# Concurrency Reference

**Source:** [`runners.py`](../adk-python/src/google/adk/runners.py) · [`functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py) · [`sessions/database_session_service.py`](../adk-python/src/google/adk/sessions/database_session_service.py) · [`sessions/in_memory_session_service.py`](../adk-python/src/google/adk/sessions/in_memory_session_service.py) · [`agents/parallel_agent.py`](../adk-python/src/google/adk/agents/parallel_agent.py)

---

## What's Safe

| Operation | Safe? | Notes |
|---|---|---|
| Same `Runner`, different `session_id` | Yes | Runner is stateless |
| Same `Runner`, same `session_id` with `DatabaseSessionService` (MySQL/PostgreSQL) | Yes | DB lock serializes `append_event` |
| Same `Runner`, same `session_id` with `InMemorySessionService` | No | No locks, last writer wins, silent data loss |
| Same `Runner`, same `session_id` with `DatabaseSessionService` + SQLite across processes | No | Only in-process asyncio lock; cross-process writes corrupt |
| Sharing `Agent` instances across invocations | Yes | Agents are pure config (Pydantic models) |
| Sharing `Session` objects across invocations | No | Let session service return fresh copies |
| Parallel tools writing same state key | No | `deep_merge_dicts` uses last-write-wins |
| `ToolThreadPoolConfig` + tools accessing `ToolContext` | No | Shared objects not thread-safe |

---

## Parallel Tool Execution

When an LLM response contains multiple tool calls, `functions.py` dispatches them via `asyncio.gather`:

- All tool coroutines are launched concurrently and awaited together.
- `return_exceptions=True` is **not** used -- one failing tool re-raises immediately while the others keep running in the background. This is a potential resource leak.
- State deltas from parallel tools are merged via `deep_merge_dicts`. On key conflicts the last-merged tool's value wins silently.

```
Parallel Tool Execution — Happy Path:

  LLM returns: [FunctionCall("get_weather"), FunctionCall("get_news")]
                          │                           │
                          ▼                           ▼
                   ┌─────────────┐            ┌─────────────┐
                   │ get_weather │            │  get_news   │
                   │ (200ms)     │            │  (300ms)    │
                   └──────┬──────┘            └──────┬──────┘
                          │                           │
                          └─────────┬─────────────────┘
                                    ▼
                         asyncio.gather() merges results
                         → single FunctionResponse event
                         → back to LLM

  Total time: 300ms (not 500ms) — parallel wins!

Collision Scenario — both tools write same state key:

  Tool A: ctx.state["result"] = "sunny"     (finishes first)
  Tool B: ctx.state["result"] = "breaking"  (finishes second)
                          │
                          ▼
              deep_merge_dicts → last write wins
              state["result"] = "breaking"  ← Tool A's write is lost!

  Fix: use different state keys per tool
```

---

## Session Locking

### DatabaseSessionService -- Two-Layer Locking

1. **In-process asyncio lock** keyed by `(app_name, user_id, session_id)` with reference counting. Ensures only one coroutine within a single process touches a session at a time.
2. **Database row-level locking** (`SELECT FOR UPDATE`) on MySQL and PostgreSQL only. SQLite does not support this, so cross-process safety is not guaranteed with SQLite.
3. **Staleness detection:** compares `update_time` timestamps on load and reloads the session if the stored version is newer than the in-memory copy.

### InMemorySessionService -- No Locking

- The docstring is explicit: "not suitable for multi-threaded production environments."
- `get_session` returns a `copy.deepcopy` of the stored session, preventing callers from mutating internal storage directly.
- Concurrent `append_event` calls are a data race -- no synchronization exists.

---

## Plugin Execution

Plugins run **strictly sequentially** (a `for` loop with `await` on each plugin). The `close` phase is also sequential to avoid task-context issues with anyio/MCP on Python 3.10.

---

## ParallelAgent

- Each sub-agent receives an isolated `InvocationContext` copy with a unique `branch`.
- Events are serialized back to the caller via an `asyncio.Queue` + resume-signal pattern.
- All sub-agents share the same `Session` reference, but event delivery to the session is serialized through the queue.
- **Known race:** parallel sub-agents that write the same `output_key` produce a last-write-wins result.

---

## Thread Pool (ToolThreadPoolConfig)

- **Opt-in**, disabled by default.
- **Sync tools:** run directly in a `ThreadPoolExecutor`.
- **Async tools:** run in a brand-new event loop per worker thread. This means they cannot share asyncio primitives (locks, queues, events) with the main loop.
- The pool is **global and process-wide** -- it is never destroyed.
- `InvocationContext` and `ToolContext` are shared with the main event loop but are **not thread-safe**. Accessing or mutating them from a pool worker is undefined behavior.

---

## Cross-References

- [Request Lifecycle](01-request-lifecycle.md) -- full traced request showing where session calls happen
- [Sessions](08-sessions.md) -- session state model and storage backends
- [Session Service Lifecycle](18-session-lifecycle.md) -- detailed `append_event` flow and state delta mechanics
- [Error Reference](16-error-reference.md) -- what happens when tool or model calls fail mid-execution
