# 02 — When to Build What in ADK

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [`tools/`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/), [`agents/`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/), [`plugins/`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/), [`flows/`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/) | **Prereqs:** 01

## At a Glance (big-picture diagram first, then one paragraph)

```
What are you trying to do?
│
├─ Add a capability to an agent?
│  ├─ Simple function               ► FunctionTool (auto-wrapped)
│  ├─ Needs lifecycle hooks          ► BaseTool subclass
│  ├─ Dynamic set of tools           ► BaseToolset
│  ├─ External API with auth         ► AuthenticatedFunctionTool
│  └─ Long-running / async           ► LongRunningFunctionTool
│
├─ Compose multiple agents?
│  ├─ LLM picks which agent          ► LlmAgent(sub_agents=[...]) (AutoFlow)
│  ├─ Fixed sequence                 ► SequentialAgent
│  ├─ Run in parallel                ► ParallelAgent
│  ├─ Repeat until done              ► LoopAgent
│  └─ Call a remote agent            ► RemoteA2aAgent (as sub_agent)
│
├─ Add cross-cutting behavior?
│  ├─ Guard all agents               ► BasePlugin (on App)
│  ├─ Guard one agent                ► before/after_agent_callback
│  ├─ Intercept LLM calls            ► before/after_model_callback
│  └─ Intercept tool calls           ► before/after_tool_callback
│
├─ Use a non-Gemini model?
│  ├─ OpenAI, Groq, etc.             ► LiteLlm ("provider/model")
│  ├─ Claude                         ► AnthropicLlm ("claude-*")
│  └─ Custom model                   ► BaseLlm subclass + LLMRegistry
│
├─ Stream to a web UI?
│  └─ RunConfig(streaming_mode=StreamingMode.SSE)
│
└─ Remember past conversations?
   └─ BaseMemoryService + load_memory_tool
```

Decision guide for every ADK extensibility point: **what**, **when**, **when not**, and **how**. This file maps real-world scenarios to the right ADK component and shows how to build each one.

---

## Key API

### [ ] Quick Decision Tree

```
I need to...
│
├─ Do something the LLM can request (call an API, query a DB, run code)
│  ├─ Single function, no setup/teardown          ► Plain function tool
│  ├─ Needs state, complex logic, or is_long_running ► Custom BaseTool subclass
│  └─ Many tools from one source (REST API, MCP)  ► Custom BaseToolset subclass
│
├─ Control HOW a single agent behaves
│  ├─ Before/after the agent runs                 ► before/after_agent_callback
│  ├─ Before/after each LLM call                  ► before/after_model_callback
│  ├─ Before/after each tool call                  ► before/after_tool_callback
│  └─ On LLM or tool errors                       ► on_model/tool_error_callback
│
├─ Control HOW ALL agents behave (app-wide)        ► Plugin
│
├─ Compose multiple agents
│  ├─ Run A, then B, then C in order              ► SequentialAgent
│  ├─ Run A, B, C at the same time                ► ParallelAgent
│  ├─ Repeat until done or N times                ► LoopAgent
│  └─ LLM decides which sub-agent to use          ► LlmAgent with sub_agents
│
├─ Change how an agent THINKS or RESPONDS
│  ├─ Custom reasoning / planning                 ► Custom BasePlanner subclass
│  └─ Run code the LLM generates                  ► BaseCodeExecutor subclass
│
├─ Use a non-Gemini model                          ► LiteLlm adapter or custom BaseLlm
│
├─ Remember past conversations / search knowledge  ► BaseMemoryService + load_memory_tool
│
├─ Stream tokens to a web UI in real-time          ► RunConfig(streaming_mode=SSE) or BIDI
│
├─ Expose / consume agents across services         ► A2A protocol (to_a2a / RemoteA2aAgent)
│
├─ Require user OAuth tokens for a tool            ► AuthenticatedFunctionTool
│
└─ Change where sessions/memory/artifacts are stored ► Custom service backend
```

---

## How It Works (diagram before prose)

### [ ] Real-World Use Cases → What to Build

Common scenarios mapped to ADK components.

#### [ ] Tools

| Real-world scenario | What to build |
|---------------------|---------------|
| Agent needs to call a weather API | Plain function tool |
| Agent needs to query a PostgreSQL database | Plain function tool |
| Agent needs to send a Slack message | Plain function tool |
| Agent needs to read/write files on disk | Plain function tool |
| Agent needs to search Google | Built-in `google_search` tool (no code needed) |
| Agent needs to call any REST API defined by an OpenAPI spec | `OpenAPIToolset` (no code needed) |
| Agent needs to export a report that takes 5 minutes to generate | `LongRunningFunctionTool` (or `BaseTool` subclass with `is_long_running=True`) |
| Agent needs to trigger a Cloud Run job and wait for the result | `LongRunningFunctionTool` (or `BaseTool` subclass with `is_long_running=True`) |
| Human-in-the-loop approval before executing an action | `LongRunningFunctionTool` — same pause mechanism as long-running tools. Invocation pauses, user's next message carries the approval. |
| Agent needs to execute Python code it generates | `BaseCodeExecutor` subclass. Options: `BuiltInCodeExecutor` (model-native), `ContainerCodeExecutor` (Docker), `UnsafeLocalCodeExecutor` (no isolation), `VertexAiCodeExecutor`, `GkeCodeExecutor`, `AgentEngineSandboxCodeExecutor`. |
| Agent should expose all tools from an MCP server | `MCPToolset` (no code needed) |
| Agent should only show certain tools based on user role | `BaseToolset` subclass with `get_tools()` that filters by `ctx.state` |
| Agent connects to a third-party tool platform (LangChain, CrewAI) | `LangchainTool` / `CrewaiTool` wrapper |
| Agent needs to recall past conversations or search knowledge | `BaseMemoryService` + `load_memory_tool`. Three backends: `InMemoryMemoryService` (dev), `VertexAiRagMemoryService` (production vector search), `VertexAiMemoryBankService` (LLM-distilled memory). Wire via `Runner(memory_service=...)`. See [11-memory.md](11-memory.md). |
| Tool needs user OAuth tokens (e.g. Google Drive, GitHub) | `AuthenticatedFunctionTool` wraps any callable with the full OAuth flow. When credentials are missing, the invocation pauses for user authorization. See [13-auth.md](13-auth.md). |
| Multiple independent API calls in one turn | Automatic. When the LLM returns multiple function calls in a single response, ADK runs them concurrently via `asyncio.gather`. No configuration needed. Don't confuse with `ParallelAgent` (concurrent sub-agents across invocations). |

