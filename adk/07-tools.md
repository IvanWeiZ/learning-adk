# Tools — Pluggable Capabilities

**Source:** [`tools/base_tool.py`](../adk-python/src/google/adk/tools/base_tool.py) · [`tools/base_toolset.py`](../adk-python/src/google/adk/tools/base_toolset.py) · [`tools/tool_context.py`](../adk-python/src/google/adk/tools/tool_context.py)

---

## [ ] What It Is

Tools give agents the ability to take actions beyond generating text. The LLM requests a tool call by name with arguments; ADK dispatches to the matching `BaseTool`, runs it, and feeds the result back to the LLM.

Tools attach to an agent via `LlmAgent(tools=[...])`. They can be:
- Python callables (auto-wrapped in `FunctionTool`)
- `BaseTool` instances
- `BaseToolset` instances (dynamic collections of tools)

---

## [ ] BaseTool — The Interface

```python
class BaseTool(ABC):
    name: str          # must match exactly what the LLM will call
    description: str   # shown to the LLM; affects when it chooses to use the tool
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

## [ ] FunctionTool — Wrapping Python Functions

The simplest way to create a tool: just pass a Python function.

```python
def get_weather(city: str) -> dict:
    """Returns the current weather for a city."""
    return {'temp': 72, 'condition': 'sunny'}

agent = LlmAgent(tools=[get_weather])
# → FunctionTool(func=get_weather) is created automatically
```

`FunctionTool` uses Python type hints and docstrings to auto-generate the `FunctionDeclaration` (schema) shown to the LLM. Parameter names, types, and descriptions come from the function signature and docstring.

**Special parameter:** If a function parameter is named `tool_context: ToolContext`, ADK injects the `ToolContext` automatically — the LLM never sees it.

```python
def save_note(text: str, tool_context: ToolContext) -> str:
    """Saves a note to the session."""
    tool_context.state['note'] = text
    return 'Note saved.'
```

---

## [ ] BaseToolset — Dynamic Tool Collections

A `BaseToolset` provides a variable set of tools determined at runtime:

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

The flow calls `toolset.get_tools(ctx)` before each LLM call to get the current tool list. This is how MCP toolsets, OpenAPI toolsets, and LangChain/CrewAI adapters work — they discover tools dynamically.

---

## [ ] ToolContext — What Tools Can Do

`ToolContext` is passed to every `run_async` call. It gives tools access to session state and ADK services:

```python
class ToolContext:
    # Read/write session state:
    state: State                       # tool_context.state['key'] = value

    # Store files:
    async def save_artifact(filename, artifact) -> int   # returns version
    async def load_artifact(filename, version=None)      # returns artifact

    # Request OAuth credentials:
    def request_credential(auth_config: AuthConfig) -> None

    # Interact with memory:
    async def search_memory(query: str) -> SearchMemoryResponse

    # Agent transfer (from within a tool):
    actions.transfer_to_agent = 'agent_name'
```

---

## [ ] Built-in Tools

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

## [ ] Tool Resolution in LlmAgent

```python
agent = LlmAgent(tools=[
    my_function,           # → FunctionTool(func=my_function)
    GoogleSearchTool(),    # → used as-is (BaseTool)
    my_toolset,            # → BaseToolset.get_tools() called per LLM turn
])
```

When there are multiple tools, `GoogleSearchTool` and `VertexAiSearchTool` are automatically wrapped in an agent-based workaround (they can't mix with other tools natively in the Gemini API). This is transparent to the user.

---

## [ ] Long-Running Tools

When `is_long_running=True`, the tool starts an operation and returns an operation ID. ADK:
1. Yields a "paused" event with `long_running_tool_ids`
2. The client polls for completion using the operation ID
3. On the next invocation, the result is provided as a function response and the agent resumes

---

## [ ] Tool Confirmation (Human-in-the-Loop)

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

## [ ] Related Files

- [`tools/base_tool.py`](../adk-python/src/google/adk/tools/base_tool.py) — abstract base
- [`tools/base_toolset.py`](../adk-python/src/google/adk/tools/base_toolset.py) — dynamic tool collections
- [`tools/tool_context.py`](../adk-python/src/google/adk/tools/tool_context.py) — tool runtime context
- [`tools/function_tool.py`](../adk-python/src/google/adk/tools/function_tool.py) — Python function wrapper
- [`tools/mcp_tool/`](../adk-python/src/google/adk/tools/mcp_tool/) — MCP protocol support
- [`tools/openapi_tool/`](../adk-python/src/google/adk/tools/openapi_tool/) — OpenAPI/REST tools
- [`tools/google_search_tool.py`](../adk-python/src/google/adk/tools/google_search_tool.py) — Google Search
