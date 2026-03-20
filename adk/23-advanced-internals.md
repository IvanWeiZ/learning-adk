# 23 — Advanced Internals: Processors, Plugins, A2A

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

This file covers the internal machinery of ADK: the processor pipeline that builds prompts and handles responses, the plugin system for cross-cutting concerns, custom tool patterns beyond `FunctionTool`, the authentication flow, artifact management, code execution, planners, A2A protocol, event compaction, content filtering, and streaming modes.

## How It Works

### [ ] 1. The Processor Pipeline

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
│ │                       Filter events, handle branches               │
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
# AutoFlow injects transfer_to_agent as a tool when sub_agents exist
# The LLM sees this in its function declarations:
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

### [ ] 2. The Reason-Act Loop — Step by Step

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
# Inside handle_function_calls_async():
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

### [ ] 3. The Plugin System — Cross-Cutting Concerns

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
│ │   ┌── Plugin.before_agent_callback() ← plugins first              │
│ │   ├── Agent.before_agent_callback()  ← then agent callback        │
│ │   │                                                                │
│ │   │   ┌── Plugin.before_model_callback()                          │
│ │   │   ├── Agent.before_model_callback()                           │
│ │   │   │                                                            │
│ │   │   │   ══════ LLM CALL ══════                                  │
│ │   │   │                                                            │
│ │   │   ├── Agent.after_model_callback()                            │
│ │   │   └── Plugin.after_model_callback()                           │
│ │   │                                                                │
│ │   │   ┌── Plugin.before_tool_callback()                           │
│ │   │   ├── Agent.before_tool_callback()                            │
│ │   │   │                                                            │
│ │   │   │   ══════ TOOL CALL ══════                                 │
│ │   │   │                                                            │
│ │   │   ├── Agent.after_tool_callback()                             │
│ │   │   └── Plugin.after_tool_callback()                            │
│ │   │                                                                │
│ │   ├── Agent.after_agent_callback()                                │
│ │   └── Plugin.after_agent_callback()                               │
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

Building a custom plugin:

```python
from google.adk.plugins import BasePlugin
import time
import logging

logger = logging.getLogger(__name__)

class MetricsPlugin(BasePlugin):
    """Tracks latency and token usage across all agents."""

    name = "metrics_plugin"

    async def before_run_callback(self, callback_context, **kwargs):
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

### [ ] 4. Custom Tools — Beyond FunctionTool

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

**LongRunningFunctionTool (async operations)** — for tools that take minutes/hours (file processing, CI/CD triggers, approval workflows):

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

    # Save tracking ID to state for later polling
    tool_context.state["pending_deploy"] = deploy_id

    # Return immediately — the LLM won't retry
    return {
        "deploy_id": deploy_id,
        "status": "started",
        "message": f"Deployment {deploy_id} started. It will take ~5 minutes.",
    }

# Wrap with LongRunningFunctionTool
deploy_tool = LongRunningFunctionTool(func=start_deployment)
```

```
Normal tool:                LongRunningFunctionTool:
Normal tool:
│
├── LLM calls tool
├── Tool runs (blocks for 5 minutes)
└── Result sent to LLM

LongRunningFunctionTool:
│
├── LLM calls tool
├── Tool starts async work, returns tracking ID (immediate)
└── LLM gets tracking ID, tells user to wait
```

**AgentTool (wrap an agent as a tool):**

```python
from google.adk.tools.agent_tool import AgentTool

# Define a specialist agent
research_agent = Agent(
    model="gemini-2.5-pro",
    name="deep_researcher",
    instruction="Do thorough research on the given topic. Return detailed findings.",
    tools=[web_search, read_paper],
)

# Wrap it as a tool — the parent agent can call it like any other tool
research_tool = AgentTool(
    agent=research_agent,
    skip_summarization=False, # LLM summarizes research output
)

# Parent uses it as a regular tool
root_agent = Agent(
    name="coordinator",
    instruction="Use the deep_researcher tool for complex questions.",
    tools=[research_tool, simple_search], # Mix of tool types
)
```

