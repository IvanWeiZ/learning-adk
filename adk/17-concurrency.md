# 17 — Concurrency: Thread Safety & Parallel Tools

> **Source:** [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) · [`functions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/functions.py) · [`sessions/database_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/database_session_service.py) · [`sessions/in_memory_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/in_memory_session_service.py) · [`agents/parallel_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/parallel_agent.py) | **Prereqs:** [08-sessions.md](./08-sessions.md), [09-tools.md](./09-tools.md) | **Official docs:** <https://google.github.io/adk-docs/runtime/>

---

## At a Glance

```
              Runner (stateless — safe to share)
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
 Session A   Session B   Session C    ← different session_id = always safe
    │
    ├─ DatabaseSessionService ──→ asyncio lock + DB row lock ──→ safe
    └─ InMemorySessionService ──→ no locks ──→ data race!

 Parallel Tool Execution (asyncio.gather):
    LLM returns: [tool_A, tool_B]
         │            │
         ▼            ▼
    ┌─────────┐ ┌─────────┐
    │ tool_A  │ │ tool_B  │   concurrent coroutines
    └────┬────┘ └────┬────┘
         └─────┬─────┘
               ▼
    deep_merge_dicts (last-write-wins on key conflicts)
```

ADK is async-first and generally safe for concurrent requests across different sessions. The main danger zones are: (1) concurrent writes to the same session with `InMemorySessionService`, (2) parallel tools writing the same state key, and (3) thread-pool tools accessing non-thread-safe `ToolContext`. Understanding these boundaries lets you scale safely.

---

## Class Hierarchy

```
SessionService
 ├── InMemorySessionService   (no locks — not production-safe for concurrency)
 ├── DatabaseSessionService   (asyncio lock + DB row lock — production-safe)
 └── SQLiteSessionService     (in-process lock only — not cross-process safe)

ParallelAgent (agents/parallel_agent.py — runs sub-agents concurrently)

 ToolThreadPoolConfig (opt-in thread pool for sync/async tools)
```

---

## Key API

### [ ] What's Safe

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

## How It Works

### [ ] Parallel Tool Execution

```
Parallel Tool Execution — Happy Path:

 LLM returns: [FunctionCall("get_weather"), FunctionCall("get_news")]
 │ │
 ▼ ▼
 ┌─────────────┐ ┌─────────────┐
 │ get_weather │ │ get_news │
 │ (200ms) │ │ (300ms) │
 └──────┬──────┘ └──────┬──────┘
 │ │
 └─────────┬─────────────────┘
 ▼
 asyncio.gather() merges results
 → single FunctionResponse event
 → back to LLM

 Total time: 300ms (not 500ms) — parallel wins!

Collision Scenario — both tools write same state key:

 Tool A: ctx.state["result"] = "sunny" (finishes first)
 Tool B: ctx.state["result"] = "breaking" (finishes second)
 │
 ▼
 deep_merge_dicts → last write wins
 state["result"] = "breaking" ← Tool A's write is lost!

 Fix: use different state keys per tool
```

`functions.py` dispatches multiple tool calls via `asyncio.gather`:

- All tool coroutines launch concurrently.
- `return_exceptions=True` is **not** used -- one failing tool re-raises immediately while the others keep running in the background. This is a potential resource leak.
- State deltas from parallel tools are merged via `deep_merge_dicts`. On key conflicts the last-merged tool's value wins silently.

### [ ] Session Locking

#### [ ] DatabaseSessionService — Two-Layer Locking

1. **In-process asyncio lock** keyed by `(app_name, user_id, session_id)` with reference counting. Ensures only one coroutine within a single process touches a session at a time.
2. **Database row-level locking** (`SELECT FOR UPDATE`) on MySQL and PostgreSQL only. SQLite does not support this, so cross-process safety is not guaranteed with SQLite.
3. **Staleness detection:** compares `update_time` timestamps on load and reloads the session if the stored version is newer than the in-memory copy.

#### [ ] InMemorySessionService — No Locking

- The docstring is explicit: "not suitable for multi-threaded production environments."
- `get_session` returns a `copy.deepcopy` of the stored session, preventing callers from mutating internal storage directly.
- Concurrent `append_event` calls are a data race -- no synchronization exists.