#### [ ] Agent Callbacks (single-agent hooks)

| Real-world scenario | What to build |
|---------------------|---------------|
| Block the agent if the user is not authenticated | `before_agent_callback` → return Content if not authed |
| Cache the agent's full response for repeated identical inputs | `before_agent_callback` (check cache) + `after_agent_callback` (write cache) |
| Always append "Disclaimer: AI-generated" to agent replies | `after_agent_callback` → return extra Content |
| Inject today's date into the system prompt before every LLM call | `before_model_callback` → mutate `llm_request` |
| Return a cached LLM response to avoid redundant API calls | `before_model_callback` → return cached `LlmResponse` |
| Log token usage for every LLM call on a specific agent | `after_model_callback` → read `llm_response.usage_metadata` |
| Sanitize PII from LLM output before it reaches the user | `after_model_callback` → return scrubbed `LlmResponse` |
| Show a friendly message when the LLM quota is exceeded | `on_model_error_callback` → return fallback `LlmResponse` |
| Validate tool arguments (e.g. reject SQL with DROP TABLE) | `before_tool_callback` → return error dict if invalid |
| Rate-limit tool calls per user per minute | `before_tool_callback` → check counter in state, return error if exceeded |
| Normalize/clean a tool's return value before the LLM sees it | `after_tool_callback` → return transformed dict |
| Alert on-call when a tool raises an exception | `on_tool_error_callback` → send alert, return fallback dict |

#### [ ] Plugins (app-wide hooks)

| Real-world scenario | What to build |
|---------------------|---------------|
| Log every LLM call and token count across all agents | `BasePlugin` with `before/after_model_callback` |
| Add OpenTelemetry tracing spans around every agent and tool call | `BasePlugin` with all `before/after` hooks |
| Block all invocations for users on a deny-list, globally | `BasePlugin` with `before_run_callback` |
| Attach a request ID to every event for distributed tracing | `BasePlugin` with `on_event_callback` |
| Enforce a global system prompt added to every LLM call | `BasePlugin` with `before_model_callback` |
| Clean up DB connections when the server shuts down | `BasePlugin.close()` |

#### [ ] Agent Composition

| Real-world scenario | What to build |
|---------------------|---------------|
| Research → Draft → Review pipeline, each step depends on the previous | `SequentialAgent` |
| Summarize 10 documents at once, then merge summaries | `ParallelAgent` → `LlmAgent` synthesizer |
| Run a code-generate → test → fix loop until tests pass | `LoopAgent` with `max_iterations`, sub-agent calls `escalate()` when tests pass |
| Customer support router: billing vs tech vs sales | `LlmAgent` with `sub_agents` (LLM decides routing) |
| Multi-step form wizard (collect name, then address, then payment) | `SequentialAgent` with one `LlmAgent` per step |
| Competitive analysis: run 3 different analyst agents in parallel | `ParallelAgent` with 3 specialized `LlmAgent`s |
| Expose an ADK agent as a remote service for other systems | `to_a2a(agent)` creates a Starlette ASGI app implementing the A2A protocol. |
| Consume a remote agent as a sub-agent | `RemoteA2aAgent(agent_card=...)` as a drop-in `sub_agent`. |

#### [ ] Custom Agents

| Real-world scenario | What to build |
|---------------------|---------------|
| Deterministic FAQ bot with no LLM needed | `BaseAgent` subclass with rule-matching logic |
| Wrap a LangGraph graph as an ADK agent | `BaseAgent` subclass that calls the graph in `_run_async_impl` |
| An agent that calls an external orchestration API and streams its events back | `BaseAgent` subclass |
| Use a non-Gemini model (OpenAI, Anthropic, etc.) | `LiteLlm` adapter supports 100+ providers via `'provider/model-name'` format (e.g., `'openai/gpt-4o'`). For fully custom models, subclass `BaseLlm`, implement `generate_content_async()`, and register via `LLMRegistry.register(MyLlm)`. See [06-models.md](06-models.md). |

#### [ ] Runtime & Configuration

| Real-world scenario | What to build |
|---------------------|---------------|
| Stream tokens to a web frontend in real-time | `RunConfig(streaming_mode=StreamingMode.SSE)`. Partial events (`event.partial=True`) arrive as LLM generates; final aggregated event follows. For bidirectional audio/video, use `runner.run_live()` with `StreamingMode.BIDI`. |

---

## Examples

### [ ] 1. Plain Function Tool

Wrap any Python function. ADK auto-generates the schema from type hints and docstrings.

