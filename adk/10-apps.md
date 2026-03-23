# 10 — Apps: Container & Plugins

> **Official docs:** [Runtime](https://google.github.io/adk-docs/runtime/) | **Source:** [`apps/app.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/app.py) · [`apps/compaction.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/compaction.py) · [`plugins/base_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/base_plugin.py) | **Prereqs:** [03-runners.md](03-runners.md), [04-agents.md](04-agents.md), [09-tools.md](09-tools.md)

## At a Glance

```
┌─────────────────────────────────────────────────────────┐
│                        App                               │
│  name, root_agent, plugins, configs                     │
│         │                                                │
│         ├── plugins: [BasePlugin, ...]                   │
│         │       └── 12 callbacks (see BasePlugin below)  │
│         │                                                │
│         ├── events_compaction_config                     │
│         │       └── summarize old events → 1 compact evt │
│         │                                                │
│         ├── context_cache_config                         │
│         │       └── cache static_instruction tokens      │
│         │                                                │
│         └── resumability_config                          │
│                 └── pause/resume long-running tools       │
│                                                          │
│         ▼                                                │
│  Runner(app=app, session_service=...)                    │
│         └── consumes all App config automatically        │
└─────────────────────────────────────────────────────────┘
```

`App` wraps your root agent with cross-cutting concerns — plugins, compaction, context caching, and resumability.

```python
# With App (production — enables all features):
runner = Runner(app=App(name='my_app', root_agent=agent), session_service=...)

# Without App (scripts/demos — no plugins, compaction, or caching):
runner = Runner(agent=agent, app_name='my_app', session_service=...)
```

| Feature | `app=App(...)` | `agent=..., app_name=...` |
|---------|---------------|--------------------------|
| Plugins | Yes | No |
| Compaction | Yes | No |
| Context cache | Yes | No |
| Resumability | Yes | No |

## Class Hierarchy

```
App (BaseModel):
│
├── name: str
├── root_agent: BaseAgent
├── plugins: list[BasePlugin]
├── events_compaction_config
├── context_cache_config
└── resumability_config

BasePlugin (ABC):
│
├── Runner-level callbacks:
│      on_user_message_callback()
│      before_run_callback()
│      on_event_callback()
│      after_run_callback()
│      close()
│
├── Agent-level callbacks:
│      before_agent_callback()
│      after_agent_callback()
│
├── Model-level callbacks:
│      before_model_callback()
│      after_model_callback()
│      on_model_error_callback()
│
└── Tool-level callbacks:
       before_tool_callback()
       after_tool_callback()
       on_tool_error_callback()

EventsCompactionConfig:
│
├── compaction_interval: int
├── overlap_size: int
└── summarizer: Optional

ContextCacheConfig:
│
├── cache_intervals: int
├── ttl_seconds: int
└── min_tokens: int

ResumabilityConfig:
│
└── is_resumable: bool
```

## Key API

### App Fields

```python
class App(BaseModel):
    name: str # app identifier (valid Python identifier)
    root_agent: BaseAgent # the root agent
    plugins: list[BasePlugin] = [] # app-level hooks
    events_compaction_config: Optional[EventsCompactionConfig] = None
    context_cache_config: Optional[ContextCacheConfig] = None
    resumability_config: Optional[ResumabilityConfig] = None
```

### BasePlugin Interface

12 event-driven callbacks plus `close()` (a lifecycle hook, not a callback — called when the app shuts down). Plugins execute in registration order.

> **Short-circuit rule:** A non-`None` return from any plugin callback short-circuits remaining plugins AND the agent's own callbacks for that stage.

```python
class BasePlugin(ABC):
    def __init__(self, name: str): ...

    # --- Runner-level callbacks ---

    async def on_user_message_callback(
        self, *, invocation_context, user_message: types.Content
    ) -> Optional[types.Content]:
        ... # modify or replace user message before invocation starts

    async def before_run_callback(
        self, *, invocation_context
    ) -> Optional[types.Content]:
        ... # return Content to halt the runner immediately

    async def on_event_callback(
        self, *, invocation_context, event: Event
    ) -> Optional[Event]:
        ... # modify or replace an event after it is yielded from the runner

    async def after_run_callback(
        self, *, invocation_context
    ) -> None:
        ... # cleanup, logging after invocation completes

    async def close(self) -> None:
        ... # release resources when the runner is closed

    # --- Agent-level callbacks ---

    async def before_agent_callback(
        self, *, agent, callback_context
    ) -> Optional[types.Content]:
        ... # return Content to short-circuit the agent

    async def after_agent_callback(
        self, *, agent, callback_context
    ) -> Optional[types.Content]:
        ... # return Content to append an extra event

    # --- Model-level callbacks ---

    async def before_model_callback(
        self, *, callback_context, llm_request
    ) -> Optional[LlmResponse]:
        ... # return LlmResponse to skip the actual model call (e.g., caching)

    async def after_model_callback(
        self, *, callback_context, llm_response
    ) -> Optional[LlmResponse]:
        ... # modify or replace the model response

    async def on_model_error_callback(
        self, *, callback_context, llm_request, error
    ) -> Optional[LlmResponse]:
        ... # return LlmResponse to recover from a model error

    # --- Tool-level callbacks ---

    async def before_tool_callback(
        self, *, tool, tool_args, tool_context
    ) -> Optional[dict]:
        ... # return dict to skip tool execution and use as the result

    async def after_tool_callback(
        self, *, tool, tool_args, tool_context, result
    ) -> Optional[dict]:
        ... # return dict to replace the tool result

    async def on_tool_error_callback(
        self, *, tool, tool_args, tool_context, error
    ) -> Optional[dict]:
        ... # return dict to recover from a tool error
```

### Plugin Callback Execution Chain

```
User message arrives
│
▼
on_user_message_callback (Plugin 1 → Plugin 2 → ...)
│
▼
before_run_callback (Plugin 1 → Plugin 2 → ...)
│ (return Content → halt runner)
│
▼
┌─── Agent execution loop ───────────────────────────────────┐
│                                                            │
│  before_agent_callback                                     │
│    Plugin 1 → Plugin 2 → ... → Agent's own callback       │
│    (return Content → short-circuit agent)                  │
│                                                            │
│  ┌─── LLM call ──────────────────────────────────────┐    │
│  │ before_model_callback                              │    │
│  │   Plugin 1 → Plugin 2 → ... → Agent's own callback│    │
│  │   (return LlmResponse → skip model call)           │    │
│  │                                                    │    │
│  │ [Model API call]                                   │    │
│  │                                                    │    │
│  │ after_model_callback                               │    │
│  │   Plugin 1 → Plugin 2 → ... → Agent's own callback│    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  ┌─── Tool calls ────────────────────────────────────┐    │
│  │ before_tool_callback                               │    │
│  │   Plugin 1 → Plugin 2 → ... → Agent's own callback│    │
│  │                                                    │    │
│  │ [Tool execution]                                   │    │
│  │                                                    │    │
│  │ after_tool_callback                                │    │
│  │   Plugin 1 → Plugin 2 → ... → Agent's own callback│    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  after_agent_callback                                      │
│    Plugin 1 → Plugin 2 → ... → Agent's own callback       │
│                                                            │
│  on_event_callback (Plugin 1 → Plugin 2 → ...)            │
│    (for each event yielded)                                │
│                                                            │
└────────────────────────────────────────────────────────────┘
│
▼
after_run_callback (Plugin 1 → Plugin 2 → ...)
```

### EventsCompactionConfig

```python
from google.adk.apps.app import EventsCompactionConfig

EventsCompactionConfig(
    compaction_interval=10, # compact after every 10 new user turns
    overlap_size=2, # keep 2 most recent turns verbatim (for context)
    summarizer=None, # use default LLM-based summarizer
)
```

### ContextCacheConfig

```python
from google.adk.agents.context_cache_config import ContextCacheConfig

ContextCacheConfig(
    cache_intervals=10, # refresh cache every 10 invocations (range: 1–100)
    ttl_seconds=1800, # cache TTL in seconds (default: 30 min)
    min_tokens=0, # minimum token count before caching activates
)
```

Context caching stores `static_instruction` tokens server-side so they don't re-upload on every LLM call — reduces latency and cost for agents with large system prompts. **Requires** `static_instruction` on `LlmAgent` (see [04-agents.md](04-agents.md)); no effect without it.

### ResumabilityConfig

```python
from google.adk.apps.app import ResumabilityConfig

ResumabilityConfig(is_resumable=True)
```

## How It Works

### Plugins — App-Wide Lifecycle Hooks

Plugins fire **before** the agent's own callbacks at each stage (before_agent, before_model, before_tool). If any plugin returns non-`None`, the agent's own callback never runs.

Use cases:
- Logging / tracing every agent call
- Rate limiting
- Global guardrails / safety checks
- Injecting shared context into every agent

### Event Compaction — History Summarization

Compaction summarizes old events into a single compact event, keeping the list bounded.

How compaction works:
1. Runner tracks how many user-initiated invocations have occurred since the last compaction
2. After `compaction_interval` new invocations, Runner triggers compaction
3. The `BaseEventsSummarizer` (default: LLM-based) produces a summary of old events
4. Old events are replaced with a single `EventCompaction` event containing the summary
5. The most recent `overlap_size` invocations are kept verbatim for continuity

```
BEFORE compaction (50 events):
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ e01 │ e02 │ e03 │ ... │ e45 │ e46 │ e47 │ e48 │ e49 │ e50 │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
 ◄──────────── old events ──────────────► ◄── recent ──►

AFTER compaction (overlap_size=2):
┌──────────────────────────────────┬─────┬─────┬─────┬─────┐
│ CompactionEvent                  │ e47 │ e48 │ e49 │ e50 │
│ (LLM summary of e01..e46)       │     │     │     │     │
└──────────────────────────────────┴─────┴─────┴─────┴─────┘
 ◄──── 1 summary event ──────────► ◄── kept verbatim ──►
```

### Resumability — Pause/Resume Long-Running Tools

When an agent calls a `is_long_running=True` tool:
1. The invocation pauses and yields a "paused" event
2. The caller polls for the long-running operation to complete
3. On the next `run_async` call with the same session, the invocation resumes from where it left off

**Requires idempotent tool calls.** Resuming a paused agent re-invokes previous tools; non-idempotent tools may double-execute or corrupt state.

## Examples

### Custom Logging Plugin

```python
class MyLoggingPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="my_logging_plugin")

    async def before_agent_callback(self, *, agent, callback_context):
        print(f'Agent {agent.name} starting...')
        return None # don't short-circuit

app = App(name='my_app', root_agent=agent, plugins=[MyLoggingPlugin()])
```

### App with Compaction

```python
from google.adk.apps.app import EventsCompactionConfig

app = App(
    name='my_app',
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,
        overlap_size=2,
        summarizer=None,
    ),
)
```

### App with Context Cache

```python
from google.adk.agents.context_cache_config import ContextCacheConfig

app = App(
    name='my_app',
    root_agent=agent,
    context_cache_config=ContextCacheConfig(
        cache_intervals=10,
        ttl_seconds=1800,
        min_tokens=0,
    ),
)
```

### App with Resumability

```python
from google.adk.apps.app import ResumabilityConfig

app = App(
    name='my_app',
    root_agent=agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

# Invocation 1: agent calls a long-running tool → pauses
async for event in runner.run_async(user_id='u1', session_id='s1', new_message=msg):
    if event.long_running_tool_ids:
        print(f"Paused — waiting for: {event.long_running_tool_ids}")
        break  # caller polls for completion externally

# Invocation 2: same session → resumes from where it left off
async for event in runner.run_async(user_id='u1', session_id='s1', new_message=resume_msg):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

## Gotchas

### App Name Constraints

Must be a valid Python identifier (not `"user"`). Scopes sessions.

## Related

- [`apps/app.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/app.py) — `App`, `EventsCompactionConfig`, `ResumabilityConfig`
- [`apps/compaction.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/compaction.py) — sliding window compaction logic
- [`apps/base_events_summarizer.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/base_events_summarizer.py) — summarizer interface
- [`plugins/base_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/base_plugin.py) — plugin interface
- [`plugins/plugin_manager.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/plugin_manager.py) — plugin lifecycle management
- [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) — consumes App config
