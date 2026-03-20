# 09 — Tools: Pluggable Capabilities

> **Official docs:** [Tools](https://google.github.io/adk-docs/tools-custom/) | **Source:** [`tools/base_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/base_tool.py) · [`tools/base_toolset.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/base_toolset.py) · [`tools/tool_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/tool_context.py) · [`tools/function_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/function_tool.py) | **Prereqs:** [04-agents.md](04-agents.md), [05-flows.md](05-flows.md), [07-events.md](07-events.md)

## At a Glance

```
┌─────────────────────────────────────────────────────────┐
│                      LlmAgent                           │
│  tools=[func, BaseTool(), BaseToolset()]                │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Tool Resolution                         │
│  func        → auto-wrapped as FunctionTool             │
│  BaseTool()  → used as-is                               │
│  BaseToolset → get_tools() called per LLM turn          │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              FunctionDeclaration                        │
│  schema sent to LLM → LLM emits FunctionCall           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Tool Execution Pipeline                    │
│  before_tool_cb → tool.run_async() → after_tool_cb     │
│  (ToolContext injected)                                 │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│         FunctionResponse → back to LLM                  │
└─────────────────────────────────────────────────────────┘
```

Tools let agents take actions beyond text generation. The LLM requests a tool call; ADK dispatches, runs, and feeds results back. Tools attach to an agent via `LlmAgent(tools=[...])`. They can be Python callables (auto-wrapped in `FunctionTool`), `BaseTool` instances, or `BaseToolset` instances (dynamic collections of tools).

## Class Hierarchy

```
BaseTool (ABC)
├── FunctionTool        — wraps plain Python functions
├── AgentTool           — wraps a sub-agent as a tool
├── LongRunningFunctionTool — async operations with polling
├── GoogleSearchTool    — Google Search grounding
└── VertexAiSearchTool  — Vertex AI Search

BaseToolset (ABC)
├── McpToolset          — Model Context Protocol
├── OpenAPIToolset      — REST APIs via OpenAPI spec
├── LangchainTool       — LangChain tool wrapper
├── CrewaiTool          — CrewAI tool wrapper
└── BigQueryToolset     — BigQuery operations
```

## Key API

### BaseTool — The Interface

```python
class BaseTool(ABC):
    name: str # must match exactly what the LLM will call
    description: str # shown to the LLM; affects when it chooses to use the tool
    is_long_running: bool = False
    # If True, the tool returns an operation ID first, finishes later.
    # Runner pauses the invocation until the operation completes.

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        # Returns the OpenAPI-style schema shown to the LLM.
        # Return None for built-in tools (e.g. GoogleSearch) that don't need it.

    async def run_async(self, *, args: dict, tool_context: ToolContext) -> Any:
        # Execute the tool. Return value becomes the FunctionResponse content.
        # Can be a dict, string, or any JSON-serializable value.

    async def process_llm_request(self, *, tool_context, llm_request) -> None:
        # Called during preprocessing to add this tool to the LlmRequest.
        # Default: calls llm_request.append_tools([self])
        # Override for tools that need special request manipulation (e.g. grounding).
```

### BaseToolset — Dynamic Tool Collections

```python
class BaseToolset(ABC):
    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> list[BaseTool]:
        # Return the list of tools available in the current context.
        # Can vary based on user, session state, etc.

    async def close(self) -> None:
        # Clean up resources (connections, etc.)

```

The flow calls `toolset.get_tools(ctx)` before each LLM call. MCP, OpenAPI, LangChain, and CrewAI toolsets use this for dynamic discovery.

### ToolContext — What Tools Can Do

`ToolContext` is passed to every `run_async`. Provides access to state and services:

```python
class ToolContext:
    # Read/write session state:
    state: State # tool_context.state['key'] = value

    # Store files:
    async def save_artifact(filename, artifact) -> int # returns version
    async def load_artifact(filename, version=None) # returns artifact

    # Request OAuth credentials:
    def request_credential(auth_config: AuthConfig) -> None

    # Interact with memory:
    async def search_memory(query: str) -> SearchMemoryResponse

    # Agent transfer (from within a tool):
    actions.transfer_to_agent = 'agent_name'
```

### Built-in Tools

| Tool | Import | What it does |
|------|--------|-------------|
| `google_search` | `google.adk.tools` | Google Search grounding |
| `VertexAiSearchTool` | `google.adk.tools` | Vertex AI Search |
| `BuiltInCodeExecutor` | `google.adk.code_executors` | Model-native code execution |
| `McpToolset` | `google.adk.tools.mcp_tool` | Model Context Protocol tools |
| `OpenAPIToolset` | `google.adk.tools.openapi_tool` | Any REST API via OpenAPI spec |
| `LangchainTool` | `google.adk.tools.langchain_tool` | Wrap any LangChain tool |
| `CrewaiTool` | `google.adk.tools.crewai_tool` | Wrap any CrewAI tool |
| `BigQueryToolset` | `google.adk.tools` | BigQuery operations |

## How It Works

### Tool Invocation Lifecycle

```
LLM response contains FunctionCall(name="get_weather", args={"city": "Tokyo"})
│
├── before_tool_callback(tool, args, tool_context)
│   ├── returns dict? → use as result, skip tool execution
│   └── returns None? → continue
│
├── tool.run_async(args=args, tool_context=tool_context)
│   ├── get_weather("Tokyo") → {temp: 18}
│   └── on error: on_tool_error_callback (if set)
│
├── after_tool_callback(tool, args, tool_context, result)
│   ├── returns dict? → replace result
│   └── returns None? → keep original result
│
└── FunctionResponse event yielded
    └── back to LLM in next loop iteration
```

### Default Error Behavior

If your tool function raises an exception and no `on_tool_error_callback` is set:
- The exception **propagates up** and terminates the entire invocation
- The LLM does **not** get a chance to retry — the `run_async()` generator raises the exception to your code
- To handle gracefully: set `on_tool_error_callback` on the agent, or wrap your tool in try/except and return an error dict

### Tool Resolution in LlmAgent

```
LlmAgent(tools=[...]) — resolution at each LLM turn
│
├── my_function (callable)
│   └── auto-wrapped as FunctionTool(func=my_function)
│
├── GoogleSearchTool() (BaseTool instance)
│   └── used as-is
│
└── my_toolset (BaseToolset instance)
    └── BaseToolset.get_tools() called per LLM turn
```

```python
agent = LlmAgent(tools=[
    my_function, # → FunctionTool(func=my_function)
    GoogleSearchTool(), # → used as-is (BaseTool)
    my_toolset, # → BaseToolset.get_tools() called per LLM turn
])
```

`GoogleSearchTool` and `VertexAiSearchTool` cannot mix with function tools in one API call. ADK auto-creates a hidden sub-agent for isolation.

### Long-Running Tools

```
LongRunningFunctionTool execution
│
├── 1. Tool returns operation ID
│   └── signals this is a long-running operation
│
├── 2. Runner yields "paused" event
│   └── event.long_running_tool_ids is set
│       └── is_final_response() returns True
│
├── 3. Client polls for completion
│   └── uses the operation ID to check status
│
└── 4. Next invocation: result provided as FunctionResponse
    └── agent resumes with the completed result
```

When `is_long_running=True`, the tool returns an operation ID. ADK:
1. Yields a "paused" event with `long_running_tool_ids`
2. The client polls for completion using the operation ID
3. On the next invocation, the result is provided as a function response and the agent resumes

####Long-Running Tool Lifecycle Across 2 Invocations

```
════════════════════════════════════════════════════════════
  INVOCATION 1 — tool starts, runner pauses
════════════════════════════════════════════════════════════

├── User
│      "Export my report as PDF"
│
├── LLM responds
│      FunctionCall(name="export_report", args={"report_id": "r-42"})
│
├── Tool executes
│      export_report.run_async()
│      returns {"job_id": "job-r-42-pdf", "status": "started"}
│
├── Flow detects is_long_running=True
│      sets event.long_running_tool_ids = {"fc-001"}
│
├── Event yielded to caller
│      content:              FunctionResponse("export_report", {"job_id": "..."})
│      long_running_tool_ids: {"fc-001"}
│      is_final_response():  True ← runner pauses here
│
└── Invocation ends
       Client receives job_id
       Client starts polling the external system

─── time passes, client polls, job completes ───

════════════════════════════════════════════════════════════
  INVOCATION 2 — client sends result, agent resumes
════════════════════════════════════════════════════════════

├── Client calls runner.run_async() with new_message:
│      FunctionResponse(
│          id   = "fc-001"        ← matches original call ID
│          name = "export_report"
│          response = {
│              "job_id": "job-r-42-pdf",
│              "status": "done",
│              "url":    "https://storage.example.com/report.pdf"
│          }
│      )
│
├── LLM receives the completed result in its context
│      sees the tool response as part of conversation history
│
├── LLM responds
│      "Your report is ready! Download it at https://..."
│
└── is_final_response() = True
       normal completion
```

### Tool Confirmation (Human-in-the-Loop)

Tools can request human confirmation before executing:

```python
class MyTool(BaseTool):
    async def run_async(self, args, tool_context):
        # Request confirmation via the clean API
        tool_context.request_confirmation(
            hint='Delete file?',
            payload={'filename': args['filename']}
        )
        # Tool execution pauses; client shows confirmation dialog
        # On next invocation, if confirmed, the tool runs for real
```

`ToolConfirmation` uses `hint` and `payload` fields (not `title`/`message`).

## Examples

### FunctionTool — Wrapping Python Functions

Pass a Python function:

```python
def get_weather(city: str) -> dict:
    """Returns the current weather for a city."""
    return {'temp': 72, 'condition': 'sunny'}

agent = LlmAgent(tools=[get_weather])
# → FunctionTool(func=get_weather) is created automatically
```

`FunctionTool` auto-generates `FunctionDeclaration` from type hints and docstrings.

Parameter named `tool_context: ToolContext` is auto-injected (hidden from LLM).

```python
def save_note(text: str, tool_context: ToolContext) -> str:
    """Saves a note to the session."""
    tool_context.state['note'] = text
    return 'Note saved.'
```

### Error Handling

```python
# Option 1: Handle inside the tool (recommended for simple cases)
def get_weather(city: str) -> dict:
    try:
        return call_weather_api(city)
    except Exception as e:
        return {"error": str(e)} # LLM sees the error and can respond appropriately

# Option 2: Use on_tool_error_callback (handles all tools at once)
agent = LlmAgent(
    tools=[get_weather],
    on_tool_error_callback=lambda tool, args, ctx, err: {"error": str(err)},
)
```

### MCP (Model Context Protocol) Tools

> **Official docs:** [MCP](https://modelcontextprotocol.io/) | **Source:** [`tools/mcp_tool/`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/mcp_tool/)

MCP is an open protocol for connecting LLMs to external tools and data sources. ADK's `McpToolset` wraps MCP servers as a `BaseToolset`, making any MCP-compatible tool available to your agents.

```
How MCP fits into ADK:
│
├── MCP Server
│      external process exposing tools via MCP protocol
│      (e.g., filesystem, database, API, browser)
│
├── Connection
│      StdioServerParameters  — launch server as subprocess (stdin/stdout)
│      SseServerParams        — connect to running server via HTTP SSE
│
├── McpToolset
│      wraps MCP connection as a BaseToolset
│      get_tools() discovers available tools from the MCP server
│      each tool becomes a BaseTool with auto-generated schema
│
└── LlmAgent
       receives MCP tools alongside regular FunctionTools
       LLM sees them identically — calls them the same way
```

```python
# Example: Connect to an MCP filesystem server via stdio
from mcp import StdioServerParameters
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

# McpToolset wraps an MCP server as a BaseToolset
filesystem_tools = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp/workspace"],
    ),
)

agent = LlmAgent(
    name="file_agent",
    model="gemini-2.5-flash",
    instruction="You can read and write files in /tmp/workspace.",
    tools=[filesystem_tools],  # passed as a toolset, not individual tools
)

# At runtime:
# 1. McpToolset.get_tools(ctx) launches the MCP server subprocess
# 2. Discovers available tools (read_file, write_file, list_directory, etc.)
# 3. Each tool becomes a BaseTool with FunctionDeclaration from MCP schema
# 4. LLM calls them like any other tool
# 5. McpToolset.close() shuts down the subprocess when done
```

```python
# Example: Connect to a running MCP server via SSE
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams as SseServerParams

api_tools = McpToolset(
    connection_params=SseServerParams(
        url="http://localhost:8080/mcp",
    ),
)

agent = LlmAgent(
    name="api_agent",
    model="gemini-2.5-flash",
    tools=[api_tools],
)
```

**Key points:**
- `McpToolset` is a `BaseToolset` — pass it to `tools=[]` directly, not individual tools
- Tool discovery happens dynamically via `get_tools()` before each LLM call
- The old `MCPToolset` class name is deprecated — use `McpToolset`
- MCP servers run as separate processes; `McpToolset.close()` cleans them up
- Each MCP tool gets a `FunctionDeclaration` auto-generated from MCP's tool schema

---

## Gotchas

- `GoogleSearchTool` and `VertexAiSearchTool` cannot mix with function tools in one API call — ADK auto-creates a hidden sub-agent for isolation
- If your tool raises an exception and no `on_tool_error_callback` is set, the exception **propagates up** and terminates the entire invocation — the LLM does **not** get a chance to retry
- `ToolConfirmation` uses `hint` and `payload` fields, not `title`/`message`
- Tool `name` must match exactly what the LLM will call
- A parameter named `tool_context: ToolContext` is auto-injected and hidden from the LLM schema

## Related

- [`tools/base_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/base_tool.py) — abstract base
- [`tools/base_toolset.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/base_toolset.py) — dynamic tool collections
- [`tools/tool_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/tool_context.py) — tool runtime context
- [`tools/function_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/function_tool.py) — Python function wrapper
- [`tools/mcp_tool/`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/mcp_tool/) — MCP protocol support
- [`tools/openapi_tool/`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/openapi_tool/) — OpenAPI/REST tools
- [`tools/google_search_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/google_search_tool.py) — Google Search
- [12-artifacts.md](12-artifacts.md) — Artifact service deep dive (save_artifact, load_artifact)
- [13-auth.md](13-auth.md) — Authentication deep dive (OAuth, credential service)
