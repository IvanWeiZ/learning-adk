# 23b — Advanced Internals: Custom Tools, A2A, Code Executors

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [adk-python](https://github.com/google/adk-python) | **Prereqs:** [23-advanced-internals.md](23-advanced-internals.md)

*This file continues from [23-advanced-internals.md](23-advanced-internals.md), which covers the processor pipeline, reason-act loop, and plugin system.*

---

## 4. Custom Tools — Beyond FunctionTool

**BaseTool subclass (full lifecycle control):**

```python
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import aiohttp

class HttpApiTool(BaseTool):
    """A tool that calls any HTTP API endpoint."""

    def __init__(self, name: str, base_url: str, endpoints: dict):
        super().__init__(
            name=name,
            description=f"Call HTTP APIs at {base_url}",
        )
        self.base_url = base_url
        self.endpoints = endpoints # {"search": {"method": "GET", "path": "/search"}}

    def _get_declaration(self) -> types.FunctionDeclaration:
        """Define what the LLM sees."""
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "endpoint": types.Schema(
                        type="STRING",
                        description=f"API endpoint. Options: {list(self.endpoints.keys())}",
                    ),
                    "params": types.Schema(
                        type="OBJECT",
                        description="Query parameters as key-value pairs",
                    ),
                },
                required=["endpoint"],
            ),
        )

    async def run_async(
        self,
        *,
        args: dict,
        tool_context: ToolContext,
    ) -> dict:
        """Execute the API call."""
        endpoint_name = args.get("endpoint")
        params = args.get("params", {})

        if endpoint_name not in self.endpoints:
            return {"error": f"Unknown endpoint: {endpoint_name}"}

        endpoint = self.endpoints[endpoint_name]
        url = f"{self.base_url}{endpoint['path']}"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=endpoint["method"],
                url=url,
                params=params,
            ) as response:
                data = await response.json()
                return {"status": response.status, "data": data}
```

**LongRunningFunctionTool (async operations)** — for tools that take minutes/hours:

```python
from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.tool_context import ToolContext

def start_deployment(
    service: str,
    version: str,
    tool_context: ToolContext,
) -> dict:
    """Start a deployment pipeline. Returns immediately with a tracking ID."""
    deploy_id = f"deploy-{service}-{version}-{uuid4().hex[:8]}"
    tool_context.state["pending_deploy"] = deploy_id
    return {
        "deploy_id": deploy_id,
        "status": "started",
        "message": f"Deployment {deploy_id} started. It will take ~5 minutes.",
    }

deploy_tool = LongRunningFunctionTool(func=start_deployment)
```

**AgentTool (wrap an agent as a tool):**

```python
from google.adk.tools.agent_tool import AgentTool

research_agent = Agent(
    model="gemini-2.5-pro",
    name="deep_researcher",
    instruction="Do thorough research on the given topic. Return detailed findings.",
    tools=[web_search, read_paper],
)

research_tool = AgentTool(
    agent=research_agent,
    skip_summarization=False,
)

root_agent = Agent(
    name="coordinator",
    instruction="Use the deep_researcher tool for complex questions.",
    tools=[research_tool, simple_search],
)
```

AgentTool vs sub_agents:

```
AgentTool vs sub_agents comparison:
│
├── Transfer control?
│      sub_agents: Yes (LLM decides)
│      AgentTool:  No (tool call)
│
├── Shares session?
│      sub_agents: Yes (same session)
│      AgentTool:  No (new session)
│
├── Shares history?
│      sub_agents: Yes (sees all msgs)
│      AgentTool:  No (isolated)
│
├── Returns to parent?
│      sub_agents: Via transfer back
│      AgentTool:  Automatically
│
└── Use case
       sub_agents: "Route to specialist"
       AgentTool:  "Use as helper"
```

---

## 5. Custom Toolsets — Dynamic Tool Collections

`BaseToolset` provides tools dynamically at runtime, based on context:

```python
from google.adk.tools import BaseToolset, BaseTool, FunctionTool
from google.adk.tools.tool_context import ToolContext

class DatabaseToolset(BaseToolset):
    """Provides query tools based on user's database permissions."""

    def __init__(self, db_connection):
        super().__init__()
        self.db = db_connection

    async def get_tools(self, readonly_context) -> list[BaseTool]:
        """Return tools based on user permissions."""
        user_role = readonly_context.state.get("user:role", "viewer")
        tools = []

        def run_query(sql: str, tool_context: ToolContext) -> str:
            """Run a read-only SQL query against the database."""
            if any(kw in sql.upper() for kw in ["DROP", "DELETE", "UPDATE", "INSERT"]):
                return "Error: Only SELECT queries are allowed."
            results = self.db.execute(sql)
            return str(results[:100])

        tools.append(FunctionTool(func=run_query))

        if user_role == "admin":
            def modify_data(sql: str) -> str:
                """Execute a data modification query (admin only)."""
                self.db.execute(sql)
                return "Query executed successfully."
            tools.append(FunctionTool(func=modify_data))

        return tools

    async def close(self):
        await self.db.close()
```

---

## 6. Authentication Flow — How Tools Get Credentials

```
┌──────────────────────────────────────────────────────────────────────┐
│ Authentication Flow                                                  │
│                                                                      │
│ ① Tool needs credentials                                            │
│ │  tool_context.request_credential(auth_config)                     │
│ │                                                                    │
│ ② CredentialManager checks:                                         │
│ │  1. Load from credential_service → Found? Use it.                │
│ │  2. Load from session state (temp:) → Found? Exchange/refresh.   │
│ │  3. Neither found? → Request from user.                          │
│ │                                                                    │
│ ③ If user auth needed:                                              │
│ │  EventActions.requested_auth_configs = [auth_config]              │
│ │                                                                    │
│ ④ Client shows OAuth dialog / API key prompt                        │
│ │                                                                    │
│ ⑤ Client sends credentials back as function response                │
│ │                                                                    │
│ ⑥ AuthPreprocessor stores credential in session state               │
│ │                                                                    │
│ ⑦ Original tool re-executed with credential available               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Artifacts — File Management Across Sessions

```
┌──────────────────────────────────────────────────────────────────┐
│ Artifact System                                                  │
│                                                                  │
│ save_artifact(filename, part) → version_id                       │
│ load_artifact(filename, version?) → Part                         │
│ list_artifact_keys() → [filenames]                               │
│ delete_artifact(filename)                                        │
│                                                                  │
│ Storage backends:                                                │
│ ├── InMemory        (dev/test)                                   │
│ ├── FileArtifact    (local disk)                                 │
│ └── GcsArtifact     (Google Cloud)                               │
│                                                                  │
│ Versioning:                                                      │
│ save("report.pdf", v1) → version 0                              │
│ save("report.pdf", v2) → version 1                              │
│ load("report.pdf")     → latest (version 1)                     │
│ load("report.pdf", 0)  → version 0 (original)                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Code Executors — Running Code in Agents

```
┌──────────────────────────────────────────────────────────────────┐
│ Code Execution Pipeline                                          │
│                                                                  │
│ LLM generates code block in response                             │
│ │                                                                │
│ ▼                                                                │
│ BaseCodeExecutor.execute_code()                                  │
│ │                                                                │
│ │ Implementations:                                               │
│ │ ├── BuiltInCodeExecutor       ← Jupyter-like, in-process       │
│ │ ├── ContainerCodeExecutor     ← Docker sandbox                 │
│ │ ├── VertexAICodeExecutor      ← Google Cloud                   │
│ │ ├── UnsafeLocalCodeExecutor   ← Direct execution (dev)         │
│ │ └── GKECodeExecutor           ← Kubernetes pods                │
│ │                                                                │
│ ▼                                                                │
│ CodeExecutionResult:                                             │
│ ├── stdout, stderr                                               │
│ └── output_files → saved as artifacts                            │
└──────────────────────────────────────────────────────────────────┘
```

Configuration:

```python
from google.adk.code_executors import BuiltInCodeExecutor

agent = Agent(
    name="data_analyst",
    model="gemini-2.5-pro",
    instruction="You are a data analyst. Write Python code to analyze data.",
    code_executor=BuiltInCodeExecutor(),
)
```

---

## 9. Planners — Structured Reasoning

**BuiltInPlanner (model-native thinking):**

```python
from google.adk.planners import BuiltInPlanner
from google.genai import types

agent = Agent(
    name="thinker",
    model="gemini-2.5-pro",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_budget=2048),
    ),
)
```

---

## 10. A2A (Agent-to-Agent Protocol) — Cross-Service Communication

A2A enables agents running in different services to communicate:

```
┌──────────────────────────────────────────────────────────────────────┐
│ A2A Communication                                                    │
│                                                                      │
│ Service A (your app)            Service B (remote agent)             │
│ ┌──────────────────┐            ┌──────────────────┐                │
│ │ Your Agent       │   A2A      │ Remote Agent     │                │
│ │ "I need weather  │──Protocol──▶│ Weather service  │                │
│ │  data"           │◀────────────│ returns data     │                │
│ └──────────────────┘            └──────────────────┘                │
│                                                                      │
│ Event Conversion:                                                    │
│ ADK Event ──convert──▶ A2A Message ──convert──▶ ADK Event           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 11. Event Compaction — Managing Long Conversations

As conversations grow, the context window fills up. Compaction summarizes old events:

```
Before compaction (20 events, ~8000 tokens):
┌──────────────────────────────────────────┐
│ Event 1: User asks about weather         │
│ ...                                      │
│ Event 20: Agent responds with hotels     │
└──────────────────────────────────────────┘

After compaction (summary + recent events):
┌──────────────────────────────────────────┐
│ [Compaction Summary]:                    │
│ "User asked about weather, restaurants..."│
│                                          │
│ Event 18-20: Recent events kept          │
└──────────────────────────────────────────┘
```

Configuration:

```python
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig

app = App(
    name="my_app",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,
        overlap_size=1,
    ),
)
```

---

## 12. Content Filtering — How Events Become Context

```
┌──────────────────────────────────────────────────────────────────┐
│ Content Filtering Rules                                          │
│                                                                  │
│ For each event:                                                  │
│ ├── Empty content?        → SKIP                                 │
│ ├── Wrong branch?         → SKIP                                 │
│ ├── Framework event?      → SKIP                                 │
│ ├── Thought-only parts?   → SKIP (unless planning)              │
│ ├── Compaction event?     → INCLUDE as summary                   │
│ ├── Rewind event?         → Undo previous events                 │
│ └── Normal content?       → INCLUDE                              │
│                                                                  │
│ Special modes:                                                   │
│ ├── include_contents='default' → full filtered history           │
│ └── include_contents='none'    → current turn only               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 13. Function Call ID Management