**When to use:**
- The tool is a simple, stateless function
- No cleanup, no connection pooling, no long-running behavior
- You want zero boilerplate

**When NOT to use:**
- You need custom LLM schema (`_get_declaration`) not derivable from type hints
- The tool is long-running (`is_long_running=True`)
- The tool needs to modify the `LlmRequest` before it reaches the model
- You're grouping many tools together dynamically

**How to build:**

```python
# Sync function — ADK wraps it in FunctionTool automatically
def get_exchange_rate(base: str, target: str) -> dict:
    """Get the current exchange rate between two currencies.

    Args:
        base: The base currency code (e.g. 'USD').
        target: The target currency code (e.g. 'EUR').

    Returns:
        A dict with 'rate' and 'timestamp' fields.
    """
    # real impl: call an exchange API
    return {"rate": 0.92, "timestamp": "2026-03-15T10:00:00Z"}

# Async is also fine
async def fetch_user_profile(user_id: str) -> dict:
    """Fetch the profile for a given user ID."""
    # ...
    return {"name": "Alice", "tier": "premium"}

# Access session state via ToolContext (injected by ADK, never seen by LLM)
from google.adk.tools.tool_context import ToolContext

def remember_preference(preference: str, tool_context: ToolContext) -> str:
    """Save a user preference for this session."""
    tool_context.state["last_preference"] = preference
    return f"Saved: {preference}"

# Attach to agent
from google.adk.agents import LlmAgent
agent = LlmAgent(
    name="finance_agent",
    model="gemini-2.5-flash",
    tools=[get_exchange_rate, fetch_user_profile, remember_preference],
)
```

**Source:** [`tools/function_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/function_tool.py)

---

### [ ] 2. Custom BaseTool Subclass

Full control: custom schema, long-running behavior, or request-level mutation.

**When to use:**
- Need `is_long_running=True` (returns operation ID, finishes asynchronously) — prefer `LongRunningFunctionTool` for simple cases; use `BaseTool` subclass only when you also need a custom schema. The same pause mechanism supports human-in-the-loop approval (invocation pauses, user's next message carries the approval).
- Need a hand-crafted `FunctionDeclaration` (e.g. complex nested schema, optional fields, enums)
- Need to modify the `LlmRequest` before it's sent (e.g. inject a special header or flag into the request)
- Need `custom_metadata` for manifest or tool discovery
- The tool is a built-in model capability (like `google_search`) that doesn't need `run_async`

**When NOT to use:**
- A plain function works — don't subclass just for the sake of it

**How to build:**

```python
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

class ExportReportTool(BaseTool):
    """Starts a long-running report export job."""

    def __init__(self):
        super().__init__(
            name="export_report",
            description="Export a report to PDF. Returns a job ID; the file is ready when the job completes.",
            is_long_running=True, # tells ADK to pause invocation after this call
        )

    def _get_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "report_id": types.Schema(type=types.Type.STRING, description="The ID of the report to export."),
                    "format": types.Schema(type=types.Type.STRING, enum=["pdf", "csv", "xlsx"]),
                },
                required=["report_id"],
            ),
        )

    async def run_async(self, *, args: dict, tool_context: ToolContext):
        report_id = args["report_id"]
        fmt = args.get("format", "pdf")
        # kick off the export job and return operation ID
        job_id = f"job-{report_id}-{fmt}"
        return {"job_id": job_id, "status": "started"}
```

**Source:** [`tools/base_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/base_tool.py)

---

### [ ] 3. Custom BaseToolset Subclass

Dynamic, context-dependent, or externally-sourced tool collections (REST API, MCP server, database schema).

**When to use:**
- Tools are discovered at runtime (OpenAPI spec, database tables, MCP manifest)
- The set of tools changes based on user/session/permissions
- You need a single `close()` for cleanup (HTTP connection pool, subprocess)
- You want a `tool_filter` or `tool_name_prefix` applied across all tools

**When NOT to use:**
- You have a fixed, known list of tools — just pass them as `tools=[...]` on the agent

**How to build:**

```python
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.base_tool import BaseTool
from google.adk.agents.readonly_context import ReadonlyContext

class DatabaseToolset(BaseToolset):
    """Exposes SQL query tools for tables the current user has access to."""

    def __init__(self, db_client):
        super().__init__()
        self._db = db_client

    async def get_tools(self, readonly_context: ReadonlyContext = None) -> list[BaseTool]:
        # Dynamically discover which tables this user can access
        user_id = readonly_context.state.get("user_id") if readonly_context else None
        accessible_tables = await self._db.get_accessible_tables(user_id)

        tools = []
        for table in accessible_tables:
            tools.append(QueryTableTool(table_name=table, db=self._db))
        return tools

    async def close(self):
        await self._db.close() # clean up connection pool

agent = LlmAgent(
    name="data_agent",
    model="gemini-2.5-flash",
    tools=[DatabaseToolset(db_client=my_db)], # toolset, not tool list
)
```

