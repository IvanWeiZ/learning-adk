# 18 — Session Lifecycle: Service Timeline

> **Official docs:** [Sessions](https://google.github.io/adk-docs/sessions/) | **Source:** [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) · [`sessions/base_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/base_session_service.py) · [`sessions/in_memory_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/in_memory_session_service.py) · [`sessions/database_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/database_session_service.py) | **Prereqs:** [08-sessions.md](08-sessions.md), [03-runners.md](03-runners.md), [07-events.md](07-events.md)

## At a Glance

```
 ┌─ run_async() ──────────────────────────────────────────────────┐
 │                                                                │
 │ 1. get_session()       ← Load session + history from store     │
 │ 2. [create_session()]  ← Only if not found & auto_create       │
 │ 3. append_event(user)  ← Persist user's input message          │
 │                                                                │
 │ ┌─ agent execution loop ──────────────────────────────────┐    │
 │ │ 4+. append_event(agent) — one per non-partial event     │    │
 │ └──────────────────────────────────────────────────────────┘    │
 │                                                                │
 │ [append_event(plugin)]  ← If plugin short-circuits             │
 │ [append_event(rewind)]  ← If rewind_async() is called          │
 │ [compaction]            ← Optional post-invocation             │
 │                                                                │
 └────────────────────────────────────────────────────────────────┘
```

The session service loads context before execution, persists events during execution, and commits state mutations atomically. This document traces every Runner call to the session service and provides latency optimization guidance.

---

## How It Works

### The BaseSessionService Interface

`BaseSessionService` defines 5 methods — 4 abstract, 1 concrete with a default implementation:

| Method | Abstract? | Signature | Contract |
|--------|-----------|-----------|----------|
| `create_session` | Yes | `async def create_session(*, app_name, user_id, state=None, session_id=None) -> Session` | Creates a new session. Generates an ID if not provided. |
| `get_session` | Yes | `async def get_session(*, app_name, user_id, session_id, config=None) -> Optional[Session]` | Retrieves a session. Returns `None` if not found. `GetSessionConfig` can filter by `num_recent_events` or `after_timestamp`. |
| `list_sessions` | Yes | `async def list_sessions(*, app_name, user_id=None) -> ListSessionsResponse` | Lists sessions. Events and states are **not** populated. |
| `delete_session` | Yes | `async def delete_session(*, app_name, user_id, session_id) -> None` | Deletes a session. |
| `append_event` | No (concrete) | `async def append_event(session, event) -> Event` | Appends an event to the session. Has a default implementation that subclasses call via `super()`. |

### The `append_event` Base Implementation

This is the critical method. Every subclass calls `super().append_event()` first:

```python
async def append_event(self, session: Session, event: Event) -> Event:
    if event.partial:
        return event # 1. Skip partial events (never persisted)
    self._apply_temp_state(session, event) # 2. Write temp:* keys to in-memory session
    event = self._trim_temp_delta_state(event) # 3. Remove temp:* from persisted delta
    self._update_session_state(session, event) # 4. Apply remaining delta to session.state
    session.events.append(event) # 5. Append event to in-memory event list
    return event
```

**Why temp state is special:** `temp:`-prefixed keys are written to the in-memory session so downstream agents in the same invocation can read them, but they are trimmed from `state_delta` before persistence — they vanish on session reload.

### Complete Call Timeline in the Runner

For a standard `run_async` invocation, here is every point where the session service is called:

**Call 1: `get_session` — Fetch session at invocation start**

**Where:** `_get_or_create_session()` (called from `run_async` inside `_run_with_trace`)

```python
session = await self.session_service.get_session(
    app_name=self.app_name,
    user_id=user_id,
    session_id=session_id,
    config=get_session_config,
)
```

**Why:** The Runner is stateless. Every invocation begins by loading the session (history + state) from the session service. `GetSessionConfig` (from `run_config`) controls how much history is loaded (e.g., `num_recent_events` to limit the context window).

**Call 2: `create_session` — Auto-create if missing**

**Where:** `_get_or_create_session()`, only when `auto_create_session=True` and `get_session` returned `None`.

```python
session = await self.session_service.create_session(
    app_name=self.app_name, user_id=user_id, session_id=session_id
)
```

**Why:** Convenience for development/testing. In production, sessions are typically pre-created. If missing and auto-create is disabled, `SessionNotFoundError` is raised.

**Call 3: `append_event` — Persist the user's input message**

**Where:** `_append_new_message_to_session()` (called from `_handle_new_message`)

```python
await self.session_service.append_event(session=session, event=event)
```

The event has `author='user'` and carries the user's `new_message` content plus any caller-provided `state_delta`.

**Why:** The user's message must be persisted *before* the agent runs, so it appears in the conversation history that the LLM sees.

**Call 4+: `append_event` — Persist each agent-generated event**

**Where:** `_exec_with_plugin()`, inside the event iteration loop.

```python
if event.partial is not True:
    await self.session_service.append_event(session=session, event=event)
```

**Why:** Every non-partial event (model responses, function calls, function responses, state changes, agent transfers) must be persisted so that: (a) history is durable, (b) state mutations are committed, and (c) the session can be resumed later.

**This is the hot path.** A single user turn can generate 5-20+ events (think: model response, tool call, tool result, model response, another tool call, ...). Each one is an `await` on the session service.

**Optional: append_event — plugin early exit**

**Where:** `_exec_with_plugin()`, when `before_run` callback returns content.

**Optional: append_event — rewind**

**Where:** `rewind_async()` — creates a special event with `rewind_before_invocation_id` and a computed `state_delta` that reverses previous state changes.

### How State Gets Committed

**State Scoping**

For state scoping rules, see [08-sessions.md](08-sessions.md). For state delta internals, see the `append_event` base implementation above.

### InMemorySessionService vs DatabaseSessionService

| Aspect | InMemorySessionService | DatabaseSessionService |
|--------|----------------------|----------------------|
| **Storage** | Python dicts in memory | SQLAlchemy async engine (SQLite, MySQL, PostgreSQL) |
| **Persistence** | Lost on process restart | Durable across restarts |
| **Concurrency** | No locking (not production-safe) | Per-session asyncio locks + DB row-level locking |
| **Session retrieval** | Returns `copy.deepcopy()` of stored session | Fresh object from DB query |
| **State decomposition** | Three separate dicts: `sessions`, `user_state`, `app_state` | Separate DB tables/columns for app, user, session state |
| **Event filtering** | In-memory slicing | SQL WHERE clauses |
| **append_event cost** | ~microseconds (dict update + deepcopy overhead) | ~milliseconds (DB round-trip + locking) |

### Locking and Concurrency

**InMemorySessionService**

No locking. The class docstring says: *"not suitable for multi-threaded production environments."* `copy.deepcopy` on `get_session` prevents accidental mutation of internal storage, but concurrent writes race.

**DatabaseSessionService**

Two layers:

1. **In-process asyncio locks** via `_with_session_lock()` — keyed by `(app_name, user_id, session_id)`, reference-counted
2. **Database row-level locking** — `SELECT ... FOR UPDATE` on MySQL/PostgreSQL; SQLite uses file-level locking
3. **Timestamp comparison** — detects if the session was modified between initial load and append, triggers a reload

**Cross-process:** Only the database locking protects across processes. The asyncio locks are per-process only.

For latency optimization strategies (session service, model selection, streaming, tools), see [18b-session-latency-optimization.md](18b-session-latency-optimization.md).

---

## Related

- [18b-session-latency-optimization.md](18b-session-latency-optimization.md) — Full latency optimization guide (session service, model selection, streaming, tools)
- [08-sessions.md](08-sessions.md) — Session data model, state scoping, service interface
- [03-runners.md](03-runners.md) — Runner lifecycle and how it orchestrates session calls
- [07-events.md](07-events.md) — Event structure and EventActions (state_delta)
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request showing session service calls in context
- [10-apps.md](10-apps.md) — Compaction (which also appends events post-invocation)