```
AgentTool execution flow:
┌─────────────────────────────────────────────────────┐
│ Parent Agent calls research_tool(topic="quantum")   │
│ │                                                   │
│ ▼                                                   │
│ AgentTool.run_async():                              │
│ │                                                   │
│ │ 1. Create child Runner                            │
│ │ 2. Create new session for child                   │
│ │ 3. Run research_agent with input                  │
│ │ 4. Collect all events from child                  │
│ │ 5. Extract last content + state deltas            │
│ │ 6. Return result to parent                        │
│ │                                                   │
│ │ ┌──────────────────────────────┐                  │
│ │ │ Child Agent (isolated)       │                  │
│ │ │ - Own session                │                  │
│ │ │ - Own conversation history   │                  │
│ │ │ - Can use its own tools      │                  │
│ │ └──────────────────────────────┘                  │
│ │                                                   │
│ ▼                                                   │
│ Parent receives result as tool output               │
└─────────────────────────────────────────────────────┘
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
├── LLM picks when?
│      sub_agents: Based on description
│      AgentTool:  Based on tool schema
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

### [ ] 5. Custom Toolsets — Dynamic Tool Collections

`BaseToolset` provides tools dynamically at runtime, based on context:

```python
from google.adk.tools import BaseToolset, BaseTool, FunctionTool
from google.adk.tools.tool_context import ToolContext

class DatabaseToolset(BaseToolset):
    """Provides query tools based on user's database permissions."""

    def __init__(self, db_connection):
        super().__init__()
        self.db = db_connection

    async def get_tools(
        self,
        readonly_context,
    ) -> list[BaseTool]:
        """Return tools based on user permissions."""
        user_role = readonly_context.state.get("user:role", "viewer")
        tools = []

        # Everyone can query
        def run_query(sql: str, tool_context: ToolContext) -> str:
            """Run a read-only SQL query against the database."""
            if any(kw in sql.upper() for kw in ["DROP", "DELETE", "UPDATE", "INSERT"]):
                return "Error: Only SELECT queries are allowed."
            results = self.db.execute(sql)
            return str(results[:100]) # Limit results

        tools.append(FunctionTool(func=run_query))

        # Only admins can modify
        if user_role == "admin":
            def modify_data(sql: str) -> str:
                """Execute a data modification query (admin only)."""
                self.db.execute(sql)
                return "Query executed successfully."

            tools.append(FunctionTool(func=modify_data))

        return tools

    async def close(self):
        """Clean up database connection."""
        await self.db.close()
```

```
Toolset resolution at runtime:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ Agent starts running                                     │
│ │                                                        │
│ ▼                                                        │
│ For each toolset in agent.tools:                         │
│ │                                                        │
│ ├── Is it a BaseToolset?                                 │
│ │   Yes → call toolset.get_tools(readonly_context)       │
│ │         │                                              │
│ │         ▼                                              │
│ │   ┌─────────────────────────────────┐                  │
│ │   │ Toolset inspects context:       │                  │
│ │   │ - User role                     │                  │
│ │   │ - Session state                 │                  │
│ │   │ - Available services            │                  │
│ │   │                                 │                  │
│ │   │ Returns: [tool_a, tool_b, ...]  │                  │
│ │   └─────────────────────────────────┘                  │
│ │                                                        │
│ ├── Is it a BaseTool?                                    │
│ │   Yes → use directly                                   │
│ │                                                        │
│ └── Is it a callable?                                    │
│     Yes → wrap in FunctionTool                           │
│                                                          │
│ All tools combined → sent to LLM as function declarations│
└──────────────────────────────────────────────────────────┘
```

---

### [ ] 6. Authentication Flow — How Tools Get Credentials

```
┌──────────────────────────────────────────────────────────────────────┐
│ Authentication Flow                                                  │
│                                                                      │
│ ① Tool needs credentials                                            │
│ │  tool_context.request_credential(auth_config)                     │
│ │                                                                    │
│ ② CredentialManager checks:                                         │
│ │  ┌──────────────────────────────────────┐                         │
│ │  │ 1. Load from credential_service     │                         │
│ │  │    → Found and valid? Use it. Done. │                         │
│ │  │                                      │                         │
│ │  │ 2. Load from session state (temp:)  │                         │
│ │  │    → Found? Try exchange/refresh.   │                         │
│ │  │                                      │                         │
│ │  │ 3. Neither found?                   │                         │
│ │  │    → Request from user.             │                         │
│ │  └──────────────────────────────────────┘                         │
│ │                                                                    │
│ ③ If user auth needed:                                              │
│ │  EventActions.requested_auth_configs = [auth_config]              │
│ │  → ADK sends adk_request_credential function call to client       │
│ │                                                                    │
│ ④ Client shows OAuth dialog / API key prompt                        │
│ │  User provides credentials                                        │
│ │                                                                    │
│ ⑤ Client sends credentials back as function response                │
│ │                                                                    │
│ ⑥ AuthPreprocessor intercepts:                                      │
│ │  - Stores credential in session state (temp:credential_key)       │
│ │  - Identifies which tool calls to resume                          │
│ │                                                                    │
│ ⑦ Original tool re-executed with credential available               │
│ │  tool_context.load_credential() → returns the stored credential   │
│ │                                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