**Source:** [`tools/base_toolset.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/base_toolset.py)

---

### [ ] 4. Agent Callbacks

Per-agent hooks. Defined inline, not reusable across agents.

#### [ ] Callback map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Callback Flow                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  before_agent_callback(callback_context)                           │
│   ► runs before _run_async_impl                                    │
│   ► return Content → skip the agent entirely, use returned content │
│   ► return None → proceed normally                                 │
│                                                                     │
│  after_agent_callback(callback_context)                            │
│   ► runs after _run_async_impl                                     │
│   ► return Content → append an extra event with this content       │
│   ► return None → nothing added                                    │
│                                                                     │
│  before_model_callback(callback_context, llm_request)              │
│   ► runs before each LLM call within this agent                   │
│   ► return LlmResponse → skip LLM call entirely                   │
│   ► mutate llm_request → modify prompt/tools before sending       │
│   ► return None → proceed normally                                 │
│                                                                     │
│  after_model_callback(callback_context, llm_response)              │
│   ► runs after each LLM call                                      │
│   ► return LlmResponse → replace the model's actual response      │
│   ► return None → use the original response                       │
│                                                                     │
│  on_model_error_callback(callback_context, llm_request, error)     │
│   ► runs when the LLM raises an exception                         │
│   ► return LlmResponse → recover gracefully with a fallback       │
│   ► return None → re-raise the error                              │
│                                                                     │
│  before_tool_callback(tool, args, tool_context)                    │
│   ► runs before each tool execution                               │
│   ► return dict → skip tool execution, use returned dict           │
│   ► mutate args → modify tool arguments before the call           │
│   ► return None → proceed normally                                 │
│                                                                     │
│  after_tool_callback(tool, args, tool_context, tool_response)      │
│   ► runs after each tool execution                                │
│   ► return dict → replace the tool's actual result                │
│   ► return None → use the original result                         │
│                                                                     │
│  on_tool_error_callback(tool, args, tool_context, error)           │
│   ► runs when a tool raises an exception                          │
│   ► return dict → recover with a fallback result                  │
│   ► return None → re-raise the error                              │
└─────────────────────────────────────────────────────────────────────┘
```

#### [ ] When to use each

| Callback | Use for |
|----------|---------|
| `before_agent_callback` | Auth checks, feature flags, caching at the agent level |
| `after_agent_callback` | Appending audit trails, post-processing agent output |
| `before_model_callback` | Injecting dynamic context, implementing LLM caching, prompt guards |
| `after_model_callback` | Logging token usage, sanitizing model output, A/B testing |
| `on_model_error_callback` | Fallback responses, retry logic, error reporting |
| `before_tool_callback` | Input validation, rate limiting, tool access control |
| `after_tool_callback` | Result transformation, logging, caching tool results |
| `on_tool_error_callback` | Graceful degradation, fallback data, error alerting |

#### [ ] When NOT to use agent callbacks
- You need the same behavior on **all** agents → use a Plugin instead
- You want to observe events at the Runner level → use a Plugin's `on_event_callback`

#### [ ] How to build

```python
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# --- before_model_callback: inject current time into every prompt ---
async def inject_timestamp(callback_context: CallbackContext, llm_request: LlmRequest):
    import datetime
    timestamp = datetime.datetime.utcnow().isoformat()
    existing = llm_request.config.system_instruction or ""
    llm_request.config.system_instruction = f"{existing}\n\nCurrent UTC time: {timestamp}"
    return None # proceed normally

# --- before_tool_callback: block tool calls during maintenance ---
def block_during_maintenance(tool: BaseTool, args: dict, tool_context: ToolContext):
    if tool_context.state.get("maintenance_mode"):
        return {"error": "Service is under maintenance. Please try again later."}
    return None # allow the tool to run

# --- on_model_error_callback: return a friendly fallback ---
async def model_error_fallback(callback_context: CallbackContext, llm_request: LlmRequest, error: Exception):
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text="I'm having trouble right now. Please try again in a moment.")]
        )
    )

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    before_model_callback=inject_timestamp,
    before_tool_callback=block_during_maintenance,
    on_model_error_callback=model_error_fallback,
)
```

**Source:** [`agents/llm_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/llm_agent.py) · [`agents/base_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/base_agent.py)

---

### [ ] 5. Plugin

Like agent callbacks but **app-wide**: runs for every agent in the tree. Defined once, applied everywhere.

**When to use:**
- Cross-cutting concerns: logging, tracing, rate limiting, safety guardrails
- You want the same `before_model_callback` behavior on every agent without repeating it
- You need Runner-level hooks (`before_run_callback`, `after_run_callback`, `on_event_callback`)

**When NOT to use:**
- Behavior is specific to one agent → use agent callbacks instead (scoped, no coupling)
- Very simple single-agent app → callbacks are simpler

#### [ ] Plugin hooks (superset of agent callbacks)

```python
class BasePlugin(ABC):
    # Runner-level:
    async def before_run_callback(invocation_context) # before runner starts
    async def after_run_callback(invocation_context) # after runner finishes
    async def on_event_callback(invocation_context, event) # every event yielded
    async def on_user_message_callback(invocation_context, user_message)

    # Per-agent (same as agent callbacks, but for ALL agents):
    async def before_agent_callback(agent, callback_context)
    async def after_agent_callback(agent, callback_context)

    # Per-LLM-call:
    async def before_model_callback(callback_context, llm_request)
    async def after_model_callback(callback_context, llm_response)
    async def on_model_error_callback(callback_context, llm_request, error)

    # Per-tool-call:
    async def before_tool_callback(tool, tool_args, tool_context)
    async def after_tool_callback(tool, tool_args, tool_context, result)
    async def on_tool_error_callback(tool, tool_args, tool_context, error)

    async def close() # cleanup when runner shuts down
```

**Execution order:** Plugins run **before** agent callbacks. If a plugin returns a non-`None` value, all subsequent plugins and agent callbacks are skipped.

#### [ ] How to build

```python
import logging
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext
from google.adk.events.event import Event
from google.adk.agents.invocation_context import InvocationContext

logger = logging.getLogger(__name__)

class ObservabilityPlugin(BasePlugin):
    """Logs every LLM call and token usage across all agents."""

    def __init__(self):
        super().__init__(name="observability")
        self._total_tokens = 0

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ):
        logger.info(
            "LLM call | agent=%s | contents=%d",
            callback_context.agent_name,
            len(llm_request.contents),
        )
        return None # don't intercept, just observe

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ):
        if llm_response.usage_metadata:
            tokens = llm_response.usage_metadata.total_token_count or 0
            self._total_tokens += tokens
            logger.info("Tokens used this call: %d | total: %d", tokens, self._total_tokens)
        return None

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ):
        if event.is_final_response():
            logger.info("Final response from agent: %s", event.author)
        return None

    async def close(self):
        logger.info("Session ended. Total tokens consumed: %d", self._total_tokens)

# Attach via App (preferred)
from google.adk.apps.app import App
from google.adk.runners import Runner

app = App(name="my_app", agent=root_agent, plugins=[ObservabilityPlugin()])
runner = Runner(app=app, session_service=session_service)
```

**Source:** [`plugins/base_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/base_plugin.py)

---

### [ ] 6. Custom Agent (BaseAgent Subclass)

Build a fully custom execution loop when none of the built-in agent types fit.

**When to use:**
- You need control flow that `LlmAgent`, `SequentialAgent`, `LoopAgent`, `ParallelAgent` can't express
- You are building a non-LLM agent (rules engine, deterministic pipeline, external orchestrator)
- You want to wrap an external agent framework (LangGraph, CrewAI, etc.) as an ADK agent

**When NOT to use:**
- An `LlmAgent` with the right tools and instruction handles it → don't over-engineer
- You only need composition → use `SequentialAgent` / `LoopAgent` / `ParallelAgent`

**How to build:**

```python
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event, EventActions
from google.genai import types
from typing import AsyncGenerator

class RulesAgent(BaseAgent):
    """A deterministic agent that applies business rules without calling an LLM."""

    routing_table: dict[str, str] # keyword → response (Pydantic field)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            user_text = ctx.user_content.parts[0].text or ""

        # Apply routing rules
        response_text = "I don't understand that request."
        for keyword, response in self.routing_table.items():
            if keyword.lower() in user_text.lower():
                response_text = response
                break

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(
                role="model",
                parts=[types.Part(text=response_text)]
            ),
            actions=EventActions(),
        )

# Usage
rules_agent = RulesAgent(
    name="rules_agent",
    description="Handles FAQs with deterministic rules.",
    routing_table={
        "refund": "To request a refund, email support@example.com.",
        "hours": "We're open Monday–Friday, 9am–5pm PST.",
        "pricing": "See our pricing page at example.com/pricing.",
    }
)
```

**Source:** [`agents/base_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/base_agent.py)

