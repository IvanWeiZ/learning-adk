# Sessions — Conversation History & State

**Source:** [`sessions/session.py`](../adk-python/src/google/adk/sessions/session.py) · [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) · [`sessions/in_memory_session_service.py`](../adk-python/src/google/adk/sessions/in_memory_session_service.py)

---

## What It Is

A `Session` is one conversation thread. Stores:
- The full ordered list of `Event`s (conversation history)
- A mutable `state` dict (arbitrary key-value data persisted across turns)

`BaseSessionService` provides CRUD. Agents access sessions only through `InvocationContext`.

---

## Session Data Model

```python
class Session(BaseModel):
    id: str # unique session ID
    app_name: str # which app this session belongs to
    user_id: str # which user owns this session
    state: dict[str, Any] # arbitrary persistent state (survives turns)
    events: list[Event] # full conversation history (ordered)
    last_update_time: float # unix timestamp of last update
```

Intentionally minimal. Complexity lives in the service and Event list.

---

## Session State

`session.state` is a free-form dict. Written via `EventActions.state_delta`:

```python
# In a tool or callback:
tool_context.state['user_name'] = 'Alice'
# → stored in event.actions.state_delta['user_name'] = 'Alice'
# → session_service applies the delta on append_event

# In LlmAgent:
agent = LlmAgent(output_key='summary')
# → final response text is saved to session.state['summary']
```

State is scoped:
- `'key'` — session-level (default)
- `'user:key'` — user-level (shared across all sessions for this user)
- `'app:key'` — app-level (shared across all sessions and users)

Scoping is handled by the session service implementations.

---

## BaseSessionService — The Interface

```python
class BaseSessionService(ABC):
    async def create_session(
        self, *, app_name, user_id, state=None, session_id=None
    ) -> Session

    async def get_session(
        self, *, app_name, user_id, session_id, config=None
    ) -> Optional[Session]
        # config: GetSessionConfig(num_recent_events=..., after_timestamp=...)

    async def list_sessions(
        self, *, app_name, user_id
    ) -> ListSessionsResponse

    async def delete_session(
        self, *, app_name, user_id, session_id
    ) -> None

    async def append_event(
        self, session: Session, event: Event
    ) -> Event
        # Applies event.actions.state_delta to session.state.
        # Assigns event.id if not set.
        # Returns the persisted event.
```

`append_event` is called by `Runner` after every event yielded by the agent.

---

## Implementations

| Class | Storage | Use Case |
|-------|---------|----------|
| `InMemorySessionService` | Python dict | Development, tests |
| `SQLiteSessionService` | SQLite file | Local persistence, single process |
| `DatabaseSessionService` | SQLAlchemy | Postgres, MySQL, production databases |
| `VertexAiSessionService` | Vertex AI managed | Cloud deployment with Vertex AI |

Same interface; swap backends by changing the `Runner` constructor argument.

---

## GetSessionConfig — Partial Loading

Load only recent events for long conversations:

```python
config = GetSessionConfig(
    num_recent_events=50, # only last 50 events
    after_timestamp=1700000000.0, # only events after this unix time
)
session = await session_service.get_session(..., config=config)
```

sessions have thousands of events but you only need recent context.

---

## How Runner Uses Sessions

```mermaid
sequenceDiagram
    participant R as Runner
    participant SS as SessionService
    participant A as Agent
    participant S as Session

    R->>SS: get_session(app_name, user_id, session_id)
    SS-->>R: Session (or SessionNotFoundError)

    R->>SS: append_event(session, user_event)
    SS->>S: Add event, apply state_delta

    R->>A: agent.run_async(ctx)

    loop For each yielded Event
        A-->>R: yield Event
        R->>SS: append_event(session, event)
        SS->>S: Add event, apply state_delta
        SS->>S: Persist to storage
    end

    Note over R: Optional: compaction (summarize old events)
```

**ASCII version:**

