# Tools — Pluggable Capabilities

**Source:** [`tools/base_tool.py`](../adk-python/src/google/adk/tools/base_tool.py) · [`tools/base_toolset.py`](../adk-python/src/google/adk/tools/base_toolset.py) · [`tools/tool_context.py`](../adk-python/src/google/adk/tools/tool_context.py)

---

## What It Is

Tools let agents take actions beyond text generation. The LLM requests a tool call; ADK dispatches, runs, and feeds results back.

Tools attach to an agent via `LlmAgent(tools=[...])`. They can be:
- Python callables (auto-wrapped in `FunctionTool`)
- `BaseTool` instances
- `BaseToolset` instances (dynamic collections of tools)

---

## BaseTool — The Interface

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

---

## FunctionTool — Wrapping Python Functions

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

---

## BaseToolset — Dynamic Tool Collections

Variable tool set determined at runtime:

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

---

## ToolContext — What Tools Can Do

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

---

## Built-in Tools

| Tool | Import | What it does |
|------|--------|-------------|
| `google_search` | `google.adk.tools` | Google Search grounding |
| `VertexAiSearchTool` | `google.adk.tools` | Vertex AI Search |
| `BuiltInCodeExecutor` | `google.adk.code_executors` | Model-native code execution |
| `MCPToolset` | `google.adk.tools.mcp_tool` | Model Context Protocol tools |
| `OpenAPIToolset` | `google.adk.tools.openapi_tool` | Any REST API via OpenAPI spec |
| `LangchainTool` | `google.adk.tools.langchain_tool` | Wrap any LangChain tool |
| `CrewaiTool` | `google.adk.tools.crewai_tool` | Wrap any CrewAI tool |
| `BigQueryToolset` | `google.adk.tools` | BigQuery operations |

---

## Tool Invocation Lifecycle

```
LLM response contains FunctionCall(name="get_weather", args={"city": "Tokyo"})
 │
 ▼
 ┌─ before_tool_callback ─┐
 │ Return dict? ──Yes──► use dict as result (skip tool)
 │ Return None? │
 └────────┬───────────────┘
 ▼
 ┌─ tool.run_async() ─────┐
 │ get_weather("Tokyo") │
 │ → {temp: 18} │
 │ on error: │
 │ on_tool_error_cb │
 └────────┬───────────────┘
 ▼
 ┌─ after_tool_callback ──┐
 │ Return dict? ──Yes──► replace result
 │ Return None? │
 └────────┬───────────────┘
 ▼
 FunctionResponse event yielded
 → back to LLM in next loop iteration
```

### Default Error Behavior

If your tool function raises an exception and no `on_tool_error_callback` is set:
- The exception **propagates up** and terminates the entire invocation
- The LLM does **not** get a chance to retry — the `run_async()` generator raises the exception to your code
- To handle gracefully: set `on_tool_error_callback` on the agent, or wrap your tool in try/except and return an error dict

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

---

## Tool Resolution in LlmAgent

```python
agent = LlmAgent(tools=[
    my_function, # → FunctionTool(func=my_function)
    GoogleSearchTool(), # → used as-is (BaseTool)
    my_toolset, # → BaseToolset.get_tools() called per LLM turn
])
```

`GoogleSearchTool` and `VertexAiSearchTool` cannot mix with function tools in one API call. ADK auto-creates a hidden sub-agent for isolation.

---

## Long-Running Tools

When `is_long_running=True`, the tool returns an operation ID. ADK:
1. Yields a "paused" event with `long_running_tool_ids`
2. The client polls for completion using the operation ID
3. On the next invocation, the result is provided as a function response and the agent resumes

---

## Tool Confirmation (Human-in-the-Loop)

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

---

## Related Files

- [`tools/base_tool.py`](../adk-python/src/google/adk/tools/base_tool.py) — abstract base
- [`tools/base_toolset.py`](../adk-python/src/google/adk/tools/base_toolset.py) — dynamic tool collections
- [`tools/tool_context.py`](../adk-python/src/google/adk/tools/tool_context.py) — tool runtime context
- [`tools/function_tool.py`](../adk-python/src/google/adk/tools/function_tool.py) — Python function wrapper
- [`tools/mcp_tool/`](../adk-python/src/google/adk/tools/mcp_tool/) — MCP protocol support
- [`tools/openapi_tool/`](../adk-python/src/google/adk/tools/openapi_tool/) — OpenAPI/REST tools
- [`tools/google_search_tool.py`](../adk-python/src/google/adk/tools/google_search_tool.py) — Google Search
- [12-artifacts.md](12-artifacts.md) — Artifact service deep dive (save_artifact, load_artifact)
- [13-auth.md](13-auth.md) — Authentication deep dive (OAuth, credential service)