### [ ] Plugin Execution

Plugins run strictly sequentially. `close` is also sequential (anyio/MCP compatibility).

### [ ] ParallelAgent

- Each sub-agent gets an isolated `InvocationContext` with unique `branch`.
- Events serialize via `asyncio.Queue` + resume-signal.
- Sub-agents share one `Session`; event delivery is serialized through the queue.
- **Known race:** parallel sub-agents that write the same `output_key` produce a last-write-wins result.

### [ ] Thread Pool (ToolThreadPoolConfig)

```
ToolThreadPoolConfig — sync vs async tool execution paths
│
├── ToolThreadPoolConfig NOT set (default)
│   ├── Sync tool
│   │   └── Wrapped with asyncio.to_thread → runs in default executor
│   └── Async tool
│       └── Runs directly as coroutine in main event loop
│
└── ToolThreadPoolConfig SET (opt-in thread pool)
    ├── Sync tool
    │   └── Submitted to global ThreadPoolExecutor
    │       └── Runs in worker thread directly
    │       └── ToolContext shared with main loop (NOT thread-safe!)
    │
    └── Async tool
        └── Submitted to global ThreadPoolExecutor
            └── Brand-new event loop created per worker thread
            └── Cannot share asyncio primitives (locks, queues) with main loop
            └── ToolContext shared with main loop (NOT thread-safe!)
```

- **Opt-in**, disabled by default.
- **Sync tools:** run directly in a `ThreadPoolExecutor`.
- **Async tools:** run in a brand-new event loop per worker thread. This means they cannot share asyncio primitives (locks, queues, events) with the main loop.
- The pool is **global and process-wide** -- it is never destroyed.
- `InvocationContext` and `ToolContext` are shared with the main event loop but are **not thread-safe**. Accessing or mutating them from a pool worker is undefined behavior.

---

## Examples

```python
# Safe: different sessions, same runner
runner = Runner(agent=my_agent, app_name="myapp",
                session_service=DatabaseSessionService(db_url))

# These can run concurrently without issues:
asyncio.gather(
    process_request(runner, user_id="u1", session_id="s1"),
    process_request(runner, user_id="u2", session_id="s2"),
)

# Unsafe: same session with InMemorySessionService
# Both writes race — one will silently lose events
```

```python
# Safe parallel tools: use different state keys
def get_weather(city: str, ctx: ToolContext) -> str:
    ctx.state["weather_result"] = fetch_weather(city)
    return ctx.state["weather_result"]

def get_news(topic: str, ctx: ToolContext) -> str:
    ctx.state["news_result"] = fetch_news(topic)
    return ctx.state["news_result"]
```

---

## Gotchas

- `InMemorySessionService` has **no locks** -- concurrent writes to the same session silently lose data. Use `DatabaseSessionService` in production.
- SQLite with `DatabaseSessionService` is only safe within a single process. Cross-process writes can corrupt data because SQLite does not support `SELECT FOR UPDATE`.
- Parallel tools that write the same state key hit `deep_merge_dicts` last-write-wins. Always use distinct state keys per tool.
- `asyncio.gather` for tools does **not** use `return_exceptions=True` -- one failure re-raises while other tools keep running in the background (potential resource leak).
- `ToolThreadPoolConfig` shares `InvocationContext`/`ToolContext` with the main loop, but these objects are **not thread-safe**. Accessing them from pool workers is undefined behavior.
- Async tools in the thread pool get a brand-new event loop per worker -- they cannot share asyncio primitives with the main loop.
- The thread pool is global and process-wide; it is never destroyed.

---

## Related

- [Request Lifecycle](01-request-lifecycle.md) — full traced request showing where session calls happen
- [Sessions](08-sessions.md) — session state model and storage backends
- [Session Service Lifecycle](18-session-lifecycle.md) — detailed `append_event` flow and state delta mechanics
- [Error Reference](16-error-reference.md) — what happens when tool or model calls fail mid-execution
- [Apps](10-apps.md) — plugins are configured in `App` and execute sequentially
