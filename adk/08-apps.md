# Apps — High-Level Application Container

**Source:** [`apps/app.py`](../adk-python/src/google/adk/apps/app.py) · [`apps/compaction.py`](../adk-python/src/google/adk/apps/compaction.py)

---

## What It Is

`App` is an optional but recommended wrapper around your root agent. It bundles together:
- The root agent
- Plugins (lifecycle hooks that apply to every agent in the tree)
- Event compaction configuration (history summarization)
- Context cache configuration
- Resumability configuration (pause/resume long-running invocations)

Without `App`, you can pass `agent=` and `app_name=` directly to `Runner`. With `App`, you pass `app=` to `Runner` and get all the above for free. The root agent is set via the `root_agent` field.

---

## App Fields

```python
class App(BaseModel):
    name: str                                    # app identifier (valid Python identifier)
    root_agent: BaseAgent                        # the root agent
    plugins: list[BasePlugin] = []               # app-level hooks
    events_compaction_config: Optional[EventsCompactionConfig] = None
    context_cache_config: Optional[ContextCacheConfig] = None
    resumability_config: Optional[ResumabilityConfig] = None
```

---

## Basic Usage

```python
from google.adk.apps import App
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

agent = LlmAgent(name='my_agent', model='gemini-2.5-flash', instruction='...')

app = App(name='my_app', root_agent=agent)

runner = Runner(app=app, session_service=InMemorySessionService())
```

---

## Plugins

Plugins are app-wide hooks that run around every agent call, without modifying the agent itself. They implement `BasePlugin`:

```python
class BasePlugin:
    async def before_agent_callback(self, agent, callback_context) -> Optional[Content]:
        ...  # return Content to short-circuit the agent

    async def after_agent_callback(self, agent, callback_context) -> Optional[Content]:
        ...  # return Content to append an extra event
```

Use cases:
- Logging / tracing every agent call
- Rate limiting
- Global guardrails / safety checks
- Injecting shared context into every agent

```python
class MyLoggingPlugin(BasePlugin):
    async def before_agent_callback(self, agent, ctx):
        print(f'Agent {agent.name} starting...')
        return None  # don't short-circuit

app = App(name='my_app', root_agent=agent, plugins=[MyLoggingPlugin()])
```

---

## Event Compaction

For long-running conversations, `Session.events` can grow to thousands of entries. Compaction summarizes old events into a single compact event, keeping the list manageable while preserving context.

```python
from google.adk.apps.app import EventsCompactionConfig

app = App(
    name='my_app',
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,   # compact after every 10 new user turns
        overlap_size=2,           # keep 2 most recent turns verbatim (for context)
        summarizer=None,          # use default LLM-based summarizer
    ),
)
```

How compaction works:
1. Runner tracks how many user-initiated invocations have occurred since the last compaction
2. After `compaction_interval` new invocations, Runner triggers compaction
3. The `BaseEventsSummarizer` (default: LLM-based) produces a summary of old events
4. Old events are replaced with a single `EventCompaction` event containing the summary
5. The most recent `overlap_size` invocations are kept verbatim for continuity

---

## Context Cache Config

For agents with long static instructions (e.g., large documents in `static_instruction`), context caching can dramatically reduce latency and cost:

```python
from google.adk.agents.context_cache_config import ContextCacheConfig

app = App(
    name='my_app',
    root_agent=agent,
    context_cache_config=ContextCacheConfig(
        cache_intervals=10,    # refresh cache every 10 invocations (range: 1–100)
        ttl_seconds=1800,      # cache TTL in seconds (default: 30 min)
        min_tokens=0,          # minimum token count before caching activates
    ),
)
```

Without `static_instruction`, caching has no effect (nothing is cacheable). The `static_instruction` field on `LlmAgent` is the content that gets cached.

---

## Resumability Config (Experimental)

Allows invocations to pause on long-running tool calls and resume later:

```python
from google.adk.apps.app import ResumabilityConfig

app = App(
    name='my_app',
    root_agent=agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
```

When an agent calls a `is_long_running=True` tool:
1. The invocation pauses and yields a "paused" event
2. The caller polls for the long-running operation to complete
3. On the next `run_async` call with the same session, the invocation resumes from where it left off

Resumability requires that tool calls be **idempotent** (at-least-once execution guarantee).

---

## App vs. Bare Agent

| Feature | `app=App(...)` | `agent=..., app_name=...` |
|---------|---------------|--------------------------|
| Plugins | Yes | No (use deprecated `plugins=` on Runner) |
| Compaction | Yes | No |
| Context cache | Yes | No |
| Resumability | Yes | No |
| Complexity | Slightly more setup | Simpler |

For production use, always use `App`. For quick scripts and demos, bare agent is fine.

---

## App Name Constraints

App names must be valid Python identifiers (letters, digits, underscores). Cannot be `"user"` (reserved). The name is used to scope sessions — all sessions with `app_name='my_app'` are grouped together.

---

## Related Files

- [`apps/app.py`](../adk-python/src/google/adk/apps/app.py) — `App`, `EventsCompactionConfig`, `ResumabilityConfig`
- [`apps/compaction.py`](../adk-python/src/google/adk/apps/compaction.py) — sliding window compaction logic
- [`apps/base_events_summarizer.py`](../adk-python/src/google/adk/apps/base_events_summarizer.py) — summarizer interface
- [`plugins/base_plugin.py`](../adk-python/src/google/adk/plugins/base_plugin.py) — plugin interface
- [`plugins/plugin_manager.py`](../adk-python/src/google/adk/plugins/plugin_manager.py) — plugin lifecycle management
- [`runners.py`](../adk-python/src/google/adk/runners.py) — consumes App config
