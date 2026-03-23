# Session & Agent Latency Optimization

> **Official docs:** [Sessions](https://google.github.io/adk-docs/sessions/) | **Source:** [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) | **Prereqs:** [18-session-lifecycle.md](18-session-lifecycle.md), [08-sessions.md](08-sessions.md)

## Optimizing for Latency (When Persistence Is Not Critical)

If durability is not required, per-event persistence is overkill. Strategies ranked simplest to most aggressive:

**Strategy 1: Use InMemorySessionService (Baseline)**

```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="my_app", session_service=session_service)
```

Eliminates all DB I/O. `append_event` becomes ~microseconds.

Trade-off: state lost on restart, no cross-process sharing, `deepcopy` on `get_session` can be costly.

Default choice when durability is not needed.

**Strategy 2: Limit Event History with `GetSessionConfig`**

```python
from google.adk.sessions import GetSessionConfig

run_config = RunConfig(
    get_session_config=GetSessionConfig(num_recent_events=20)
)
```

Reduces data loaded per invocation. Smaller sessions = faster `get_session` + smaller LLM context.

Trade-off: older events invisible to agent (still exist in DB storage).

Always use. Prevents unbounded memory growth.

**Strategy 3: Write a No-Op or Batched Session Service**

If `InMemorySessionService` is still too heavy (e.g., the `deepcopy` on `get_session` is showing up in profiles), write a minimal subclass:

```python
from google.adk.sessions import InMemorySessionService, Session
from google.adk.events import Event

class FastSessionService(InMemorySessionService):
    """Session service optimized for latency over durability.

    - Skips deepcopy on get_session (caller and storage share the same object)
    - State still works correctly through the normal append_event flow
    """
    # WARNING: illustrative only — missing edge cases (absent app/user state dicts, error handling)

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

**Latency savings:** Eliminates `deepcopy` overhead, which is O(n) on the number of events and state entries. For sessions with 100+ events, this can save 1-10ms per `get_session` call.

**Trade-off:** The Runner and the storage share the same object. Safe if only one coroutine uses the session at a time (which is the normal case).

**Strategy 4: Batch append_event Writes (Database-Backed Only)**

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

**Latency savings:** Turns N database round-trips into 1. For a 10-event turn, this can save 50-200ms depending on DB latency.

**Trade-off:** Events are only durable after flush. A crash between flushes loses buffered events.

**Strategy 5: Fire-and-Forget append_event (Most Aggressive)**

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

### Decision Guide: Which Strategy to Use

```
Need durable sessions across restarts?
├── Yes → DatabaseSessionService
│   ├── Latency-sensitive? → Strategy 4 (batching)
│   └── Not latency-sensitive? → Default DatabaseSessionService
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

## Beyond Session Service: Full-Stack Latency Optimization

Session service is only one source of latency. The full critical path for a single user turn, with the dominant costs:

```
 Critical path for a single user turn (in time order):
 │
 ├── get_session
 │      ~1ms (in-memory)
 │
 ├── append_event(user message)
 │      ~0.1ms
 │
 ├── LLM call #1
 │      500-3000ms  ← dominant cost
 │
 ├── tool execution
 │      10-500ms
 │
 ├── LLM call #2
 │      500-3000ms  ← dominant cost
 │
 └── append_event x N (agent events)
        ~0.3ms total

 LLM calls = 80-95% of total time.
 Takeaway: optimize MODEL calls first. Session I/O barely matters.
```

LLM calls dominate latency. Session I/O only matters with database backends.

**1. Model Selection (Biggest Single Lever)**

LLM calls are 80-95% of total latency.

| Model | Typical TTFT | Typical Total | When to Use |
|-------|-------------|---------------|-------------|
| `gemini-2.5-flash` | ~200ms | ~500-1500ms | Default — fast and capable |
| `gemini-2.5-pro` | ~500ms | ~1000-3000ms | Complex reasoning only |
| `claude-haiku-4-20250514` | ~300ms | ~800-2000ms | Fast Anthropic option |
| `claude-sonnet-4-20250514` | ~500ms | ~1500-4000ms | High quality, slower |

```python
# Use the fastest model that's good enough
agent = LlmAgent(model="gemini-2.5-flash", ...)
```

**Tip:** Use a fast model for routing/triage agents, save expensive models for the final response agent.

**2. Streaming (Reduce Perceived Latency)**

ADK streams by default. Partial events improve perceived responsiveness (TTFT) without reducing total latency.

```python
async for event in runner.run_async(...):
    if event.partial:
        print(event.content.parts[0].text, end='', flush=True) # stream to UI
    # partial events are NOT passed to append_event (skipped automatically)
```

Partial events are free: `append_event` skips them. Only the final event is persisted.

**3. Reduce LLM Round-Trips (Tool Call Batching)**

Each tool call adds an LLM round-trip. 3 sequential tool calls = 4 LLM calls.

Modern models return multiple `FunctionCall`s in one response. ADK executes all before looping back.

```python
# The LLM can return multiple function calls in one response:
# FunctionCall(name='get_weather', args={'city': 'Tokyo'})
# FunctionCall(name='get_weather', args={'city': 'London'})
# → Both run, results sent back to LLM in one shot → 2 round-trips instead of 3
```

**What you can do:**
- Write tool descriptions that encourage the LLM to batch calls
- Use `output_schema` to force structured output when you don't need tool use
- Reduce the number of tools visible to the agent (fewer tools = faster LLM decisions)

**4. Minimize Tool Execution Time**

Tools are awaited in the flow loop. A slow tool blocks the turn.

```python
# BAD: slow tool blocks the LLM loop
async def search_database(query: str) -> list[dict]:
    return await slow_db_query(query) # 500ms

# BETTER: pre-warm connections, add caching
from functools import lru_cache

_db_pool = None # connection pool initialized once

async def search_database(query: str, tool_context: ToolContext) -> list[dict]:
    global _db_pool
    if _db_pool is None:
        _db_pool = await create_pool()
    # Use cached result if same query was made recently
    cache_key = f"search:{query}"
    if cached := tool_context.state.get(f"temp:{cache_key}"):
        return cached
    result = await _db_pool.fetch(query)
    tool_context.state[f"temp:{cache_key}"] = result # temp: = not persisted
    return result
```

**For I/O-heavy tools:** Consider `LongRunningFunctionTool` which returns immediately with a pending status and completes asynchronously.

**5. Limit Conversation History**

More events = larger prompt = slower LLM calls.

```python
# Limit what the LLM sees
run_config = RunConfig(
    get_session_config=GetSessionConfig(num_recent_events=20)
)

# Or use compaction to summarize old events
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
app = App(
    name="my_app",
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5, overlap_size=1
    ),  # auto-summarize periodically
)
```

**Impact:** Reducing from 100 events to 20 can cut LLM latency by 30-50% (fewer input tokens).

**6. Simplify Instructions and Tool Schemas**

Large instructions slow preprocessing and LLM calls.

```python
# BAD: huge instruction with many tools
agent = LlmAgent(
    instruction="You are an agent that can... [2000 words]...",
    tools=[tool1, tool2, ..., tool20], # 20 tool schemas in the prompt
)

# BETTER: focused agent with minimal tools
agent = LlmAgent(
    instruction="Answer weather questions using the get_weather tool.",
    tools=[get_weather], # 1 tool schema
)
```

Fewer tools = faster LLM. Route to specialized sub-agents with small tool sets.

**7. Skip Callbacks You Don't Need**

Callbacks are awaited sequentially:

```
before_agent_callback → before_model_callback → [LLM] → after_model_callback
→ before_tool_callback → [tool] → after_tool_callback → after_agent_callback
```

Unset callbacks are fast no-ops. Non-None callbacks add latency if they do I/O.

```python
# Only set callbacks you actually need
agent = LlmAgent(
    # before_model_callback=None, # default — no overhead
    # after_model_callback=None, # default — no overhead
    before_tool_callback=my_auth_check, # only if needed
)
```

**8. Avoid Unnecessary Agent Transfers**

Each agent transfer re-runs all preprocessors and makes a new LLM call.

```
User → Router Agent (LLM call #1) → transfer → Weather Agent (LLM call #2)
                                                → tool call → LLM call #3
```

3 LLM calls vs 2. Skip the router if one agent suffices.

**9. Use `SingleFlow` When Possible**

`AutoFlow` checks for transfers on every response. Force `SingleFlow` for non-transferring agents:

```python
agent = LlmAgent(
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    sub_agents=[], # no sub-agents
    # → ADK auto-selects SingleFlow
)
```

**10. Disable Compaction for Short-Lived Sessions**

Compaction runs post-invocation to summarize old events. Skip for short-lived sessions:

```python
# Don't wrap in App if you don't need plugins
runner = Runner(agent=agent, app_name="my_app", session_service=session_service)
# Instead of:
# app = App(name="my_app", root_agent=agent, plugins=[...])
# runner = Runner(app=app, session_service=session_service)
```

---

## Latency Optimization Cheat Sheet

| Optimization | Latency Saved | Effort | When |
|---|---|---|---|
| Use `gemini-2.5-flash` | 500-2000ms/call | Config change | Always (unless quality demands more) |
| `num_recent_events=20` | 30-50% of LLM time | Config change | Always |
| `InMemorySessionService` | 5-200ms/event | Config change | When persistence not needed |
| Fewer tools per agent | 100-500ms/call | Architecture | When >5 tools |
| Parallel tool calls | Saves 1 LLM round-trip | Prompt engineering | Multiple independent tools |
| Skip unnecessary callbacks | 1-50ms/callback | Config change | Always |
| `SingleFlow` (no transfers) | ~0 (avoids overhead) | Config change | No sub-agents |
| Short instructions | 50-200ms/call | Rewrite | Verbose prompts |
| Cache tool results with `temp:` | Tool-dependent | Code change | Repeated tool calls |
| Fire-and-forget session service | ~0.1ms/event | Custom class | Max throughput |

**Priority order:** Model selection > history limits > session service > tool design > everything else.

---

## Related

- [18-session-lifecycle.md](18-session-lifecycle.md) — Session service call timeline and `append_event` internals
- [08-sessions.md](08-sessions.md) — Session data model, state scoping, service interface
- [20b-debugging-guide.md](20b-debugging-guide.md) — Debugging checklist, performance profiling
