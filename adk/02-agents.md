# Agents — Blueprints for Behavior

**Source:** [`agents/base_agent.py`](../adk-python/src/google/adk/agents/base_agent.py) · [`agents/llm_agent.py`](../adk-python/src/google/adk/agents/llm_agent.py) · [`agents/invocation_context.py`](../adk-python/src/google/adk/agents/invocation_context.py)

---

## What It Is

Agents are the primary building block in ADK. An agent defines *what* an AI should do: which model to use, which tools it has, what its system prompt is, and how it should behave. Agents do **not** hold conversation state — that lives in `Session`.

---

## Class Hierarchy

```
BaseAgent           (base_agent.py)   — abstract, common contract
    ├── LlmAgent    (llm_agent.py)    — primary: calls an LLM in a loop
    ├── LoopAgent                     — runs sub-agents in a loop until done
    ├── ParallelAgent                 — runs sub-agents concurrently, merges results
    └── SequentialAgent               — runs sub-agents one after another
```

`Agent` is a type alias for `LlmAgent` — it's what most users instantiate.

---

## BaseAgent — The Contract

Every agent must implement one method:

```python
async def _run_async_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    ...

# Optionally also:
async def _run_live_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    ...  # for video/audio (Live API) mode
```

`BaseAgent` provides the **final** public entry points that wrap `_run_async_impl`:

```python
@final
async def run_async(parent_context: InvocationContext) -> AsyncGenerator[Event, None]:
    # 1. Creates a child InvocationContext for this agent
    # 2. Runs before_agent_callback (can short-circuit the run)
    # 3. Delegates to _run_async_impl
    # 4. Runs after_agent_callback
    # 5. Yields all resulting Events
```

`@final` means subclasses must **not** override `run_async` — only `_run_async_impl`.

### [ ] BaseAgent Fields

```python
name: str               # must be a valid Python identifier, unique in tree
description: str        # one-line summary; LLM uses this to decide delegation
sub_agents: list[BaseAgent]    # child agents in the hierarchy
parent_agent: Optional[BaseAgent]  # set automatically, defaults to None, not in constructor
before_agent_callback: ...     # runs before _run_async_impl; can short-circuit
after_agent_callback: ...      # runs after _run_async_impl; can append events
```

**Agent name constraint:** Cannot be `"user"` (reserved for end-user messages). Must be a valid Python identifier. Names must be unique within the tree.

---

## LlmAgent — The Primary Agent

`LlmAgent` implements `_run_async_impl` by delegating to an `LlmFlow`:

```python
async def _run_async_impl(ctx):
    async for event in self._llm_flow.run_async(ctx):
        self.__maybe_save_output_to_state(event)  # output_key → state_delta
        yield event
```

### [ ] Which flow does it use?

```python
@property
def _llm_flow(self) -> BaseLlmFlow:
    if self.disallow_transfer_to_parent and self.disallow_transfer_to_peers and not self.sub_agents:
        return SingleFlow()   # no agent routing needed
    else:
        return AutoFlow()     # handles agent transfer/delegation
```

### [ ] Key Fields

```python
model: Union[str, BaseLlm]  # e.g. 'gemini-2.5-flash'. Inherits from parent if empty.
                             # Default: '' (empty string). Resolution walks up parent agents;
                             # falls back to class variable DEFAULT_MODEL ('gemini-2.5-flash')
                             # only if no ancestor sets a model.

instruction: Union[str, InstructionProvider]
# System prompt. Supports {variable} placeholders resolved from session state.
# Can be a callable (ctx) -> str for dynamic instructions.

static_instruction: Optional[types.ContentUnion]
# Static content sent as-is (no variable substitution). Used for context caching.

tools: list[ToolUnion]
# Accepts: BaseTool instances, BaseToolset instances, plain Python callables.

generate_content_config: types.GenerateContentConfig
# Temperature, safety settings, etc. Tools/instructions must NOT be set here.

output_schema: Optional[SchemaType]
# Forces structured JSON output. When set, agent cannot use tools.
# SchemaType accepts: type[BaseModel], list[type[BaseModel]], list[primitive], dict, or Schema.

output_key: Optional[str]
# On final response, writes text to session.state[output_key].

input_schema: Optional[type[BaseModel]]
# Validates arguments when this agent is used as a sub-agent tool (AgentTool).
# The parent LLM must provide arguments matching this Pydantic model.

include_contents: Literal['default', 'none']
# 'none' = agent gets no conversation history (stateless mode).

disallow_transfer_to_parent: bool
disallow_transfer_to_peers: bool
# Control agent routing behavior.

planner: Optional[BasePlanner]   # step-by-step planning / thinking
code_executor: Optional[BaseCodeExecutor]  # run generated code blocks
```

