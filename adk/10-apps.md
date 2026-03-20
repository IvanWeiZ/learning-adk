# 10 — Apps: Container & Plugins

> **Source:** [`apps/app.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/app.py), [`apps/compaction.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/compaction.py), [`plugins/base_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/base_plugin.py) | **Prereqs:** 03, 04, 09 | **Official docs:** <https://google.github.io/adk-docs/runtime/>

## At a Glance

```
┌─────────────────────────────────────────────────────────┐
│                        App                               │
│  name, root_agent, plugins, configs                     │
│         │                                                │
│         ├── plugins: [BasePlugin, ...]                   │
│         │       │                                        │
│         │       ├── on_user_message_callback()           │
│         │       ├── before_run_callback()                │
│         │       ├── before_agent_callback()              │
│         │       ├── after_agent_callback()               │
│         │       ├── before_model_callback()              │
│         │       ├── after_model_callback()               │
│         │       ├── on_model_error_callback()            │
│         │       ├── before_tool_callback()               │
│         │       ├── after_tool_callback()                │
│         │       ├── on_tool_error_callback()             │
│         │       └── on_event_callback()                  │
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

`App` wraps your root agent with cross-cutting concerns: plugins (lifecycle hooks that apply to every agent in the tree), event compaction (history summarization), context caching, and resumability. Without `App`, you pass `agent=` and `app_name=` to `Runner`. With `App`, you pass `app=` to get all features.

## Class Hierarchy

```
┌──────────────────────────┐
│          App             │  (BaseModel)
├──────────────────────────┤
│ name: str                │
│ root_agent: BaseAgent    │
│ plugins: list[BasePlugin]│
│ events_compaction_config │
│ context_cache_config     │
│ resumability_config      │
└──────────────────────────┘

┌──────────────────────────────────────┐
│            BasePlugin                │  (ABC)
├──────────────────────────────────────┤
│ Runner-level callbacks:              │
│   on_user_message_callback()         │
│   before_run_callback()              │
│   on_event_callback()                │
│   after_run_callback()               │
│   close()                            │
│                                      │
│ Agent-level callbacks:               │
│   before_agent_callback()            │
│   after_agent_callback()             │
│                                      │
│ Model-level callbacks:               │
│   before_model_callback()            │
│   after_model_callback()             │
│   on_model_error_callback()          │
│                                      │
│ Tool-level callbacks:                │
│   before_tool_callback()             │
│   after_tool_callback()              │
│   on_tool_error_callback()           │
└──────────────────────────────────────┘

┌──────────────────────────┐
│ EventsCompactionConfig   │
├──────────────────────────┤
│ compaction_interval: int │
│ overlap_size: int        │
│ summarizer: Optional     │
└──────────────────────────┘

┌──────────────────────────┐
│   ContextCacheConfig     │
├──────────────────────────┤
│ cache_intervals: int     │
│ ttl_seconds: int         │
│ min_tokens: int          │
└──────────────────────────┘

┌──────────────────────────┐
│   ResumabilityConfig     │
├──────────────────────────┤
│ is_resumable: bool       │
└──────────────────────────┘
```

## Key API

### [ ] App Fields

```python
class App(BaseModel):
    name: str # app identifier (valid Python identifier)
    root_agent: BaseAgent # the root agent
    plugins: list[BasePlugin] = [] # app-level hooks
    events_compaction_config: Optional[EventsCompactionConfig] = None
    context_cache_config: Optional[ContextCacheConfig] = None
    resumability_config: Optional[ResumabilityConfig] = None
```

### [ ] BasePlugin Interface

All 11 callbacks. Plugins execute in registration order. A non-`None` return short-circuits remaining plugins and agent callbacks.

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

### [ ] Plugin Callback Execution Chain

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

### [ ] EventsCompactionConfig

```python
from google.adk.apps.app import EventsCompactionConfig

EventsCompactionConfig(
    compaction_interval=10, # compact after every 10 new user turns
    overlap_size=2, # keep 2 most recent turns verbatim (for context)
    summarizer=None, # use default LLM-based summarizer
)
```

### [ ] ContextCacheConfig

```python
from google.adk.agents.context_cache_config import ContextCacheConfig

ContextCacheConfig(
    cache_intervals=10, # refresh cache every 10 invocations (range: 1–100)
    ttl_seconds=1800, # cache TTL in seconds (default: 30 min)
    min_tokens=0, # minimum token count before caching activates
)
```

Requires `static_instruction` on `LlmAgent`. No effect without it.

### [ ] ResumabilityConfig

```python
from google.adk.apps.app import ResumabilityConfig

ResumabilityConfig(is_resumable=True)
```

## How It Works

### [ ] Basic Usage

```python
from google.adk.apps import App
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

agent = LlmAgent(name='my_agent', model='gemini-2.5-flash', instruction='...')

app = App(name='my_app', root_agent=agent)

runner = Runner(app=app, session_service=InMemorySessionService())
```

### [ ] Plugins — App-Wide Lifecycle Hooks

Plugins are app-wide hooks around every agent call.

Use cases:
- Logging / tracing every agent call
- Rate limiting
- Global guardrails / safety checks
- Injecting shared context into every agent

### [ ] Event Compaction — History Summarization

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

### [ ] Resumability — Pause/Resume Long-Running Tools

When an agent calls a `is_long_running=True` tool:
1. The invocation pauses and yields a "paused" event
2. The caller polls for the long-running operation to complete
3. On the next `run_async` call with the same session, the invocation resumes from where it left off

Requires idempotent tool calls.

## Examples

### [ ] Custom Logging Plugin

```python
class MyLoggingPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="my_logging_plugin")

    async def before_agent_callback(self, *, agent, callback_context):
        print(f'Agent {agent.name} starting...')
        return None # don't short-circuit

app = App(name='my_app', root_agent=agent, plugins=[MyLoggingPlugin()])
```

### [ ] App with Compaction

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

### [ ] App with Context Cache

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

### [ ] App with Resumability

```python
from google.adk.apps.app import ResumabilityConfig

app = App(
    name='my_app',
    root_agent=agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
```

## Gotchas

### [ ] App vs. Bare Agent

| Feature | `app=App(...)` | `agent=..., app_name=...` |
|---------|---------------|--------------------------|
| Plugins | Yes | No (use deprecated `plugins=` on Runner) |
| Compaction | Yes | No |
| Context cache | Yes | No |
| Resumability | Yes | No |
| Complexity | Slightly more setup | Simpler |

Use `App` for production. Bare agent is fine for scripts/demos.

**Quick decision:**
```
Do you need plugins, compaction, context caching, or resumability?
 Yes → use App(root_agent=agent, ...)
 No  → use Runner(agent=agent, app_name="my_app", ...)
```

### [ ] App Name Constraints

Must be a valid Python identifier (not `"user"`). Scopes sessions.

## Related

- [`apps/app.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/app.py) — `App`, `EventsCompactionConfig`, `ResumabilityConfig`
- [`apps/compaction.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/compaction.py) — sliding window compaction logic
- [`apps/base_events_summarizer.py`](https://github.com/google/adk-python/blob/main/src/google/adk/apps/base_events_summarizer.py) — summarizer interface
- [`plugins/base_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/base_plugin.py) — plugin interface
- [`plugins/plugin_manager.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/plugin_manager.py) — plugin lifecycle management
- [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) — consumes App config
