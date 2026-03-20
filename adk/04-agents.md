# 04 — Agents: Blueprints for Behavior

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [`agents/base_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/base_agent.py), [`agents/llm_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/llm_agent.py), [`agents/invocation_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/invocation_context.py) | **Prereqs:** 01, 03

## At a Glance

```
┌──────────────────────────────────────────┐
│             BaseAgent                     │
│  abstract contract:                       │
│    name, sub_agents, callbacks            │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│             Concrete Agents               │
│  LlmAgent        — calls an LLM in loop  │
│  LoopAgent        — repeat until done     │
│  ParallelAgent    — concurrent sub-agents │
│  SequentialAgent  — one after another     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│             LlmAgent Flows                │
│  SingleFlow  — no sub-agents              │
│  AutoFlow    — has sub-agents (routing)   │
└──────────────────────────────────────────┘
```

Agents define AI behavior — model, tools, system prompt, sub-agents — but hold no conversation state (that lives in `Session`). `BaseAgent` provides the abstract contract; `LlmAgent` (aliased as `Agent`) is the primary implementation that calls an LLM in a reason-act loop. Composition agents (`LoopAgent`, `ParallelAgent`, `SequentialAgent`) orchestrate sub-agents without calling an LLM themselves.

---

## Class Hierarchy

```
BaseAgent (base_agent.py) — abstract, common contract
 ├── LlmAgent (llm_agent.py) — primary: calls an LLM in a loop
 ├── LoopAgent — runs sub-agents in a loop until done
 ├── ParallelAgent — runs sub-agents concurrently, merges results
 └── SequentialAgent — runs sub-agents one after another
```

`Agent` is a type alias for `LlmAgent`.

---

## Key API

### [ ] BaseAgent — The Contract

Every agent must implement one method:

```python
async def _run_async_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    ...

# Optionally also:
async def _run_live_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    ... # for video/audio (Live API) mode
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
name: str # must be a valid Python identifier, unique in tree
description: str # one-line summary; LLM uses this to decide delegation
sub_agents: list[BaseAgent] # child agents in the hierarchy
parent_agent: Optional[BaseAgent] # set automatically, defaults to None, not in constructor
before_agent_callback: ... # runs before _run_async_impl; can short-circuit
after_agent_callback: ... # runs after _run_async_impl; can append events
```

**Agent name constraint:** Cannot be `"user"` (reserved for end-user messages). Must be a valid Python identifier. Names must be unique within the tree.

### [ ] LlmAgent Key Methods

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

## How It Works

### [ ] LlmAgent — The Primary Agent

```
LlmAgent._run_async_impl(ctx)
│
├── self._llm_flow.run_async(ctx)
│   └── yields events from the reason-act loop
│
├── __maybe_save_output_to_state(event)
│   └── if output_key set → event.actions.state_delta[key] = text
│
└── yield event
```

`LlmAgent` implements `_run_async_impl` by delegating to an `LlmFlow`:

```python
async def _run_async_impl(ctx):
    async for event in self._llm_flow.run_async(ctx):
        self.__maybe_save_output_to_state(event) # output_key → state_delta
        yield event
```

### [ ] Which Flow Does It Use?

ADK auto-selects the flow based on three conditions:

```
Which flow does LlmAgent use?
│
├─ disallow_transfer_to_parent = True?
│   └─ AND disallow_transfer_to_peers = True?
│       └─ AND sub_agents is empty?
│           ├── Yes to ALL three ──► SingleFlow (pure tool-use loop, no routing)
│           └── No to ANY ─────────► AutoFlow  (adds transfer_to_agent support)
│
└─ Default (no flags set, no sub_agents) ──► AutoFlow
```

`AutoFlow` extends `SingleFlow` — it adds agent transfer/delegation on top of the basic reason-act loop.

### [ ] LlmAgent Key Fields

```python
model: Union[str, BaseLlm] # e.g. 'gemini-2.5-flash'. Inherits from parent if empty.
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

generate_content_config: Optional[types.GenerateContentConfig] = None
# Temperature, safety settings, etc. Tools/instructions must NOT be set here.

output_schema: Optional[SchemaType]
# Forces structured JSON output. When set, agent CANNOT use tools (mutual exclusion).
# SchemaType accepts: type[BaseModel], list[type[BaseModel]], list[primitive], dict, or Schema.
# Want structured output AND tools? Use output_key to capture text, then parse it.
# Or use a 2-agent pipeline: agent 1 uses tools, agent 2 formats with output_schema.

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

planner: Optional[BasePlanner] # step-by-step planning / thinking
code_executor: Optional[BaseCodeExecutor] # run generated code blocks
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

### [ ] InvocationContext — The Shared Thread

```
┌──────────────────────────────────────────┐
│          InvocationContext                │
│  agent          → current BaseAgent       │
│  session        → Session (history+state) │
│  invocation_id  → unique ID for this run  │
│  branch         → routing path            │
│  end_invocation → bool: stop invocation   │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│          Injected Services                │
│  session_service    artifact_service      │
│  memory_service     credential_service    │
│  plugin_manager                           │
└──────────────────────────────────────────┘
```

Created by `Runner`, flows through every layer:

```python
class InvocationContext:
    agent: BaseAgent # current agent being run
    session: Session # the full conversation history + state
    invocation_id: str # unique ID for this run_async() call
    branch: Optional[str] = None # routing path (e.g. 'root.sub.leaf')
    end_invocation: bool # set to True to stop the entire invocation

    # Services injected by Runner:
    session_service: BaseSessionService
    artifact_service: BaseArtifactService
    memory_service: BaseMemoryService
    credential_service: BaseCredentialService
    plugin_manager: PluginManager
```

Sub-agent calls create a child context via `model_copy()`. Branch and session are shared.

### [ ] Agent Trees and Transfer

```
root_agent (LlmAgent)
├── search_agent (LlmAgent + GoogleSearchTool)
└── write_agent (LlmAgent, no tools)
```

Agents compose via `sub_agents`. The LLM transfers control by calling `transfer_to_agent`.

The LLM in `root_agent` can say "transfer to search_agent", which triggers `EventActions.transfer_to_agent = 'search_agent'`.

### [ ] How Agent Transfer Works

```
User: "Book me a flight to Tokyo"
│
└── router_agent (AutoFlow)
    │
    ├── BEFORE LLM CALL: AutoFlow injects transfer_to_agent tool
    │   └── agent_transfer.py adds FunctionDeclaration + instructions
    │       listing available targets: [travel_agent, weather_agent]
    │
    ├── LLM calls: transfer_to_agent("travel_agent")
    │   └── sets EventActions.transfer_to_agent = "travel_agent"
    │
    ├── DISPATCH: base_llm_flow.py intercepts the flag
    │   ├── finds travel_agent via root_agent.find_agent("travel_agent")
    │   ├── calls travel_agent.run_async(invocation_context)
    │   │   └── _create_invocation_context: model_copy(update={'agent': travel_agent})
    │   │       only 'agent' changes — everything else is shared
    │   │
    │   └── travel_agent runs with its OWN tools, instruction, model
    │       ├── search_flights(destination="Tokyo") → [{flight: "JL001"}]
    │       └── "I found flight JL001 for $450..."
    │
    └── Events from travel_agent bubble back to caller
```

### [ ] What Gets Shared vs Isolated

```
SHARED (same object reference via model_copy):
├── session            ← same Session object
├── session.state      ← writes by agent A visible to agent B immediately
├── session.events     ← same event list
├── invocation_id      ← same invocation
├── branch             ← NOT changed by transfer (only ParallelAgent changes it)
├── session_service    ← same service
├── artifact_service   ← same service
└── run_config         ← same config

NOT SHARED (unique to each agent):
├── agent.tools        ← target uses its OWN tools, source's tools are gone
├── agent.instruction  ← target uses its OWN system prompt
├── agent.model        ← target uses its OWN model (or inherits via canonical_model)
├── agent.callbacks    ← target's before/after callbacks, not source's
└── agent.sub_agents   ← target's own children
```

### [ ] What the Target Agent Sees in History

```
contents.py builds the target agent's LLM prompt:
│
├── Events with branch=None (root-level) → VISIBLE to everyone
├── Events with matching branch → VISIBLE
├── Events from OTHER agents → re-presented as user-role text:
│   └── "[source_agent] called tool X with parameters: ..."
│       "[source_agent] X tool returned result: ..."
│       (thoughts are stripped, role flattened to 'user')
│
├── ALWAYS EXCLUDED (regardless of branch):
│   ├── auth events (adk_request_credential)
│   ├── confirmation events (adk_request_confirmation)
│   ├── framework events (adk_framework)
│   └── events with empty content or only thoughts
│
└── Key: transfer_to_agent does NOT change branch
    → target sees the SAME events as source (no additional filtering)
    → contrast with ParallelAgent which sets unique branches for isolation
```

### [ ] How Control Returns and Persists

```
WITHIN an invocation:
├── Target agent finishes (final text response)
│   └── Events bubble back up to source agent's flow
│       └── Source agent's loop also exits (last event is final)
│
├── Target can transfer BACK to source (recursive delegation)
│   └── transfer_to_agent("router_agent") works — same mechanism
│
└── Target can transfer to a PEER
    └── transfer_to_agent("weather_agent") — found via root_agent.find_agent()

ACROSS invocations (next user message):
├── Runner._find_agent_to_run() walks session.events backwards
│   └── finds last event's author agent
│       └── if that agent is transferable (disallow_transfer_to_parent=False up the tree)
│           → THAT agent handles the next message (control "sticks")
│
└── escalate is NOT transfer — it signals LoopAgent to break its loop
    └── tool_context.actions.escalate = True → consumed by LoopAgent only
```

### [ ] Branch in Events

`branch` tracks which agent produced each event. This lets each agent see only its own lineage:

```
Event stream with branches:

 evt-001  author="user"          branch=None
 evt-002  author="router_agent"  branch=None           ← transfer_to_agent call
 evt-003  author="travel_agent"  branch=None           ← same branch (transfer doesn't change it)
 evt-004  author="travel_agent"  branch=None           ← tool call
 evt-005  author="travel_agent"  branch=None           ← final answer

Note: branch stays None because transfer_to_agent does NOT set a new branch.
ParallelAgent is the only agent type that creates new branches for isolation.
```

---

## Examples

### [ ] Minimal Multi-Agent Example

```python
travel_agent = LlmAgent(name="travel_agent", model="gemini-2.5-flash",
    instruction="You book flights.", tools=[search_flights])

weather_agent = LlmAgent(name="weather_agent", model="gemini-2.5-flash",
    instruction="You report weather.", tools=[get_weather])

router = LlmAgent(name="router", model="gemini-2.5-flash",
    instruction="Route to the right specialist.",
    sub_agents=[travel_agent, weather_agent])
# AutoFlow is selected automatically because sub_agents is non-empty
```

The router LLM sees sub-agents as transfer targets (injected by AutoFlow) and calls `transfer_to_agent()` to route.

### [ ] 3-Layer Agent Tree with Transfer Back

```python
# Layer 3: leaf specialists
flight_search = LlmAgent(name="flight_search", model="gemini-2.5-flash",
    instruction="Search flights. When done, transfer back to travel_agent.",
    tools=[search_flights_api])

hotel_search = LlmAgent(name="hotel_search", model="gemini-2.5-flash",
    instruction="Search hotels. When done, transfer back to travel_agent.",
    tools=[search_hotels_api])

# Layer 2: domain agent (has sub-agents)
travel_agent = LlmAgent(name="travel_agent", model="gemini-2.5-flash",
    instruction="""You handle travel requests.
    - For flights, transfer to flight_search
    - For hotels, transfer to hotel_search
    - When fully done, transfer back to router""",
    sub_agents=[flight_search, hotel_search])

# Layer 1: root router
router = LlmAgent(name="router", model="gemini-2.5-flash",
    instruction="Route to travel_agent for travel, weather_agent for weather.",
    sub_agents=[travel_agent, weather_agent])
```

Transfer flow for "Book a flight and hotel in Tokyo":

```
User: "Book a flight and hotel in Tokyo"
│
├── router (Layer 1)
│   └── LLM calls transfer_to_agent("travel_agent")
│
├── travel_agent (Layer 2)
│   └── LLM calls transfer_to_agent("flight_search")
│
├── flight_search (Layer 3)
│   ├── search_flights_api("Tokyo") → [{flight: "JL001"}]
│   └── LLM calls transfer_to_agent("travel_agent")  ← BACK TO PARENT
│
├── travel_agent (Layer 2, resumed)
│   └── LLM calls transfer_to_agent("hotel_search")
│
├── hotel_search (Layer 3)
│   ├── search_hotels_api("Tokyo") → [{hotel: "Park Hyatt"}]
│   └── LLM calls transfer_to_agent("travel_agent")  ← BACK TO PARENT
│
├── travel_agent (Layer 2, resumed)
│   └── LLM calls transfer_to_agent("router")  ← BACK TO GRANDPARENT
│
└── router (Layer 1, resumed)
    └── "I've booked flight JL001 and Park Hyatt in Tokyo!"
```

**How transfer back works** — by default `disallow_transfer_to_parent=False`, so AutoFlow automatically includes the parent agent in the transfer target list. The LLM's system prompt says: *"If neither you nor the other agents are best for the question, transfer to your parent agent travel_agent."*

**What each agent can transfer to** (computed by `_get_transfer_targets`):

```
router can transfer to:
├── travel_agent     (sub_agent)
└── weather_agent    (sub_agent)
    (no parent — router is root)

travel_agent can transfer to:
├── flight_search    (sub_agent)
├── hotel_search     (sub_agent)
├── router           (parent, because disallow_transfer_to_parent=False)
└── weather_agent    (peer, because disallow_transfer_to_peers=False)

flight_search can transfer to:
├── travel_agent     (parent)
└── hotel_search     (peer)
    (no sub_agents)
```

**To PREVENT transfer back**, set `disallow_transfer_to_parent=True`:

```python
# This agent can only go deeper, never back up
one_way_agent = LlmAgent(name="one_way",
    disallow_transfer_to_parent=True,  # can't transfer to parent
    disallow_transfer_to_peers=True,   # can't transfer to siblings
    sub_agents=[...])

# WARNING: if this agent also has no sub_agents, it gets SingleFlow
# (no transfer at all) and the user may get "stuck" with this agent.
# ADK mitigates this: on the NEXT user turn, Runner automatically
# transfers control back to the parent if the current agent can't
# transfer anywhere.
```

---

## Gotchas

- Agent names must be valid Python identifiers and unique within the tree; `"user"` is reserved.
- `output_schema` and `tools` are mutually exclusive — when `output_schema` is set, the agent cannot use tools. Workaround: use `output_key` to capture text then parse, or use a 2-agent pipeline.
- `@final` on `run_async` means you must override `_run_async_impl`, never `run_async` itself.
- `model` defaults to `''` (empty string); resolution walks up the parent chain and falls back to `DEFAULT_MODEL` (`'gemini-2.5-flash'`) only if no ancestor sets a model.
- `include_contents='none'` makes the agent stateless — it receives no conversation history.

---

## Related

- [`agents/base_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/base_agent.py) — abstract base
- [`agents/llm_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/llm_agent.py) — primary implementation
- [`agents/invocation_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/invocation_context.py) — shared context
- [`agents/loop_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/loop_agent.py) — loop composition
- [`agents/parallel_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/parallel_agent.py) — parallel composition
- [`agents/sequential_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/sequential_agent.py) — sequential composition
- [`agents/callback_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/callback_context.py) — context passed to callbacks
- [14-planners.md](14-planners.md) — BuiltInPlanner and PlanReActPlanner deep dive