```
Runner.run_async(user_id, session_id, new_message)
│
├─ session_service.get_session(app_name, user_id, session_id)
│ └─ If not found: raise SessionNotFoundError (or auto-create if configured)
│
├─ Create user message Event, session_service.append_event(session, user_event)
│
├─ agent.run_async(ctx) → yields Events
│
├─ For each event:
│ └─ session_service.append_event(session, event)
│ → applies state_delta
│ → persists to storage
│
└─ (Optional) compaction: summarize old events, update session
```

---

## State Delta Lifecycle

```mermaid
sequenceDiagram
    participant Code as Your Code
    participant State as State Object
    participant EA as EventActions
    participant R as Runner
    participant SS as SessionService
    participant DB as Storage

    Code->>State: ctx.state["city"] = "Tokyo"
    State->>State: _delta["city"] = "Tokyo"
    State->>State: _value["city"] = "Tokyo" (immediately readable)

    Note over State,EA: When event is yielded
    State->>EA: event.actions.state_delta = {"city": "Tokyo"}

    Note over R,SS: Runner calls append_event
    R->>SS: append_event(session, event)
    SS->>SS: session.state["city"] = "Tokyo" (committed)
    SS->>DB: Persist to storage
```

**ASCII version:**

```
Your code EventActions Session Service
───────── ──────────── ───────────────

ctx.state["city"] = "Tokyo"
 │
 ▼
State._delta["city"] = "Tokyo"
State._value["city"] = "Tokyo" ← immediately readable
 │
 ▼ (when event is yielded)
event.actions.state_delta = {"city": "Tokyo"}
 │
 ▼ (Runner calls append_event)
session.state["city"] = "Tokyo" ← committed
 │
 ▼ (subclass persists)
Database/Memory store updated
```

## State Scope Visual

```mermaid
graph TD
    subgraph APP["app:config — shared by ALL users, ALL sessions"]
        subgraph USER["user:preferences — shared across ALL sessions for this user"]
            subgraph SESSION["count (session-scoped) — lives in THIS session only"]
                TEMP["temp:scratch — THIS invocation only, never persisted"]
            end
        end
    end

    style APP fill:#ffebee,stroke:#c62828
    style USER fill:#fff3e0,stroke:#ef6c00
    style SESSION fill:#e8f5e9,stroke:#2e7d32
    style TEMP fill:#e3f2fd,stroke:#1565c0
```

**ASCII version:**

```
┌─ app:config ──────────────────────────────────────────────────┐
│ Shared by ALL users, ALL sessions │
│ │
│ ┌─ user:preferences ──────────────────────────────────────┐ │
│ │ Shared across ALL sessions for this user │ │
│ │ │ │
│ │ ┌─ count (session-scoped) ──────────────────────────┐ │ │
│ │ │ Lives in THIS session only │ │ │
│ │ │ │ │ │
│ │ │ ┌─ temp:scratch ──────────────────────────────┐ │ │ │
│ │ │ │ THIS invocation only — never persisted │ │ │ │
│ │ │ └──────────────────────────────────────────────┘ │ │ │
│ │ └────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## State Scoping in Practice

```python
# Session-scoped (default) — only this session sees this:
tool_context.state['cart_items'] = [...]

# User-scoped — all sessions for this user see this:
tool_context.state['user:preferences'] = {'theme': 'dark'}

# App-scoped — every user in this app sees this:
tool_context.state['app:feature_flags'] = {'beta': True}
```

---

## Related Files

- [`sessions/session.py`](../adk-python/src/google/adk/sessions/session.py) — data model
- [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) — abstract interface
- [`sessions/in_memory_session_service.py`](../adk-python/src/google/adk/sessions/in_memory_session_service.py) — default for dev
- [`sessions/sqlite_session_service.py`](../adk-python/src/google/adk/sessions/sqlite_session_service.py) — local persistence
- [`sessions/database_session_service.py`](../adk-python/src/google/adk/sessions/database_session_service.py) — production DB
- [`sessions/state.py`](../adk-python/src/google/adk/sessions/state.py) — state scoping constants
- [19-session-security.md](19-session-security.md) — Session event security considerations
- [18-session-lifecycle.md](18-session-lifecycle.md) — Session service call timeline and optimization