---

### [ ] 7. Composition Agents (SequentialAgent / ParallelAgent / LoopAgent)

These are **not subclassed** — you instantiate them directly with `sub_agents`.

#### [ ] SequentialAgent — run sub-agents one after another

**Use when:** Pipeline stages that must run in order, each passing output to the next via session state.

```
extract ► transform ► load
research ► draft ► review ► publish
```

```python
from google.adk.agents import SequentialAgent, LlmAgent

pipeline = SequentialAgent(
    name="etl_pipeline",
    sub_agents=[
        LlmAgent(name="extractor", instruction="Extract key facts. Save to state['facts'].", output_key="facts"),
        LlmAgent(name="transformer", instruction="Reformat state['facts'] into a report. Save to state['report'].", output_key="report"),
        LlmAgent(name="loader", instruction="Send state['report'] to the API.", tools=[send_to_api]),
    ],
)
```

**Source:** [`agents/sequential_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/sequential_agent.py)

---

#### [ ] ParallelAgent — run sub-agents concurrently

**Use when:** Independent tasks that don't depend on each other's output. Results are merged into the session and a downstream agent synthesizes them.

```
┌─ search_agent ─────┐
├─ calculator_agent ──┤ ► all run at once ► synthesizer_agent
└─ translator_agent ──┘
```

```python
from google.adk.agents import ParallelAgent, SequentialAgent, LlmAgent

research = ParallelAgent(
    name="parallel_research",
    sub_agents=[
        LlmAgent(name="web_researcher", tools=[google_search], output_key="web_results"),
        LlmAgent(name="db_researcher", tools=[query_database], output_key="db_results"),
    ],
)

full_pipeline = SequentialAgent(
    name="research_pipeline",
    sub_agents=[
        research,
        LlmAgent(name="synthesizer", instruction="Combine state['web_results'] and state['db_results'] into a summary."),
    ],
)
```

> **Important:** Each sub-agent in `ParallelAgent` runs in an isolated branch — they cannot see each other's events. Use session state (`output_key`) to share data.

**Source:** [`agents/parallel_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/parallel_agent.py)

---

#### [ ] LoopAgent — repeat until escalate or max_iterations

**Use when:** Iterative refinement, polling, retry loops, or any "keep going until done" pattern.

```
┌─────────────────────────────────────┐
│         refinement_loop             │
│  ┌──────────┐    ┌──────────┐      │
│  │  critic   │ ►  │  refiner  │     │
│  └──────────┘    └──────────┘      │
│       ▲               │            │
│       └───────────────┘            │
│   loops until critic escalates     │
└─────────────────────────────────────┘
```