Implementing an authenticated tool:

```python
from google.adk.tools.tool_context import ToolContext
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes, OAuth2Auth

GITHUB_AUTH = AuthConfig(
    auth_scheme=OAuth2Auth(
        authorization_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scopes=["repo", "read:user"],
    ),
    raw_auth_credential=AuthCredential(
        auth_type=AuthCredentialTypes.OAUTH2,
        oauth2={"client_id": "your_client_id", "client_secret": "your_secret"},
    ),
)

async def list_repos(username: str, tool_context: ToolContext) -> str:
    """List GitHub repositories for a user."""
    # Try to load existing credential
    credential = tool_context.load_credential(
    "github_token",
    GITHUB_AUTH,
    )

    if not credential or not credential.oauth2.access_token:
        # No credential — request from user
        tool_context.request_credential(GITHUB_AUTH)
        return "Please authenticate with GitHub to continue."

    # Use the credential
    token = credential.oauth2.access_token
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.github.com/users/{username}/repos",
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            repos = await resp.json()
            return "\n".join(r["full_name"] for r in repos[:10])

agent = Agent(
    name="github_agent",
    tools=[list_repos],
)
```

---

### [ ] 7. Artifacts — File Management Across Sessions

```
┌──────────────────────────────────────────────────────────────────┐
│ Artifact System                                                  │
│                                                                  │
│ ┌───────────────────────────────────────────────┐                │
│ │ ArtifactService                               │                │
│ │                                               │                │
│ │ save_artifact(filename, part) → version_id    │                │
│ │ load_artifact(filename, version?) → Part      │                │
│ │ list_artifact_keys() → [filenames]            │                │
│ │ delete_artifact(filename)                     │                │
│ │ list_versions(filename) → [0, 1, 2, ...]     │                │
│ └───────────────────────────────────────────────┘                │
│                                                                  │
│ Storage backends:                                                │
│ ├── InMemory        (dev/test)                                   │
│ ├── FileArtifact    (local disk)                                 │
│ └── GcsArtifact     (Google Cloud)                               │
│                                                                  │
│ Scoping:                                                         │
│ ├── Session-scoped: tied to one conversation                     │
│ └── User-scoped: accessible across all sessions (session_id=None)│
│                                                                  │
│ Versioning:                                                      │
│ save("report.pdf", v1) → version 0                              │
│ save("report.pdf", v2) → version 1                              │
│ load("report.pdf")     → latest (version 1)                     │
│ load("report.pdf", 0)  → version 0 (original)                   │
└──────────────────────────────────────────────────────────────────┘
```

Using artifacts in tools:

```python
from google.adk.tools.tool_context import ToolContext
from google.genai import types
import json

async def generate_report(topic: str, tool_context: ToolContext) -> str:
    """Generate a report and save it as an artifact."""
    report = f"# Report on {topic}\n\nDetailed analysis..."

    # Save as artifact (returns version number)
    version = await tool_context.save_artifact(
    filename=f"report_{topic}.md",
    artifact=types.Part.from_text(report),
    )

    return f"Report saved as 'report_{topic}.md' (version {version})"

async def load_previous_report(filename: str, tool_context: ToolContext) -> str:
    """Load a previously generated report."""
    artifact = await tool_context.load_artifact(filename=filename)
    if artifact is None:
        return f"No report found with name '{filename}'"
    return artifact.text
```

---

### [ ] 8. Code Executors — Running Code in Agents

