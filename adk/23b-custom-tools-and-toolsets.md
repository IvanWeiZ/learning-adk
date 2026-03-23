# 23b — Advanced Internals: Custom Tools, A2A, Code Executors

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [adk-python](https://github.com/google/adk-python) | **Prereqs:** [23-advanced-internals.md](23-advanced-internals.md)

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

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
        # types.Schema accepts string type values ("OBJECT", "STRING") or enum values
        # (types.Type.OBJECT, types.Type.STRING). If the string form raises an error,
        # use the enum: types.Schema(type=types.Type.OBJECT, ...).
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

deploy_tool = LongRunningFunctionTool(start_deployment)  # func is positional, not keyword
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
    # include_plugins=True (default) — propagates parent plugins to the agent's runner.
    # Set to False for isolated plugin environment.
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

`BaseToolset` provides tools dynamically at runtime, based on context.

> **Import note:** `BaseToolset` is **not** exported from `google.adk.tools` (it is not in `__all__`). Import it directly: `from google.adk.tools.base_toolset import BaseToolset`.

```python
from google.adk.tools.base_toolset import BaseToolset  # not in google.adk.tools.__all__
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.readonly_context import ReadonlyContext
from typing import Optional

class DatabaseToolset(BaseToolset):
    """Provides query tools based on user's database permissions."""

    def __init__(self, db_connection):
        # BaseToolset.__init__ accepts optional tool_filter and tool_name_prefix:
        #   tool_filter: Optional[Union[ToolPredicate, list[str]]] — filter tools by predicate or name list
        #   tool_name_prefix: Optional[str] — prefix prepended to all tool names
        super().__init__()
        self.db = db_connection

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> list[BaseTool]:
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


---

## Topics Covered in Dedicated Files

The following topics are covered in depth in their own files. Brief summaries and links:

- **Authentication** (credential management, OAuth, `request_credential`) → [13-auth.md](13-auth.md)
- **Artifacts** (binary file storage, versioning, `save_artifact`/`load_artifact`) → [12-artifacts.md](12-artifacts.md)
- **Planners** (`BuiltInPlanner`, thinking mode, plan-then-act) → [14-planners.md](14-planners.md)
- **Event Compaction** (`EventsCompactionConfig`, summarizing long conversations) → [10-apps.md](10-apps.md)
- **Content Filtering** (branch isolation, `include_contents`, filtering rules) → [05-flows.md](05-flows.md)
- **Function Call ID Management** (ADK wraps server IDs with `adk-` prefix) → [07-events.md](07-events.md)
- **Streaming and Live Mode** (bidirectional audio/video via `model.connect()`) → [06-models.md](06-models.md)
- **Advanced Agent Patterns** (guardrails, dynamic instructions, phase-aware agents) → [21-advanced-patterns.md](21-advanced-patterns.md)


---

## Gotchas

- **`ToolContext` is an alias for `Context`** — `tool_context.py` defines `ToolContext = Context`. They are the same class, not a subclass relationship. Import either from `google.adk.tools.tool_context` or `google.adk.agents.context`.
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