### [ ] Callbacks on LlmAgent

LlmAgent adds finer-grained hooks compared to BaseAgent:

| Callback | When | Can short-circuit? |
|----------|------|--------------------|
| `before_agent_callback` | Before `_run_async_impl` | Yes — return Content to skip agent |
| `after_agent_callback` | After `_run_async_impl` | No — only appends extra event |
| `before_model_callback` | Before each LLM call | Yes — return LlmResponse to skip LLM |
| `after_model_callback` | After each LLM call | Yes — return LlmResponse to replace |
| `on_model_error_callback` | On LLM error | Yes — return LlmResponse to recover |
| `before_tool_callback` | Before each tool run | Yes — return dict to skip tool |
| `after_tool_callback` | After each tool run | Yes — return dict to replace result |
| `on_tool_error_callback` | On tool error | Yes — return dict to recover |

**Full signatures for error callbacks:**

```python
def on_model_error_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    error: Exception,
) -> Optional[LlmResponse]: ...

def on_tool_error_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> Optional[dict]: ...
```

### [ ] Key Methods

```python
@classmethod
LlmAgent.set_default_model(model: str | BaseLlm) -> None
# Override the global default model (class variable DEFAULT_MODEL).
# Affects all LlmAgent instances that don't set their own model and have no
# ancestor with a model set. Default is 'gemini-2.5-flash'.

@property
LlmAgent.canonical_model -> BaseLlm
# Resolves the effective model for this agent by walking up parent agents
# until one has a model set. Falls back to DEFAULT_MODEL. Returns a BaseLlm
# instance (wraps a string model name via LLMRegistry if needed).
```

---

## InvocationContext — The Shared Thread

`InvocationContext` is created by `Runner` and flows through every layer. It carries everything needed for one request:

```python
class InvocationContext:
    agent: BaseAgent         # current agent being run
    session: Session         # the full conversation history + state
    invocation_id: str       # unique ID for this run_async() call
    branch: str              # routing path (e.g. 'root.sub.leaf')
    end_invocation: bool     # set to True to stop the entire invocation

    # Services injected by Runner:
    session_service: BaseSessionService
    artifact_service: BaseArtifactService
    memory_service: BaseMemoryService
    credential_service: BaseCredentialService
    plugin_manager: PluginManager
```

When an agent calls a sub-agent, it creates a child context (`model_copy(update={'agent': sub_agent})`). The branch and session are shared.

---

## Agent Trees and Transfer

Agents compose into trees via `sub_agents`. The LLM can transfer control to a sub-agent by calling the special `transfer_to_agent` function. `LlmAgent._run_async_impl` handles this by resuming the right sub-agent on the next turn.

```
root_agent (LlmAgent)
├── search_agent (LlmAgent + GoogleSearchTool)
└── write_agent (LlmAgent, no tools)
```

The LLM in `root_agent` can say "transfer to search_agent", which triggers `EventActions.transfer_to_agent = 'search_agent'`.

---

## Related Files

- [`agents/base_agent.py`](../adk-python/src/google/adk/agents/base_agent.py) — abstract base
- [`agents/llm_agent.py`](../adk-python/src/google/adk/agents/llm_agent.py) — primary implementation
- [`agents/invocation_context.py`](../adk-python/src/google/adk/agents/invocation_context.py) — shared context
- [`agents/loop_agent.py`](../adk-python/src/google/adk/agents/loop_agent.py) — loop composition
- [`agents/parallel_agent.py`](../adk-python/src/google/adk/agents/parallel_agent.py) — parallel composition
- [`agents/sequential_agent.py`](../adk-python/src/google/adk/agents/sequential_agent.py) — sequential composition
- [`agents/callback_context.py`](../adk-python/src/google/adk/agents/callback_context.py) — context passed to callbacks