```
┌──────────────────────────────────────────────────────────────────┐
│ Code Execution Pipeline                                          │
│                                                                  │
│ LLM generates code block in response                             │
│ │                                                                │
│ ▼                                                                │
│ Response processor extracts code:                                │
│ ```python                                                        │
│ import pandas as pd                                              │
│ df = pd.read_csv("data.csv")                                    │
│ print(df.describe())                                             │
│ ```                                                              │
│ │                                                                │
│ ▼                                                                │
│ ┌──────────────────────────────────┐                             │
│ │ BaseCodeExecutor.execute_code() │                             │
│ │                                  │                             │
│ │ Implementations:                 │                             │
│ │ ├── BuiltInCodeExecutor          │ ← Jupyter-like, in-process │
│ │ ├── ContainerCodeExecutor        │ ← Docker sandbox           │
│ │ ├── VertexAICodeExecutor         │ ← Google Cloud             │
│ │ ├── UnsafeLocalCodeExecutor      │ ← Direct execution (dev)   │
│ │ └── GKECodeExecutor              │ ← Kubernetes pods          │
│ └──────────────────────────────────┘                             │
│ │                                                                │
│ ▼                                                                │
│ CodeExecutionResult:                                             │
│ ├── stdout: "  col1   col2\nmean  42.0  ..."                    │
│ ├── stderr: ""                                                   │
│ └── output_files: ["chart.png"] → saved as artifacts            │
│ │                                                                │
│ ▼                                                                │
│ Output appended to conversation → LLM sees results              │
│ Output files saved as artifacts → user can download              │
└──────────────────────────────────────────────────────────────────┘
```

Configuration:

```python
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk import Agent

agent = Agent(
    name="data_analyst",
    model="gemini-2.5-pro",
    instruction="""You are a data analyst. Write Python code to analyze data.
    Use pandas for data manipulation and matplotlib for charts.""",
    code_executor=BuiltInCodeExecutor(),
    # Note: BuiltInCodeExecutor delegates to the model's built-in code
    # execution (Gemini 2.0+). It has no constructor parameters — code
    # execution configuration is handled by the model itself.
)
```

---

### [ ] 9. Planners — Structured Reasoning

**PlanReActPlanner** — adds explicit planning/reasoning tags to the LLM's response:

```
┌──────────────────────────────────────────────────────────────────┐
│ PlanReAct Flow                                                   │
│                                                                  │
│ User: "Research quantum computing and write a summary"           │
│ │                                                                │
│ ▼                                                                │
│ /*PLANNING*/                                                     │
│ 1. Search for recent quantum computing breakthroughs             │
│ 2. Read key papers and articles                                  │
│ 3. Synthesize findings into a summary                            │
│ /*END PLANNING*/                                                 │
│ │                                                                │
│ ▼                                                                │
│ /*ACTION*/                                                       │
│ Call: web_search("quantum computing breakthroughs 2025")         │
│ /*END ACTION*/                                                   │
│ │                                                                │
│ ▼                                                                │
│ Tool result: [article1, article2, ...]                           │
│ │                                                                │
│ ▼                                                                │
│ /*REASONING*/                                                    │
│ Found 3 relevant articles. article1 covers error correction,     │
│ article2 covers qubit scaling. Need to read article3.            │
│ /*END REASONING*/                                                │
│ │                                                                │
│ ▼                                                                │
│ /*ACTION*/                                                       │
│ Call: read_article(url=article3.url)                             │
│ /*END ACTION*/                                                   │
│ │                                                                │
│ ▼                                                                │
│ /*REPLANNING*/                                                   │
│ All research done. Proceeding to write summary.                  │
│ /*END REPLANNING*/                                               │
│ │                                                                │
│ ▼                                                                │
│ /*FINAL_ANSWER*/                                                 │
│ # Quantum Computing: 2025 Breakthroughs                          │
│ Recent advances include...                                       │
│ /*END FINAL_ANSWER*/                                             │
└──────────────────────────────────────────────────────────────────┘
```

**BuiltInPlanner (model-native thinking):**

```python
from google.adk.planners import BuiltInPlanner
from google.genai import types

agent = Agent(
    name="thinker",
    model="gemini-2.5-pro",
    planner=BuiltInPlanner(
    thinking_config=types.ThinkingConfig(
    thinking_budget=2048, # Token budget for internal reasoning
    ),
    ),
)
```

---

### [ ] 10. A2A (Agent-to-Agent Protocol) — Cross-Service Communication

A2A enables agents running in different services to communicate:

```
┌──────────────────────────────────────────────────────────────────────┐
│ A2A Communication                                                    │
│                                                                      │
│ Service A (your app)            Service B (remote agent)             │
│ ┌──────────────────┐            ┌──────────────────┐                │
│ │ Your Agent       │            │ Remote Agent     │                │
│ │                  │   A2A      │                  │                │
│ │ "I need weather  │──Protocol──▶│ Weather service  │                │
│ │  data"           │            │ processes request │                │
│ │                  │◀────────────│ returns data     │                │
│ └──────────────────┘            └──────────────────┘                │
│                                                                      │
│ Event Conversion:                                                    │
│ ADK Event ──convert──▶ A2A Message ──convert──▶ ADK Event           │
│                                                                      │
│ Metadata preserved:                                                  │
│ ├── app_name, user_id, session_id                                   │
│ ├── invocation_id, author, event_id                                 │
│ ├── branch info                                                      │
│ ├── grounding_metadata                                               │
│ └── custom_metadata (prefixed with "_adk_")                         │
└──────────────────────────────────────────────────────────────────────┘
```

