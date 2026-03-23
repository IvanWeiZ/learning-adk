# 23 — Advanced Internals: Processor Pipeline & Reason-Act Loop

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [adk-python](https://github.com/google/adk-python) | **Prereqs:** [00-onboarding-guide.md](00-onboarding-guide.md), [20-best-practices.md](20-best-practices.md), [05-flows.md](05-flows.md)

## At a Glance

```
ADK Internals — Three Pillars:
│
├── Processor Pipeline
│      12 request procs → LLM call → 2 response procs
│
├── Plugin System
│      Wraps agent lifecycle with before/after hooks on every layer
│
├── A2A Protocol
│      Cross-service agent communication (ADK Event ↔ A2A Message)
│
└── + Custom Tools, Toolsets, Auth, Artifacts, Code Executors,
      Planners, Streaming, Event Compaction, Content Filtering
```

This file covers the processor pipeline that builds prompts and handles responses, the reason-act loop, and the plugin system. For custom tools, A2A protocol, code executors, and advanced agent patterns, see [23b-plugins-and-a2a.md](23b-plugins-and-a2a.md).

## How It Works

### 1. The Processor Pipeline

`BaseLlmFlow` runs **request processors** (build prompt) then **response processors** (handle output) in order for every LLM call.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Request Processors (executed in order)                                │
│                                                                      │
│ ① basic               Set model, config, output_schema               │
│ │                                                                    │
│ ② auth_preprocessor    Resume tool calls after auth completed        │
│ │                                                                    │
│ ③ request_confirmation Set up tool confirmation prompts              │
│ │                                                                    │
│ ④ instructions         Inject system prompt + state placeholders     │
│ │                                                                    │
│ ⑤ identity             Add identity context (user info)              │
│ │                                                                    │
│ ⑥ compaction           Compact long conversation history             │
│ │                                                                    │
│ ⑦ contents             Build conversation messages array             │
│ │                       Filters events by branch + content rules:    │
│ │                       Empty content? → SKIP                        │
│ │                       Wrong branch? → SKIP                         │
│ │                       Framework event? → SKIP                      │
│ │                       Thought-only? → SKIP (unless planning)       │
│ │                       Compaction event? → INCLUDE as summary        │
│ │                       Rewind event? → Undo previous events          │
│ │                       Normal content? → INCLUDE                     │
│ │                       Modes: 'default' = full history              │
│ │                              'none' = current turn only            │
│ │                                                                    │
│ ⑧ context_cache        Set up context caching for long prompts       │
│ │                                                                    │
│ ⑨ interactions          Stateful conversation API setup              │
│ │                                                                    │
│ ⑩ nl_planning          Mark thought/reasoning parts                  │
│ │                                                                    │
│ ⑪ code_execution       Preprocess code blocks + data files           │
│ │                                                                    │
│ ⑫ output_schema_processor Handle output_schema + tools workaround   │
│ │                                                                    │
│ ▼                                                                    │
│ LlmRequest ready → sent to model                                    │
└──────────────────────────────────────────────────────────────────────┘
 │
 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Response Processors (executed in order)                               │
│                                                                      │
│ ① nl_planning          Extract planning tags from response           │
│ │                                                                    │
│ ② code_execution       Execute code blocks, capture output           │
│ │                                                                    │
│ ▼                                                                    │
│ LlmResponse processed → function calls extracted → tools run        │
└──────────────────────────────────────────────────────────────────────┘
```

AutoFlow adds agent transfer — `AutoFlow` extends `SingleFlow` by injecting one extra request processor:

```
SingleFlow processors:
 [basic, auth, confirmation, instructions, identity, compaction,
 contents, cache, interactions, planning, code_exec, output_schema]

AutoFlow processors:
 [basic, auth, confirmation, instructions, identity, compaction,
 contents, cache, interactions, planning, code_exec, output_schema,
 agent_transfer] ← adds transfer_to_agent tool declaration
```

```python
# Conceptual illustration — AutoFlow injects transfer_to_agent as a tool when sub_agents exist.
# The LLM sees a function declaration equivalent to:
{
    "name": "transfer_to_agent",
    "description": "Transfer to another agent for specialized handling",
    "parameters": {
        "agent_name": {
            "type": "string",
            "description": "Name of the agent to transfer to"
        }
    }
}
```

---

### 2. The Reason-Act Loop — Step by Step

The core loop in `BaseLlmFlow.run_async()`:

```
┌──────────────────────────────────────────────────────────────────┐
│ BaseLlmFlow.run_async() Loop                                     │
│                                                                  │
│ while True:                                                      │
│ │                                                                │
│ │ ┌─────────────────────────────────────┐                        │
│ │ │ 1. Run all request processors      │                        │
│ │ │    → builds LlmRequest             │                        │
│ │ └─────────────────┬───────────────────┘                        │
│ │                   │                                            │
│ │ ┌─────────────────▼───────────────────┐                        │
│ │ │ 2. Call model.generate_content()    │                        │
│ │ │    or model.connect() for live      │                        │
│ │ │    → yields LlmResponse            │                        │
│ │ └─────────────────┬───────────────────┘                        │
│ │                   │                                            │
│ │ ┌─────────────────▼───────────────────┐                        │
│ │ │ 3. Run all response processors     │                        │
│ │ │    → may modify response           │                        │
│ │ └─────────────────┬───────────────────┘                        │
│ │                   │                                            │
│ │         ┌─────────▼─────────┐                                  │
│ │         │  Function calls?  │                                  │
│ │         └────┬─────────┬────┘                                  │
│ │          Yes │         │ No                                    │
│ │              │         │                                        │
│ │   ┌────────────▼──┐    │                                       │
│ │   │ 4. Execute    │    │                                       │
│ │   │    tools in   │    │                                       │
│ │   │    parallel   │    │                                       │
│ │   └────────┬──────┘    │                                       │
│ │            │           │                                       │
│ │   ┌────────▼──────┐    │                                       │
│ │   │ 5. Yield tool │    │                                       │
│ │   │    events     │    │                                       │
│ │   └────────┬──────┘    │                                       │
│ │            │           │                                       │
│ │      continue loop     │                                       │
│ │                        │                                       │
│ │     ┌──────────────────────▼──────┐                            │
│ │     │ 6. Yield final text event   │                            │
│ │     │    → break loop             │                            │
│ │     └─────────────────────────────┘                            │
│ │                                                                │
│ end while                                                        │
└──────────────────────────────────────────────────────────────────┘
```

Parallel tool execution — when the LLM returns multiple function calls, ADK runs them concurrently:

```python
# Pseudocode — simplified from handle_function_calls_async()
async def _execute_tools_parallel(function_calls, tool_context):
    tasks = []
    for fc in function_calls:
        tool = find_tool(fc.name)
        task = asyncio.create_task(
            _execute_single_tool(tool, fc.args, tool_context)
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results
```

```
LLM returns: [get_weather("Tokyo"), get_weather("London"), get_weather("NYC")]
│
├── Task 1: get_weather("Tokyo")
│      runs concurrently
│
├── Task 2: get_weather("London")
│      runs concurrently
│
├── Task 3: get_weather("NYC")
│      runs concurrently
│
└── asyncio.gather() collects all results
       → merged into single event
       → fed back to LLM in next iteration
```

---

### 3. The Plugin System — Cross-Cutting Concerns

Plugins wrap the entire agent lifecycle. They execute **before** agent-level callbacks.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Full Callback Execution Order                                        │
│                                                                      │
│ User message arrives                                                 │
│ │                                                                    │
│ ├── Plugin.on_user_message_callback()  ← all plugins, in order      │
│ │                                                                    │
│ ├── Plugin.before_run_callback()       ← before runner starts       │
│ │                                                                    │
│ │   ┌── Plugin.before_agent_callback() ← plugins FIRST for before_* │
│ │   ├── Agent.before_agent_callback()  ← then agent callback        │
│ │   │                                                                │
│ │   │   ┌── Plugin.before_model_callback()  ← plugins FIRST         │
│ │   │   ├── Agent.before_model_callback()                           │
│ │   │   │                                                            │
│ │   │   │   ══════ LLM CALL ══════                                  │
│ │   │   │                                                            │
│ │   │   ├── Agent.after_model_callback()  ← agent FIRST for after_* │
│ │   │   └── Plugin.after_model_callback() ← plugins LAST            │
│ │   │                                                                │
│ │   │   ┌── Plugin.before_tool_callback()  ← plugins FIRST          │
│ │   │   ├── Agent.before_tool_callback()                            │
│ │   │   │                                                            │
│ │   │   │   ══════ TOOL CALL ══════                                 │
│ │   │   │                                                            │
│ │   │   ├── Agent.after_tool_callback()  ← agent FIRST for after_*  │
│ │   │   └── Plugin.after_tool_callback() ← plugins LAST             │
│ │   │                                                                │
│ │   ├── Agent.after_agent_callback()  ← agent FIRST for after_*     │
│ │   └── Plugin.after_agent_callback() ← plugins LAST                │
│ │                                                                    │
│ ├── Plugin.on_event_callback()         ← after each event yielded   │
│ │                                                                    │
│ └── Plugin.after_run_callback()        ← after runner completes     │
│                                                                      │
│ Error paths:                                                         │
│ ├── Plugin.on_model_error_callback()   ← LLM errors                │
│ └── Plugin.on_tool_error_callback()    ← Tool errors                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Examples

### Building a custom plugin

Plugin callbacks receive `callback_context` (a `CallbackContext` — same type as in `before_agent_callback` on `LlmAgent`). Plugin callbacks do **not** receive `tool_context` (`ToolContext`). Use `callback_context.state` to read and write session state.

For plugin API basics — available hooks, return types, and registration — see [10-apps.md](10-apps.md).

```python
from google.adk.plugins import BasePlugin
import time
import logging

logger = logging.getLogger(__name__)

class MetricsPlugin(BasePlugin):
    """Tracks latency and token usage across all agents."""

    name = "metrics_plugin"

    async def before_run_callback(self, callback_context, **kwargs):
        # callback_context is CallbackContext — same as agent callbacks
        callback_context.state["temp:run_start"] = time.time()
        return None # Continue normally

    async def before_model_callback(self, callback_context, llm_request, **kwargs):
        callback_context.state["temp:model_start"] = time.time()
        msg_count = len(llm_request.contents) if llm_request.contents else 0
        logger.info(f"LLM call with {msg_count} messages")
        return None

    async def after_model_callback(self, callback_context, llm_response, **kwargs):
        start = callback_context.state.get("temp:model_start", 0)
        latency = time.time() - start
        logger.info(f"LLM responded in {latency:.2f}s")

        # Track cumulative token usage in user-scoped state
        if llm_response and llm_response.usage_metadata:
            total = callback_context.state.get("user:total_tokens", 0)
            total += llm_response.usage_metadata.total_token_count or 0
            callback_context.state["user:total_tokens"] = total
        return None

    async def on_event_callback(self, callback_context, event, **kwargs):
        # Log every event for observability
        logger.debug(f"Event from {event.author}: {event.id}")
        return None

    async def after_run_callback(self, callback_context, **kwargs):
        start = callback_context.state.get("temp:run_start", 0)
        total = time.time() - start
        logger.info(f"Total run time: {total:.2f}s")
        return None
```

Registering plugins:

```python
from google.adk.apps import App

app = App(
    name="my_app",
    root_agent=root_agent,
    plugins=[
        MetricsPlugin(),
        DebugLoggingPlugin(), # Built-in
    ],
)
```

---

## Gotchas

- **Processor order matters** — request processors run in a fixed sequence. If you override or extend a flow, inserting a processor in the wrong position can break downstream processors.
- **Plugin callbacks run before agent callbacks** — for `before_*` hooks, plugins execute first. For `after_*` hooks, agent callbacks run first, then plugins. This asymmetry is intentional but easy to forget.
- **`AutoFlow` silently adds `transfer_to_agent`** — if your agent has `sub_agents`, `AutoFlow` injects a transfer tool. This can conflict if you define your own tool with a similar name.

*Continued in [23b-plugins-and-a2a.md](23b-plugins-and-a2a.md) — custom tools, toolsets, authentication, artifacts, code executors, A2A protocol, streaming, event compaction, content filtering, and advanced agent patterns.*

---

## Related

- [23b-plugins-and-a2a.md](23b-plugins-and-a2a.md) — Custom tools, A2A, code executors, advanced patterns
- [00-onboarding-guide.md](00-onboarding-guide.md) — Start here if you are new
- [20-best-practices.md](20-best-practices.md) — Common mistakes to avoid
- [07-events.md](07-events.md) — Event class deep dive
- [05-flows.md](05-flows.md) — Flow architecture
- [09-tools.md](09-tools.md) — Tool system reference
- [10-apps.md](10-apps.md) — App container and plugins
- [11-memory.md](11-memory.md) — Memory and long-term recall
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request