```python
from google.adk.agents import LoopAgent, LlmAgent

refinement_loop = LoopAgent(
    name="refinement_loop",
    max_iterations=5,
    sub_agents=[
        LlmAgent(
            name="critic",
            instruction="""Review the draft in state['draft'].
            If it's good enough, call escalate(). Otherwise describe what to fix.""",
        ),
        LlmAgent(
            name="refiner",
            instruction="Improve the draft based on the critic's feedback. Save to state['draft'].",
            output_key="draft",
        ),
    ],
)
```

**Stop conditions:** The loop exits when:
- A sub-agent sets `event.actions.escalate = True`
- `max_iterations` is reached

**Source:** [`agents/loop_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/loop_agent.py)

---

### [ ] 8. LLM-controlled Sub-agent Transfer

Give `LlmAgent` a list of `sub_agents`; the LLM decides which to delegate to.

**Use when:** The routing decision is complex, context-dependent, or natural-language-driven.

```python
root = LlmAgent(
    name="router",
    model="gemini-2.5-flash",
    instruction="Route the user to the right specialist agent.",
    sub_agents=[
        LlmAgent(name="billing_agent", description="Handles billing and payment questions."),
        LlmAgent(name="tech_support_agent", description="Handles technical issues and bugs."),
        LlmAgent(name="sales_agent", description="Handles new purchases and upgrades."),
    ],
)
```

The LLM calls the hidden `transfer_to_agent` function. `AutoFlow` intercepts it and routes control. Use `description` on sub-agents — the LLM uses it to decide whom to transfer to.

**Source:** [`flows/llm_flows/auto_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/auto_flow.py)

---

## Gotchas

### [ ] Summary Table

| What to build | When | Key base class / pattern |
|--------------|------|--------------------------|
| Plain function tool | Simple stateless callable | Python `def` / `async def` |
| Custom tool | Long-running, custom schema, request mutation | `BaseTool` |
| Custom toolset | Dynamic tool set, external source, shared cleanup | `BaseToolset` |
| `before_agent_callback` | Pre-check or short-circuit one specific agent | Inline on `LlmAgent` |
| `after_agent_callback` | Post-process or audit one specific agent | Inline on `LlmAgent` |
| `before_model_callback` | Mutate/cache/guard LLM requests for one agent | Inline on `LlmAgent` |
| `after_model_callback` | Log/replace LLM responses for one agent | Inline on `LlmAgent` |
| `on_model_error_callback` | Recover from LLM errors on one agent | Inline on `LlmAgent` |
| `before_tool_callback` | Validate/gate tool calls on one agent | Inline on `LlmAgent` |
| `after_tool_callback` | Transform tool results on one agent | Inline on `LlmAgent` |
| `on_tool_error_callback` | Recover from tool errors on one agent | Inline on `LlmAgent` |
| Plugin | Any of the above but app-wide, or Runner-level hooks | `BasePlugin` |
| Custom agent | Non-LLM logic, external framework adapter, custom loop | `BaseAgent` |
| `SequentialAgent` | Ordered pipeline | Instantiate directly |
| `ParallelAgent` | Concurrent independent tasks | Instantiate directly |
| `LoopAgent` | Repeat until done | Instantiate directly |
| LLM-routed sub-agents | LLM decides delegation | `LlmAgent(sub_agents=[...])` |
| Memory / RAG | Agent needs past conversations or knowledge search | `BaseMemoryService` + `load_memory_tool` |
| Streaming UI | Real-time token streaming to frontend | `RunConfig(streaming_mode=SSE)` or `BIDI` |
| OAuth-gated tools | Tool requires user authorization | `AuthenticatedFunctionTool` |
| A2A protocol | Expose or consume agents as remote services | `to_a2a()` / `RemoteA2aAgent` |
| Custom model | Non-Gemini LLM provider | `LiteLlm` adapter or `BaseLlm` subclass |
| Parallel tool execution | Multiple independent tool calls in one turn | Automatic (`asyncio.gather`) |
| Human-in-the-loop | Pause for user approval | `LongRunningFunctionTool` |

---

## Related

### [ ] Custom Use Cases

#### [ ] Use Case 1 — Parse the User Message, Enrich with API Context, Feed Only Enriched Context to the Responder Agent

**Scenario:**
The user sends a raw message like `"abc media_id:1"`. You want to:
1. Extract the clean query (`"abc"`) and structured IDs (`media_id=1`)
2. Call external APIs to fetch context for those IDs (media record, user profile, etc.)
3. Hand off to a **responder agent** that sees the enriched context — not the raw original message

The raw message is fine sitting in session events for auditing. The key is that the **responder agent's LLM never sees it**. That is controlled by `include_contents="none"` on the responder — not by deleting it from the session.

**What the responder agent's LLM should receive:**
```
User query is: abc

Current media is:
 id: 1
 title: "Summer Reel"
 tags: ["outdoor", "sports"]

Additional context for the user:
 name: Alice
 tier: premium
 watch_history: [...]

Additional context for the media:
 recommendations: [...]
 trending_score: 0.87
```

---

##### How it works: `include_contents="none"` is the key

`LlmAgent` has a field `include_contents: Literal["default", "none"]`.

- `"default"` — the flow includes all session events (filtered by branch) in the LlmRequest. The LLM sees the full conversation history.
- `"none"` — the flow sends **zero** contents to the LLM. The LLM only sees the system prompt (instruction). No history, no raw user message, nothing.

So the pattern is:
1. **Stage 1** (extractor): parse the raw message, call APIs, write results to `session.state`
2. **Stage 2** (responder): `include_contents="none"` + `instruction` with `{variable}` placeholders that resolve from `session.state`