ADK tracks function calls with client-side IDs:

```
LLM response: FunctionCall(id="server-123", name="get_weather")
    ▼
ADK wraps: FunctionCall(id="adk-abc123", name="get_weather")
    ▼
Tool executes → FunctionResponse(id="adk-abc123", response={...})
    ▼
Before sending back: FunctionResponse(id="server-123", response={...})
```

---

## 14. Streaming and Live Mode

```
Standard mode:              Live mode:
User ──msg──▶ Agent         User ◀══════▶ Agent
              │                  ║
              ▼                  ║ Bidirectional
         Response                ║ streaming
              │                  ║
              ▼               Audio/Video
             User            in real-time
```

---

## 15. Advanced Agent Patterns

**Pattern: Guardrail Agent**

```python
async def safety_check(callback_context, llm_response):
    """Block unsafe responses before they reach the user."""
    if llm_response and llm_response.content:
        text = str(llm_response.content)
        if contains_pii(text):
            from google.adk.models import LlmResponse
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="I can't share personal information.")],
                ),
            )
    return None

agent = Agent(name="safe_agent", after_model_callback=safety_check)
```

**Pattern: Dynamic Instruction Based on Conversation Phase**

```python
async def phase_aware_instruction(ctx) -> str:
    turn_count = ctx.state.get("temp:turn_count", 0)
    ctx.state["temp:turn_count"] = turn_count + 1

    if turn_count == 0:
        return "You are a sales assistant. Start by greeting the customer."
    elif turn_count < 5:
        return "You are a sales assistant in the discovery phase."
    else:
        return "You are a sales assistant in the closing phase."

agent = Agent(name="adaptive_sales", instruction=phase_aware_instruction)
```

---

## Gotchas

- **`AgentTool` creates isolated sessions** — the child agent gets its own session and conversation history. State changes in the child do not propagate to the parent unless explicitly handled via state deltas.
- **`BaseToolset.get_tools()` is called per-request** — tools are resolved dynamically before each LLM call. If your toolset is expensive to evaluate, cache the results.
- **Auth flow requires resumability** — credential requests pause the agent. Without proper `ResumabilityConfig`, the flow cannot resume after the user provides credentials.
- **Compaction loses detail** — compacted events are replaced by a summary. If downstream logic depends on specific past tool responses, compaction may break it.
- **Content filtering hides events** — events from other branches, framework events, and empty events are silently excluded from LLM context.
- **Function call IDs are rewritten** — ADK wraps server IDs with `adk-` prefixed client IDs during execution, then strips them before sending back.

---

## Related

- [23-advanced-internals.md](23-advanced-internals.md) — Processor pipeline, reason-act loop, plugin system
- [09-tools.md](09-tools.md) — Tool system reference
- [10-apps.md](10-apps.md) — App container and plugins
- [07-events.md](07-events.md) — Event class deep dive
- [05-flows.md](05-flows.md) — Flow architecture
- [13-auth.md](13-auth.md) — OAuth and credential management