A2aAgentExecutor:

```python
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

executor = A2aAgentExecutor(
    runner=my_runner, # Or a callable that returns a Runner
    config=A2aAgentExecutorConfig(
        # Interceptors use ExecuteInterceptor with before_agent/after_agent/after_event hooks
        execute_interceptors=[
            ExecuteInterceptor(
                before_agent=validate_request,   # async (RequestContext) -> RequestContext
                after_agent=transform_response,  # async (ExecutorContext, TaskStatusUpdateEvent) -> TaskStatusUpdateEvent
                after_event=log_event,           # async (ExecutorContext, A2AEvent, Event) -> A2AEvent | None
            ),
        ],
    ),
)
```

---

### [ ] 11. Event Compaction — Managing Long Conversations

As conversations grow, the context window fills up. Compaction summarizes old events:

```
Before compaction (20 events, ~8000 tokens):
┌──────────────────────────────────────────┐
│ Event 1: User asks about weather         │
│ Event 2: Agent calls get_weather         │
│ Event 3: Tool returns weather data       │
│ Event 4: Agent responds with weather     │
│ Event 5: User asks about restaurants     │
│ ...                                      │
│ Event 18: User asks about hotel          │
│ Event 19: Agent calls search_hotels      │
│ Event 20: Agent responds with hotels     │
└──────────────────────────────────────────┘

After compaction (summary + recent events):
┌──────────────────────────────────────────┐
│ [Compaction Summary]:                    │
│ "User asked about weather in Tokyo       │
│  (sunny, 22C), then searched for         │
│  restaurants (found 3 options), then     │
│  discussed pricing..."                   │
│                                          │
│ Event 18: User asks about hotel          │
│ Event 19: Agent calls search_hotels      │
│ Event 20: Agent responds with hotels     │
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
        compaction_interval=5, # Compact every 5 turns
        overlap_size=1, # Keep 1 recent turn uncompacted
    ),
)
```

---

### [ ] 12. Content Filtering — How Events Become Context

Not every event in the session becomes part of the LLM context. The `contents` processor filters:

```
┌──────────────────────────────────────────────────────────────────┐
│ Content Filtering Rules                                          │
│                                                                  │
│ Session has 50 events. Which ones go to the LLM?                 │
│                                                                  │
│ For each event:                                                  │
│ │                                                                │
│ ├── Empty content?        → SKIP                                 │
│ │                                                                │
│ ├── Wrong branch?         → SKIP                                 │
│ │   (events from other agent                                     │
│ │    branches are filtered out)                                  │
│ │                                                                │
│ ├── Framework event?      → SKIP                                 │
│ │   (auth requests, confirmations)                               │
│ │                                                                │
│ ├── Thought-only parts?   → SKIP (unless planning)              │
│ │                                                                │
│ ├── Compaction event?     → INCLUDE as summary                   │
│ │                                                                │
│ ├── Rewind event?         → Undo previous events                 │
│ │                                                                │
│ └── Normal content?       → INCLUDE                              │
│                                                                  │
│ Special modes:                                                   │
│ ├── include_contents='default' → full filtered history           │
│ └── include_contents='none'    → current turn only               │
└──────────────────────────────────────────────────────────────────┘
```

---

### [ ] 13. Function Call ID Management

ADK tracks function calls with client-side IDs:

```python
# ADK generates IDs prefixed with "adk-"
function_call_id = f"adk-{uuid4().hex}"

# These IDs enable:
# 1. Matching async tool responses to their original calls
# 2. Tracking tool execution across events
# 3. Deduplication of parallel results
```

```
LLM response contains:
 FunctionCall(id="server-123", name="get_weather", args={...})
 │
 ▼
ADK wraps with client ID:
 FunctionCall(id="adk-abc123", name="get_weather", args={...})
 │
 ▼
Tool executes, result tagged with same ID:
 FunctionResponse(id="adk-abc123", response={...})
 │
 ▼
Before sending back to LLM, ADK strips the "adk-" prefix:
 FunctionResponse(id="server-123", response={...})
```

---

### [ ] 14. Streaming and Live Mode

Standard streaming:

```python
# Events are yielded as they're produced
async for event in runner.run_async(session_id, user_id, message):
    if event.content:
        for part in event.content.parts:
            if part.text:
                print(part.text, end="", flush=True) # Stream text
            elif part.function_call:
                print(f"\n[Calling {part.function_call.name}...]")
```

Live mode (bidirectional streaming):

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

```python
# Live mode tools receive a LiveRequestQueue for input streaming
async def live_tool(
    query: str,
    input_stream: LiveRequestQueue, # ADK detects this parameter
    tool_context: ToolContext,
) -> AsyncGenerator[str, None]:
    """A streaming tool that receives live input."""
    async for chunk in input_stream:
        processed = process(chunk)
        yield processed # Stream results back
```

---

### [ ] 15. Advanced Agent Patterns

**Pattern: Guardrail Agent**

```python
async def safety_check(callback_context, llm_response):
    """Block unsafe responses before they reach the user."""
    if llm_response and llm_response.content:
        text = str(llm_response.content)
        if contains_pii(text):
            # Replace response with safe version
            from google.adk.models import LlmResponse
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="I can't share personal information.")],
                ),
            )
    return None # Allow original response

agent = Agent(
    name="safe_agent",
    after_model_callback=safety_check,
)
```

**Pattern: Retry with Reflection**

```python
async def retry_on_tool_error(tool, args, tool_context, tool_response):
    """If a tool returns an error, add context for the LLM to retry smarter."""
    if isinstance(tool_response, dict) and "error" in tool_response:
        error = tool_response["error"]
        # Enrich error with guidance
        return {
            "error": error,
            "suggestion": f"The tool '{tool.name}' failed. "
            f"Consider adjusting your parameters and trying again.",
            "failed_args": args,
        }
    return None
```

**Pattern: Dynamic Instruction Based on Conversation Phase**

```python
async def phase_aware_instruction(ctx) -> str:
    """Change agent behavior based on conversation progress."""
    turn_count = ctx.state.get("temp:turn_count", 0)
    ctx.state["temp:turn_count"] = turn_count + 1

    if turn_count == 0:
        return """You are a sales assistant. Start by greeting the customer
        and asking what they're looking for."""
    elif turn_count < 5:
        return """You are a sales assistant in the discovery phase.
        Ask about preferences, budget, and requirements."""
    else:
        return """You are a sales assistant in the closing phase.
        Summarize options and guide toward a purchase decision."""

agent = Agent(
    name="adaptive_sales",
    instruction=phase_aware_instruction,
)
```

## Examples

See the inline code throughout "How It Works" above. Each section contains production-ready patterns from the adk-python source tree.

## Gotchas

- **Processor order matters** — request processors run in a fixed sequence. If you override or extend a flow, inserting a processor in the wrong position can break downstream processors.
- **Plugin callbacks run before agent callbacks** — for `before_*` hooks, plugins execute first. For `after_*` hooks, agent callbacks run first, then plugins. This asymmetry is intentional but easy to forget.
- **`AutoFlow` silently adds `transfer_to_agent`** — if your agent has `sub_agents`, `AutoFlow` injects a transfer tool. This can conflict if you define your own tool with a similar name.
- **`AgentTool` creates isolated sessions** — the child agent gets its own session and conversation history. State changes in the child do not propagate to the parent unless explicitly handled via state deltas.
- **`BaseToolset.get_tools()` is called per-request** — tools are resolved dynamically before each LLM call. If your toolset is expensive to evaluate, cache the results.
- **Auth flow requires resumability** — credential requests pause the agent. Without proper `ResumabilityConfig`, the flow cannot resume after the user provides credentials.
- **Compaction loses detail** — compacted events are replaced by a summary. If downstream logic depends on specific past tool responses, compaction may break it.
- **Content filtering hides events** — events from other branches, framework events, and empty events are silently excluded from LLM context. This can be confusing when debugging why the model "forgot" something.
- **Function call IDs are rewritten** — ADK wraps server IDs with `adk-` prefixed client IDs during execution, then strips them before sending back. Do not rely on raw IDs from LLM responses.

## Related

- [00-onboarding-guide.md](00-onboarding-guide.md) — Start here if you are new
- [20-best-practices.md](20-best-practices.md) — Common mistakes to avoid
- [07-events.md](07-events.md) — Event class deep dive
- [05-flows.md](05-flows.md) — Flow architecture
- [09-tools.md](09-tools.md) — Tool system reference
- [10-apps.md](10-apps.md) — App container and plugins
- [11-memory.md](11-memory.md) — Memory and long-term recall
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request
