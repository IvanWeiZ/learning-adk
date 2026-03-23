# 17 — Concurrency: Thread Safety & Parallel Tools

> **Official docs:** [Runtime](https://google.github.io/adk-docs/runtime/) | **Source:** [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) · [`functions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/functions.py) · [`sessions/database_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/database_session_service.py) · [`sessions/in_memory_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/in_memory_session_service.py) · [`agents/parallel_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/parallel_agent.py) | **Prereqs:** [08-sessions.md](08-sessions.md), [09-tools.md](09-tools.md)

---

## At a Glance

```
Runner is stateless — safe to share across concurrent requests.

Safety depends on session service + session_id:
├─ Different session_id → always safe (no shared state)
├─ Same session_id + DatabaseSessionService → safe (asyncio lock + DB row lock)
├─ Same session_id + InMemorySessionService → NOT safe (no locks, data race)
└─ Same session_id + SqliteSessionService → NOT safe (no application-level locks)

Danger zones:
├─ Parallel tools writing same state key → last-write-wins (silent data loss)
└─ Thread-pool tools accessing ToolContext → not thread-safe
```

ADK is async-first and generally safe for concurrent requests across different sessions. The main danger zones are: (1) concurrent writes to the same session with `InMemorySessionService`, (2) parallel tools writing the same state key, and (3) thread-pool tools accessing non-thread-safe `ToolContext`. Understanding these boundaries lets you scale safely.

---

## Class Hierarchy

```
SessionService
 ├── InMemorySessionService   (no locks — not production-safe for concurrency)
 ├── DatabaseSessionService   (asyncio lock + DB row lock — production-safe)
 └── SqliteSessionService     (no locks — relies on SQLite's own file locking only)

ParallelAgent (agents/parallel_agent.py — runs sub-agents concurrently)

 ToolThreadPoolConfig (opt-in thread pool for sync/async tools)
```

---

## Key API

### What's Safe

| Operation | Safe? | Notes |
|---|---|---|
| Same `Runner`, different `session_id` | Yes | Runner is stateless |
| Same `Runner`, same `session_id` with `DatabaseSessionService` (MySQL/MariaDB/PostgreSQL) | Yes | DB lock serializes `append_event` |
| Same `Runner`, same `session_id` with `InMemorySessionService` | No | No locks, last writer wins, silent data loss |
| Same `Runner`, same `session_id` with `SqliteSessionService` | No | No application-level locks; concurrent writes risk data loss |
| Sharing `Agent` instances across invocations | Yes | Agents are pure config (Pydantic models) |
| Sharing `Session` objects across invocations | No | Let session service return fresh copies |
| Parallel tools writing same state key | No | `deep_merge_dicts` uses last-write-wins |
| `ToolThreadPoolConfig` + tools accessing `ToolContext` | No | Shared objects not thread-safe |

---

## How It Works

### Parallel Tool Execution

```
Parallel Tool Execution — Happy Path:
│
├── LLM returns two FunctionCalls in one response
│      FunctionCall("get_weather", {"city": "Tokyo"})
│      FunctionCall("get_news", {"topic": "tech"})
│
├── ADK runs both concurrently via asyncio.gather()
│      get_weather runs (200ms)
│      get_news runs (300ms)
│      total wall time: 300ms (not 500ms)
│
└── Results merged into single FunctionResponse event
       both results sent back to LLM in next loop iteration


Collision Scenario — both tools write same state key:
│
├── Tool A finishes first
│      ctx.state["result"] = "sunny"
│
├── Tool B finishes second
│      ctx.state["result"] = "breaking news"
│
└── deep_merge_dicts → last write wins
       state["result"] = "breaking news"
       Tool A's write is silently lost!

 Fix: use different state keys per tool
```

`functions.py` dispatches multiple tool calls via `asyncio.gather`:

- All tool coroutines launch concurrently.
- `return_exceptions=True` is **not** used — one failing tool raises immediately. The remaining coroutines are **not** cancelled; they continue running to completion in the background (potential resource leak).
- State deltas from parallel tools are merged via `deep_merge_dicts`. On key conflicts the last-merged tool's value wins silently.

### Session Locking

#### DatabaseSessionService — Two-Layer Locking

1. **In-process asyncio lock** keyed by `(app_name, user_id, session_id)` with reference counting. Ensures only one coroutine within a single process touches a session at a time.
2. **Database row-level locking** (`SELECT FOR UPDATE`) on MySQL, MariaDB, and PostgreSQL. SQLite does not support this, so cross-process safety is not guaranteed with SQLite.
3. **Staleness detection:** primarily compares `_storage_update_marker` (an exact revision marker set by `DatabaseSessionService`). Falls back to `update_time` timestamps for marker-less sessions. Raises `ValueError` if the session is stale (does not auto-reload).

#### InMemorySessionService — No Locking

- The docstring is explicit: "not suitable for multi-threaded production environments."
- `get_session` returns a `copy.deepcopy` of the stored session, preventing callers from mutating internal storage directly.
- Concurrent `append_event` calls are a data race -- no synchronization exists.

### Plugin Execution

Plugins run strictly sequentially. `close` is also sequential (anyio/MCP compatibility).

### ParallelAgent

- Each sub-agent gets an isolated `InvocationContext` with unique `branch`.
- Events serialize via `asyncio.Queue` + resume-signal (an `asyncio.Event` that notifies the parent when a sub-agent yields).
- Sub-agents share one `Session`; event delivery is serialized through the queue.
- **Known race:** parallel sub-agents that write the same `output_key` produce a last-write-wins result.

### Thread Pool (ToolThreadPoolConfig)

```
ToolThreadPoolConfig — sync vs async tool execution paths
│
├── ToolThreadPoolConfig NOT set (default)
│   ├── Sync tool
│   │   └── Called directly (blocks the event loop until it returns!)
│   └── Async tool
│       └── Runs directly as coroutine in main event loop
│
└── ToolThreadPoolConfig SET (opt-in thread pool)
    ├── Sync tool
    │   └── Submitted to ThreadPoolExecutor (keyed by max_workers — different
    │       │   max_workers values create separate pools)
    │       └── Runs in worker thread directly
    │       └── ToolContext shared with main loop (NOT thread-safe!)
    │
    └── Async tool
        └── Submitted to ThreadPoolExecutor (same pool lookup by max_workers)
            └── Brand-new event loop created per worker thread
            └── Cannot share asyncio primitives (locks, queues) with main loop
            └── ToolContext shared with main loop (NOT thread-safe!)
```

> **Warning:** `ToolContext` is shared with the main event loop but is **not thread-safe**. Accessing it from pool workers is undefined behavior. Pools are process-wide (keyed by `max_workers`) and never destroyed.

---

## Examples

```python
# Safe: different sessions, same runner
runner = Runner(agent=my_agent, app_name="myapp",
                session_service=DatabaseSessionService(db_url))

# These can run concurrently without issues:
await asyncio.gather(
    process_request(runner, user_id="u1", session_id="s1"),
    process_request(runner, user_id="u2", session_id="s2"),
)

# Unsafe: same session with InMemorySessionService
# Both writes race — one will silently lose events
```

```python
# BAD: both tools write same key — last-write-wins, one result silently lost
def get_weather(city: str, ctx: ToolContext) -> str:
    ctx.state["result"] = fetch_weather(city)  # overwritten by get_news!
    return ctx.state["result"]

def get_news(topic: str, ctx: ToolContext) -> str:
    ctx.state["result"] = fetch_news(topic)  # overwrites weather!
    return ctx.state["result"]

# GOOD: distinct keys per tool
def get_weather(city: str, ctx: ToolContext) -> str:
    ctx.state["weather_result"] = fetch_weather(city)
    return ctx.state["weather_result"]

def get_news(topic: str, ctx: ToolContext) -> str:
    ctx.state["news_result"] = fetch_news(topic)
    return ctx.state["news_result"]
```

---

## Related

- [Request Lifecycle](01-request-lifecycle.md) — full traced request showing where session calls happen
- [Sessions](08-sessions.md) — session state model and storage backends
- [Session Service Lifecycle](18-session-lifecycle.md) — detailed `append_event` flow and state delta mechanics
- [Error Reference](16-error-reference.md) — what happens when tool or model calls fail mid-execution
- [Apps](10-apps.md) — plugins are configured in `App` and execute sequentially
