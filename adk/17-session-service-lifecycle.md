# Session Service Lifecycle — How ADK Persists Every Turn

**Source:** [`runners.py`](../adk-python/src/google/adk/runners.py) · [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) · [`sessions/in_memory_session_service.py`](../adk-python/src/google/adk/sessions/in_memory_session_service.py) · [`sessions/database_session_service.py`](../adk-python/src/google/adk/sessions/database_session_service.py)

---

## What It Is

The session service is ADK's durability backbone. It loads context before agent execution, persists every meaningful event during execution, and commits state mutations atomically with their triggering events. This document traces **every call** the Runner makes to the session service, explains the state management model, and provides guidance on **optimizing for latency** when strong persistence guarantees are not required.

---

## The BaseSessionService Interface

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
        return event                          # 1. Skip partial events (never persisted)
    self._apply_temp_state(session, event)    # 2. Write temp:* keys to in-memory session
    event = self._trim_temp_delta_state(event) # 3. Remove temp:* from persisted delta
    self._update_session_state(session, event) # 4. Apply remaining delta to session.state
    session.events.append(event)              # 5. Append event to in-memory event list
    return event
```

**Why temp state is special:** `temp:`-prefixed keys are written to the in-memory session so downstream agents in the same invocation can read them, but they are trimmed from `state_delta` before persistence — they vanish on session reload.

---

## Complete Call Timeline in the Runner

For a standard `run_async` invocation, here is every point where the session service is called:

```
 ┌─ run_async() ──────────────────────────────────────────────────┐
 │                                                                 │
 │  1. get_session()          ← Load session + history from store  │
 │  2. [create_session()]     ← Only if not found & auto_create    │
 │  3. append_event(user_msg) ← Persist user's input message       │
 │                                                                 │
 │  ┌─ agent execution loop ──────────────────────────────────┐    │
 │  │  4. append_event(agent) ← For EACH non-partial event    │    │
 │  │  5. append_event(agent) ← Repeated for every yield      │    │
 │  │  ...                                                     │    │
 │  └──────────────────────────────────────────────────────────┘    │
 │                                                                 │
 │  6. [append_event(plugin)] ← If plugin short-circuits           │
 │  7. [append_event(rewind)] ← If rewind_async() is called       │
 │  8. [compaction]           ← Optional post-invocation           │
 │                                                                 │
 └─────────────────────────────────────────────────────────────────┘
```

### Call 1: `get_session` — Fetch session at invocation start

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

### Call 2: `create_session` — Auto-create if missing

**Where:** `_get_or_create_session()`, only when `auto_create_session=True` and `get_session` returned `None`.

```python
session = await self.session_service.create_session(
    app_name=self.app_name, user_id=user_id, session_id=session_id
)
```

**Why:** Convenience for development/testing. In production, sessions are typically pre-created. If missing and auto-create is disabled, `SessionNotFoundError` is raised.

### Call 3: `append_event` — Persist the user's input message

**Where:** `_append_new_message_to_session()` (called from `_handle_new_message`)

```python
await self.session_service.append_event(session=session, event=event)
```

The event has `author='user'` and carries the user's `new_message` content plus any caller-provided `state_delta`.

**Why:** The user's message must be persisted *before* the agent runs, so it appears in the conversation history that the LLM sees.

### Call 4+: `append_event` — Persist each agent-generated event

**Where:** `_exec_with_plugin()`, inside the event iteration loop.

```python
if event.partial is not True:
    await self.session_service.append_event(session=session, event=event)
```

**Why:** Every non-partial event (model responses, function calls, function responses, state changes, agent transfers) must be persisted so that: (a) history is durable, (b) state mutations are committed, and (c) the session can be resumed later.

**This is the hot path.** A single user turn can generate 5–20+ events (think: model response → tool call → tool result → model response → another tool call → ...). Each one is an `await` on the session service.

### Call 5: `append_event` — Plugin early exit

**Where:** `_exec_with_plugin()`, when `before_run` callback returns content.

### Call 6: `append_event` — Rewind

**Where:** `rewind_async()` — creates a special event with `rewind_before_invocation_id` and a computed `state_delta` that reverses previous state changes.

---

## How State Gets Committed

### State Scoping

The `State` class defines three prefixes:

| Prefix | Scope | Persistence |
|--------|-------|-------------|
| *(none)* | Session-level | Persisted per session |
| `app:` | App-level | Shared across all sessions for the app |
| `user:` | User-level | Shared across all sessions for a user |
| `temp:` | Invocation-level | In-memory only, never persisted |

### The Delta Flow

```
Agent code sets state              State._delta accumulates
  ctx.state["key"] = val    →     EventActions.state_delta["key"] = val
                                          │
                                          ▼
                                  session_service.append_event()
                                          │
                                          ▼
                              base: _apply_temp_state() → _trim_temp_delta_state()
                                   → _update_session_state() → session.events.append()
                                          │
                                          ▼
                              subclass: write to storage (memory / database)