Stage 2 is completely isolated. It reads only what stage 1 wrote to state.

---

##### Three Options for Stage 1 (the extraction step)

The responder agent is always the same. What varies is how you do the extraction.

---

###### Option A — `before_agent_callback` on the pipeline (simplest, no extra LLM call)

Use `before_agent_callback` on the root `SequentialAgent` to parse the message and call APIs **before any agent runs**. Pure Python, no LLM involved in extraction. Results go to session state. Then the responder reads from state.

```
before_agent_callback fires (on SequentialAgent)
 ► read ctx.user_content (the raw "abc media_id:1")
 ► parse IDs with regex
 ► call media API + user API concurrently
 ► write to callback_context.state["clean_query"], ["media_context"], ["user_context"]
 ► return None → pipeline runs normally
 │
 ▼
responder_agent (include_contents="none")
 ► instruction resolves {clean_query}, {media_context}, {user_context} from state
 ► LLM sees only the enriched system prompt, nothing else
```

```python
import re
import asyncio
import json
import httpx
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# --- Parsing helper ---
def parse_user_message(raw: str) -> tuple[str, dict]:
    """'abc media_id:1' → ('abc', {'media_id': '1'})"""
    ids = {}
    clean = raw
    for match in re.finditer(r'(\w+_id):(\w+)', raw):
        ids[match.group(1)] = match.group(2)
        clean = clean.replace(match.group(0), '').strip()
    return clean.strip(), ids

# --- The callback: runs before any agent in the pipeline ---
async def enrich_before_pipeline(callback_context: CallbackContext):
    # Read the raw user message from context
    user_content = callback_context._invocation_context.user_content
    if not user_content or not user_content.parts:
        return None

    raw = user_content.parts[0].text or ""
    clean_query, ids = parse_user_message(raw)

    # Fetch API context concurrently
    async with httpx.AsyncClient() as client:
        tasks = {}
        if "media_id" in ids:
            tasks["media"] = client.get(f"https://api.example.com/media/{ids['media_id']}")
        if "user_id" in ids:
            tasks["user"] = client.get(f"https://api.example.com/users/{ids['user_id']}")

        responses = {k: (await v).json() for k, v in zip(tasks.keys(), await asyncio.gather(*tasks.values()))}

    # Write enriched context to session state
    callback_context.state["clean_query"] = clean_query
    callback_context.state["media_context"] = json.dumps(responses.get("media", {}), indent=2)
    callback_context.state["user_context"] = json.dumps(responses.get("user", {}), indent=2)

    return None # proceed — don't short-circuit the pipeline

# --- Responder: never sees the raw message ---
responder_agent = LlmAgent(
    name="responder",
    model="gemini-2.5-flash",
    include_contents="none", # ← zero session history sent to LLM
    instruction="""
    You are a helpful media assistant.

    User query is: {clean_query}

    Current media:
    {media_context}

    User context:
    {user_context}

    Answer the user's query based only on the context above.
    """,
)

# --- Wire it up ---
pipeline = SequentialAgent(
    name="media_pipeline",
    sub_agents=[responder_agent], # just the responder; extraction is in the callback
    before_agent_callback=enrich_before_pipeline,
)
```

**Tradeoffs:**
- Zero extra LLM calls — extraction is pure Python
- Simplest structure — one agent, one callback
- Parsing logic is hardcoded — no LLM reasoning during extraction
- Complex extraction (ambiguous queries, nested structures) needs more code

---

###### Option B — `SequentialAgent` with extractor `LlmAgent` (LLM does the extraction)

Use a first LlmAgent to parse and enrich using tools. The LLM handles ambiguous or complex extraction. Results are stored in state. The responder reads from state with `include_contents="none"`.

```
SequentialAgent
 │
 ├─ extractor_agent (LlmAgent — sees raw message, calls tools)
 │  ► parse_and_extract("abc media_id:1")
 │  ► state["clean_query"] = "abc"
 │  ► state["media_context"] = "{...}"
 │  ► state["user_context"] = "{...}"
 │
 └─ responder_agent (LlmAgent — include_contents="none")
    ► instruction: "User query is: {clean_query} ..."
    ► LLM sees only the enriched system prompt
```

```python
import re
import json
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext

def parse_and_extract(raw_query: str, tool_context: ToolContext) -> dict:
    """Parse the raw user message. Saves clean_query to state.

    Args:
        raw_query: The original user message, e.g. 'abc media_id:1'.
    """
    ids = {}
    clean = raw_query
    for match in re.finditer(r'(\w+_id):(\w+)', raw_query):
        ids[match.group(1)] = match.group(2)
        clean = clean.replace(match.group(0), '').strip()
    tool_context.state["clean_query"] = clean.strip()
    return {"clean_query": clean.strip(), **ids}

async def fetch_and_store_media(media_id: str, tool_context: ToolContext) -> dict:
    """Fetch media record and save to state['media_context'].

    Args:
        media_id: The media ID extracted from the user's message.
    """
    import httpx
    async with httpx.AsyncClient() as client:
        data = (await client.get(f"https://api.example.com/media/{media_id}")).json()
    tool_context.state["media_context"] = json.dumps(data, indent=2)
    return data

async def fetch_and_store_user(user_id: str, tool_context: ToolContext) -> dict:
    """Fetch user profile and save to state['user_context'].

    Args:
        user_id: The user ID extracted from the user's message.
    """
    import httpx
    async with httpx.AsyncClient() as client:
        data = (await client.get(f"https://api.example.com/users/{user_id}")).json()
    tool_context.state["user_context"] = json.dumps(data, indent=2)
    return data

extractor_agent = LlmAgent(
    name="extractor",
    model="gemini-2.5-flash",
    instruction="""
    You are a message parser. Given the user's raw message:
    1. Call parse_and_extract with the full raw message.
    2. If a media_id was returned, call fetch_and_store_media with it.
    3. If a user_id was returned, call fetch_and_store_user with it.
    Respond with nothing else. Only call the tools.
    """,
    tools=[parse_and_extract, fetch_and_store_media, fetch_and_store_user],
)

responder_agent = LlmAgent(
    name="responder",
    model="gemini-2.5-flash",
    include_contents="none", # ← never sees extractor's conversation or raw message
    instruction="""
    You are a helpful media assistant.

    User query is: {clean_query}

    Current media:
    {media_context}

    User context:
    {user_context}

    Answer the user's query based only on the context above.
    """,
)

pipeline = SequentialAgent(
    name="media_pipeline",
    sub_agents=[extractor_agent, responder_agent],
)
```