```

---

## InMemorySessionService vs DatabaseSessionService

| Aspect | InMemorySessionService | DatabaseSessionService |
|--------|----------------------|----------------------|
| **Storage** | Python dicts in memory | SQLAlchemy async engine (SQLite, MySQL, PostgreSQL) |
| **Persistence** | Lost on process restart | Durable across restarts |
| **Concurrency** | No locking (not production-safe) | Per-session asyncio locks + DB row-level locking |
| **Session retrieval** | Returns `copy.deepcopy()` of stored session | Fresh object from DB query |
| **State decomposition** | Three separate dicts: `sessions`, `user_state`, `app_state` | Separate DB tables/columns for app, user, session state |
| **Event filtering** | In-memory slicing | SQL WHERE clauses |
| **append_event cost** | ~microseconds (dict update + deepcopy overhead) | ~milliseconds (DB round-trip + locking) |

---

## Optimizing for Latency (When Persistence Is Not Critical)

If you're okay losing all state on failure — e.g., chatbots, demos, internal tools, stateless interactions — the default `append_event`-on-every-event model is unnecessarily expensive. Here are the strategies, ranked from simplest to most aggressive:

### Strategy 1: Use InMemorySessionService (Baseline)

```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="my_app", session_service=session_service)
```

**Latency savings:** Eliminates all DB I/O. `append_event` becomes a dict update (~microseconds).

**Trade-off:** State lost on process restart. No cross-process session sharing. Still does `copy.deepcopy` on `get_session` which can be costly for large sessions.

**When to use:** This is the right default if you don't need durable sessions. Most demos and development workflows should start here.

### Strategy 2: Limit Event History with `GetSessionConfig`

```python
from google.adk.sessions import GetSessionConfig

run_config = RunConfig(
    get_session_config=GetSessionConfig(num_recent_events=20)
)
```

**Latency savings:** Reduces the amount of data loaded into the session on each invocation. Smaller sessions mean faster `get_session` and smaller LLM context.

**Trade-off:** Older events are not visible to the agent. For database-backed services, the events still exist in storage.

**When to use:** Always. Even with InMemorySessionService, limiting event history prevents unbounded memory growth.

### Strategy 3: Write a No-Op or Batched Session Service

If `InMemorySessionService` is still too heavy (e.g., the `deepcopy` on `get_session` is showing up in profiles), write a minimal subclass:

```python
from google.adk.sessions import InMemorySessionService, Session
from google.adk.events import Event

class FastSessionService(InMemorySessionService):
    """Session service optimized for latency over durability.

    - Skips deepcopy on get_session (caller and storage share the same object)
    - State still works correctly through the normal append_event flow
    """

    async def get_session(self, *, app_name, user_id, session_id, config=None):
        # Skip the deepcopy — return the storage session directly
        # Safe when only one Runner uses this session at a time
        app_sessions = self.sessions.get(app_name, {})
        user_sessions = app_sessions.get(user_id, {})
        session = user_sessions.get(session_id)
        if session is None:
            return None
        # Still merge scoped state
        merged_state = {}
        merged_state.update(self.app_state.get(app_name, {}))
        merged_state.update(self.user_state.get(app_name, {}).get(user_id, {}))
        merged_state.update(session.state)
        session.state = merged_state
        return session
```

**Latency savings:** Eliminates `deepcopy` overhead, which is O(n) on the number of events and state entries. For sessions with 100+ events, this can save 1–10ms per `get_session` call.

**Trade-off:** The Runner and the storage share the same object. Safe if only one coroutine uses the session at a time (which is the normal case).

### Strategy 4: Batch append_event Writes (Database-Backed Only)

If you must use a database but want lower latency, batch event writes:

```python
class BatchingDatabaseSessionService(DatabaseSessionService):
    """Buffers events in memory and flushes to DB periodically or at invocation end."""

    def __init__(self, *args, flush_interval: int = 10, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer: dict[str, list[Event]] = {}
        self._flush_interval = flush_interval

    async def append_event(self, session: Session, event: Event) -> Event:
        # Still update in-memory state (critical for agent correctness)
        event = await BaseSessionService.append_event(self, session=session, event=event)

        # Buffer the event instead of writing to DB immediately
        key = f"{session.app_name}:{session.user_id}:{session.id}"
        self._buffer.setdefault(key, []).append(event)

        if len(self._buffer[key]) >= self._flush_interval:
            await self._flush(session)
        return event

    async def _flush(self, session: Session):
        key = f"{session.app_name}:{session.user_id}:{session.id}"
        events = self._buffer.pop(key, [])
        if events:
            # Write all buffered events in a single DB transaction
            async with self._engine.begin() as conn:
                for event in events:
                    # ... insert event rows ...
                    pass
```

**Latency savings:** Turns N database round-trips into 1. For a 10-event turn, this can save 50–200ms depending on DB latency.

**Trade-off:** Events are only durable after flush. A crash between flushes loses buffered events.

### Strategy 5: Fire-and-Forget append_event (Most Aggressive)

If you truly don't care about persistence and want the absolute lowest latency:

```python
import asyncio
from google.adk.sessions import BaseSessionService, Session
from google.adk.events import Event

class FireAndForgetSessionService(BaseSessionService):
    """Maintains state in-memory only. append_event never blocks on I/O."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    async def create_session(self, *, app_name, user_id, state=None, session_id=None):
        session_id = session_id or str(uuid.uuid4())
        session = Session(
            app_name=app_name, user_id=user_id, id=session_id,
            state=state or {}, events=[], last_update_time=time.time()
        )
        self._sessions[session_id] = session
        return session

    async def get_session(self, *, app_name, user_id, session_id, config=None):
        return self._sessions.get(session_id)

    async def list_sessions(self, *, app_name, user_id=None):
        # Minimal implementation
        return ListSessionsResponse(sessions=[
            s for s in self._sessions.values()
            if s.app_name == app_name and (user_id is None or s.user_id == user_id)
        ])

    async def delete_session(self, *, app_name, user_id, session_id):
        self._sessions.pop(session_id, None)

    async def append_event(self, session: Session, event: Event) -> Event:
        # Only do the in-memory state bookkeeping — no I/O, no copies
        return await super().append_event(session=session, event=event)
```

**Latency savings:** `append_event` is pure in-memory dict operations. No deepcopy, no storage sync, no locking. This is the theoretical minimum.

**Trade-off:** No separate storage copy at all. `get_session` returns the live object. Only safe for single-session-per-process usage.

---

## Decision Guide: Which Strategy to Use

```
Need durable sessions across restarts?
├── Yes → DatabaseSessionService
│         ├── Latency-sensitive? → Strategy 4 (batching)
│         └── Not latency-sensitive? → Default DatabaseSessionService
└── No
    ├── Multi-process / shared sessions?
    │   └── Yes → DatabaseSessionService with batching (Strategy 4)
    └── No (single process)
        ├── Need simplicity? → Strategy 1 (InMemorySessionService)
        ├── Large sessions (100+ events)? → Strategy 3 (skip deepcopy)
        └── Maximum throughput? → Strategy 5 (fire-and-forget)
```

**The most common production-friendly low-latency setup:** InMemorySessionService (Strategy 1) + `GetSessionConfig(num_recent_events=20)` (Strategy 2). This gives you sub-millisecond `append_event` with bounded memory.

---

## Locking and Concurrency

### InMemorySessionService

No locking. The class docstring says: *"not suitable for multi-threaded production environments."* `copy.deepcopy` on `get_session` prevents accidental mutation of internal storage, but concurrent writes will race.

### DatabaseSessionService

Two layers:

1. **In-process asyncio locks** via `_with_session_lock()` — keyed by `(app_name, user_id, session_id)`, reference-counted
2. **Database row-level locking** — `SELECT ... FOR UPDATE` on MySQL/PostgreSQL; SQLite uses file-level locking
3. **Timestamp comparison** — detects if the session was modified between initial load and append, triggers a reload

**Cross-process:** Only the database locking protects across processes. The asyncio locks are per-process only.

---

## Cross-References

- [06-sessions.md](06-sessions.md) — Session data model, state scoping, service interface
- [03-runners.md](03-runners.md) — Runner lifecycle and how it orchestrates session calls
- [01-events.md](01-events.md) — Event structure and EventActions (state_delta)
- [request-lifecycle.md](request-lifecycle.md) — Full traced request showing session service calls in context
- [08-apps.md](08-apps.md) — Compaction (which also appends events post-invocation)