**Tradeoffs:**
- LLM handles ambiguous parsing ("find that sports clip from yesterday media_id:5")
- Extractor and responder are independently testable
- Easy to add more extraction tools without changing the responder
- 2 LLM calls per turn (extractor + responder)
- More moving parts

---

###### Option C — `before_model_callback` on the responder (no SequentialAgent needed)

If you don't want a two-agent structure at all, use a single agent with `before_model_callback`. It rewrites `llm_request.contents` just before the LLM call — the LLM receives the enriched version, never the raw string.

```
Single LlmAgent
 ► flow builds LlmRequest with raw "abc media_id:1" in contents
 ► before_model_callback fires
 ► parse + call APIs
 ► replace llm_request.contents[-1] with enriched text
 ► LLM sees enriched message
```

```python
async def enrich_before_model(callback_context: CallbackContext, llm_request: LlmRequest):
    # Find the last plain-text user message in the request
    for i in range(len(llm_request.contents) - 1, -1, -1):
        c = llm_request.contents[i]
        if c.role == "user" and c.parts and c.parts[0].text:
            raw = c.parts[0].text
            clean_query, ids = parse_user_message(raw)
            if not ids:
                return None # nothing to enrich

            async with httpx.AsyncClient() as client:
                media = (await client.get(f"https://api.example.com/media/{ids['media_id']}")).json() if "media_id" in ids else {}
                user = (await client.get(f"https://api.example.com/users/{ids['user_id']}")).json() if "user_id" in ids else {}

            enriched = (
                f"User query is: {clean_query}\n\n"
                + (f"Current media:\n{json.dumps(media, indent=2)}\n\n" if media else "")
                + (f"User context:\n{json.dumps(user, indent=2)}" if user else "")
            )
            llm_request.contents[i] = types.Content(
                role="user", parts=[types.Part(text=enriched.strip())]
            )
            return None # proceed with modified request
    return None

agent = LlmAgent(
    name="media_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful media assistant.",
    before_model_callback=enrich_before_model,
)
```

**Tradeoffs:**
- Simplest possible structure — one agent, one callback, no SequentialAgent
- 1 LLM call per turn
- Enrichment logic is embedded in a callback, harder to test
- Doesn't work if you need an LLM to do the extraction

---

##### Comparison

| | Option A: `before_agent_callback` | Option B: `SequentialAgent` | Option C: `before_model_callback` |
|--|-----------------------------------|------------------------------|------------------------------------|
| Extra LLM calls | 0 | 1 (extractor) | 0 |
| Extraction type | Regex / pure Python | LLM + tools | Regex / pure Python |
| Agent structure | 1 agent + 1 callback | 2 agents | 1 agent + 1 callback |
| Responder isolation | `include_contents="none"` | `include_contents="none"` | Rewrites contents in-place |
| Best when | Fast deterministic parsing | Ambiguous/complex extraction | Same as A, slightly more direct |

**Rule of thumb:**
- Parsing is regex/rules → **Option A** (cleanest) or **Option C**
- Parsing needs LLM reasoning → **Option B**

---

##### Data Flow

```
User sends: "abc media_id:1"
 │
 ▼
Runner stores Event(author="user", content="abc media_id:1") in session
 │                          ← raw message stays here, that's fine
 │
 ├── Option A / B ──────────────────────────────────────────────────────┐
 │                                                                      │
 │  before_agent_callback (A)         extractor_agent (B)              │
 │  parse ► IDs ► API calls           parse ► API tools                │
 │  state["clean_query"] = "abc"      state["clean_query"] = "abc"     │
 │  state["media_context"]= "{...}"   state["media_context"]= "{...}"  │
 │  state["user_context"] = "{...}"   state["user_context"] = "{...}"  │
 │                                                                      │
 │  responder_agent (include_contents="none")                          │
 │  LlmRequest.contents = []         ← empty, no history sent         │
 │  system_instruction resolves {clean_query}, {media_context}, ...    │
 │  LLM sees only the enriched system prompt                           │
 │                                                                      │
 └── Option C ────────────────────────────────────────────────────────┐ │
                                                                      │ │
   before_model_callback                                              │ │
   parse ► API calls                                                  │ │
   rewrite llm_request.contents[-1] ► enriched text                   │ │
   LLM receives enriched message instead of "abc media_id:1"          │ │
                                                                      │ │
 ◄────────────────────────────────────────────────────────────────────┘ │
 ◄──────────────────────────────────────────────────────────────────────┘
 │
 ▼
LLM responds: "What I found about 'abc'..."
```
