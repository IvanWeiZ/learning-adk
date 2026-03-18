# Request-to-Response Lifecycle

A complete trace of one user message through ADK — from `run_async()` to the final streamed event.

---

## Mental Model

Five layers, each with a clear responsibility:

```
Runner       → session bookkeeping (load, persist every event)
BaseAgent    → before/after_agent_callback guards
LlmAgent     → delegates to the flow, saves output_key if set
BaseLlmFlow  → the reason-act loop: build request → call LLM → dispatch tools → repeat
SessionSvc   → atomic state commits on every append_event()
```

The flow **loops** until the LLM returns a response with no function calls. A single user turn typically runs the loop 2× for a tool-using agent: once to get the tool call, once to get the final answer.

---

## The Example

```python
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

def get_weather(city: str) -> dict:
    """Returns the current weather for a city."""
    return {"city": city, "temp_c": 18, "condition": "Partly cloudy"}

weather_agent = LlmAgent(
    name="weather_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful weather assistant. Use the get_weather tool when asked about weather.",
    tools=[get_weather],
)

session_service = InMemorySessionService()
runner = Runner(agent=weather_agent, app_name="weather_app", session_service=session_service)
session = await session_service.create_session(app_name="weather_app", user_id="user_42")

# The call that starts everything:
async for event in runner.run_async(
    user_id="user_42",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text="What's the weather in Tokyo?")]),
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

User message: **"What's the weather in Tokyo?"**

---

## Layer Diagram

The high-level structure — who calls whom, and where callbacks and session writes sit.

```
CALLER
  │  runner.run_async(user_id, session_id, new_message)
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RUNNER  [runners.py]                                               │
│                                                                     │
│  get_session()               ← SESSION READ                        │
│  [create_session()]          ← if missing + auto_create            │
│  append_event(user_msg)      ← SESSION WRITE                       │
│  [plugin.before_run()]       ← plugin early-exit opportunity       │
│  agent.run_async(ctx) ────────────────────────────────────────┐    │
│  yield Event / append_event() for each non-partial ◄──────────┘    │
│  [compaction plugin]         ← optional post-run                   │
└─────────────────────────────────────────────────────────────────────┘
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BASE AGENT  [base_agent.py]                                        │
│                                                                     │
│  before_agent_callback  → None: continue | Content: skip agent     │
│  _run_async_impl(ctx) ─────────────────────────────────────────┐   │
│  after_agent_callback   → None: done     | Content: extra event │   │
└──────────────────────────────────────────────────────────────────┘  │
  ▼  ◄─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  LLM AGENT  [llm_agent.py]                                          │
│                                                                     │
│  _llm_flow.run_async(ctx)                                           │
│  __maybe_save_output_to_state(event)   ← if output_key is set      │
└─────────────────────────────────────────────────────────────────────┘
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BASE LLM FLOW  [base_llm_flow.py]                                  │
│                                                                     │
│  ┌─ LOOP until no function calls ──────────────────────────────┐   │
│  │                                                              │   │
│  │  preprocess → build LlmRequest  (SESSION READ: history)     │   │
│  │                                                              │   │
│  │  before_model_callback  → None: call LLM | LlmResponse: skip│   │
│  │  LLM call               ← on error: on_model_error_callback │   │
│  │  after_model_callback   → None: use it  | LlmResponse: swap │   │
│  │                                                              │   │
│  │  postprocess → yield Events                                  │   │
│  │                                                              │   │
│  │  if function call:                                           │   │
│  │    before_tool_callback → None: run    | dict: skip tool     │   │
│  │    tool.run_async()     ← on error: on_tool_error_callback  │   │
│  │    after_tool_callback  → None: keep  | dict: replace result │   │
│  │    yield tool result Event                                   │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GEMINI LLM  [models/gemini_llm.py]                                 │
│  generate_content_async(LlmRequest) → AsyncIterator[LlmResponse]    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What the Caller Receives

`runner.run_async()` is an async generator. For the Tokyo weather query, it yields these events:

```
┌───────────┬──────────────────┬─────────────────────────────────────────────┬──────────────────────┐
│  Event    │  author          │  content summary                            │  is_final_response() │
├───────────┼──────────────────┼─────────────────────────────────────────────┼──────────────────────┤
│  evt-002  │  weather_agent   │  FunctionCall(get_weather, city="Tokyo")    │  False               │
│  evt-003  │  weather_agent   │  FunctionResponse(get_weather, {temp_c:18}) │  False               │
│  evt-004a │  weather_agent   │  "The weather in Tokyo"  [partial]          │  False               │
│  evt-004b │  weather_agent   │  " is currently 18°C"   [partial]          │  False               │
│  evt-004c │  weather_agent   │  " with partly cloudy skies." [partial]    │  False               │
│  evt-004  │  weather_agent   │  "The weather in Tokyo is currently 18°C…"  │  True  ← render this │
└───────────┴──────────────────┴─────────────────────────────────────────────┴──────────────────────┘
```

> `evt-001` (the user message) is appended to the session but never yielded — the Runner created it internally.

**Typical handling pattern:**

```python
async for event in runner.run_async(...):
    if event.is_final_response() and event.content:
        print(event.content.parts[0].text)
    elif event.partial and event.content:
        print(event.content.parts[0].text, end="", flush=True)  # stream to UI
```

---

## Step-by-Step Trace

### [ ] Step 0 — Session State Before the Request

```python
# Session loaded by get_session() — empty for a brand-new conversation
Session(
    id="sess-abc123",
    app_name="weather_app",
    user_id="user_42",
    state={},    # no persistent state yet
    events=[],   # no history
)
```

---

### [ ] Step 1 — Runner Entry

**Source:** [`runners.py`](../adk-python/src/google/adk/runners.py)

Runner fetches the session, wraps the user message in an Event, persists it, then builds the `InvocationContext` that flows through every subsequent call.

**User Event (evt-001) — created and persisted before the agent runs:**

```python
Event(
    id="evt-001",
    invocation_id="e-inv-9f2a",   # ties every event in this run_async() call together
    author="user",
    timestamp=1741996801.234,
    content=Content(
        role="user",
        parts=[Part(text="What's the weather in Tokyo?")]
    ),
    actions=EventActions(state_delta={}, artifact_delta={}),
)
```

**InvocationContext — passed to every layer:**

```python
InvocationContext(
    invocation_id="e-inv-9f2a",
    agent=weather_agent,
    session=session,              # now has events=[evt-001]
    branch=None,
    user_content=Content(...),    # the original user message
    end_invocation=False,
    session_service=InMemorySessionService(...),
    plugin_manager=PluginManager(plugins=[]),
)
```

---

### [ ] Step 2 — Agent Callbacks (before_agent_callback)

**Source:** [`agents/base_agent.py`](../adk-python/src/google/adk/agents/base_agent.py)

```
BaseAgent.run_async(ctx)
  → _create_invocation_context()       # clone ctx, bind agent=self
  → _handle_before_agent_callback()    # plugins first, then agent list
  → _run_async_impl()                  # → LlmAgent
  → _handle_after_agent_callback()
```

No callbacks configured on this agent → both return `None`, no short-circuit.

The `CallbackContext` passed into every callback:

```python
CallbackContext(
    invocation_id: str,
    agent_name: str,
    user_content: Optional[types.Content],  # original user message (read-only)
    state: State,                            # mutable — writes queue a state_delta
    session: Session,                        # read-only view of session
    # user_id is NOT a direct property — access via: callback_context.session.user_id
    actions: EventActions,                  # accumulated side-effects
)
```

---

### [ ] Step 3 — Build LlmRequest (Preprocess)

**Source:** [`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py)

Three processors run in order, each mutating `LlmRequest`:

1. **`instructions.py`** — injects the system prompt (substitutes `{vars}` if any)
2. **`contents.py`** — reads `session.events` filtered to the current branch → builds `contents` list
3. **`functions.py`** — converts Python tools to `FunctionDeclaration` schemas

**LlmRequest sent to the model:**

```python
LlmRequest(
    model="gemini-2.5-flash",
    contents=[
        Content(role="user", parts=[Part(text="What's the weather in Tokyo?")])
    ],
    config=GenerateContentConfig(
        system_instruction="You are a helpful weather assistant…",
        tools=[Tool(function_declarations=[
            FunctionDeclaration(
                name="get_weather",
                description="Returns the current weather for a city.",
                parameters=Schema(type="OBJECT", properties={"city": Schema(type="STRING")}, required=["city"]),
            )
        ])],
    ),
    tools_dict={"get_weather": FunctionTool(func=get_weather)},
)
```

> **`before_model_callback` fires here** — after this request is built, before the API call. Return `None` to proceed; return an `LlmResponse` to skip the LLM entirely.

---

### [ ] Step 4 — LLM Call → Function Call Response

**Source:** [`models/gemini_llm.py`](../adk-python/src/google/adk/models/gemini_llm.py)

The LLM decides to call `get_weather`. It streams back a single function call chunk, then the final:

```
chunk 1 (partial=True):  FunctionCall(name="get_weather", args={"city": "Tokyo"})
chunk 2 (partial=False): FunctionCall(name="get_weather", args={"city": "Tokyo"})
```

> If the call raises, **`on_model_error_callback`** fires. Return `None` to re-raise; return an `LlmResponse` to suppress.
> After success, **`after_model_callback`** fires. Return `None` to use the real response; return an `LlmResponse` to replace it.

**Event #2 — yielded to Runner → persisted:**

```python
Event(
    id="evt-002",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    timestamp=1741996801.891,
    content=Content(
        role="model",
        parts=[Part(function_call=FunctionCall(id="fc-001", name="get_weather", args={"city": "Tokyo"}))]
    ),
    actions=EventActions(state_delta={}, artifact_delta={}),
    long_running_tool_ids=None,
)
# is_final_response() = False — contains a function call
```

---

### [ ] Step 5 — Tool Dispatch

**Source:** [`flows/llm_flows/functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py)

```
1. Extract FunctionCall: name="get_weather", args={"city": "Tokyo"}, id="fc-001"
2. Look up: tools_dict["get_weather"] → FunctionTool(func=get_weather)
3. before_tool_callback → None → proceed
4. tool.run_async({"city": "Tokyo"}, tool_context)
   on error → on_tool_error_callback
5. after_tool_callback → None → keep original result
```

`ToolContext` is the same as `CallbackContext` plus:
- `function_call_id: str` — ID of the in-flight call (`"fc-001"`)
- `tool_confirmation: ToolConfirmation | None` — populated if confirmation was requested

**Tool result:**

```python
get_weather(city="Tokyo")  # → {"city": "Tokyo", "temp_c": 18, "condition": "Partly cloudy"}
```

**Event #3 — yielded to Runner → persisted:**

```python
Event(
    id="evt-003",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    timestamp=1741996802.045,
    content=Content(
        role="user",   # ← tool responses use role="user" per Gemini API convention
        parts=[Part(function_response=FunctionResponse(
            id="fc-001",
            name="get_weather",
            response={"result": {"city": "Tokyo", "temp_c": 18, "condition": "Partly cloudy"}},
        ))]
    ),
    actions=EventActions(state_delta={}, artifact_delta={}),
)
# is_final_response() = False — contains a function response
```

---

### [ ] Step 6 — Rebuild LlmRequest (Loop Iteration 2)

The flow loops. Session now has 3 events. A new `LlmRequest` includes the full history:

```python
LlmRequest(
    model="gemini-2.5-flash",
    contents=[
        # Turn 1: user question
        Content(role="user",  parts=[Part(text="What's the weather in Tokyo?")]),
        # Turn 2: model's tool call
        Content(role="model", parts=[Part(function_call=FunctionCall(id="fc-001", name="get_weather", args={"city": "Tokyo"}))]),
        # Turn 3: tool result
        Content(role="user",  parts=[Part(function_response=FunctionResponse(id="fc-001", name="get_weather",
            response={"result": {"city": "Tokyo", "temp_c": 18, "condition": "Partly cloudy"}}))]),
    ],
    config=GenerateContentConfig(system_instruction="…", tools=[…]),  # same as before
)
```

> `before_model_callback` fires again before this second LLM call.

---

### [ ] Step 7 — Final LLM Response (Streaming)

The LLM has the tool result and streams the answer token by token:

```
partial chunk 1: "The weather in Tokyo"
partial chunk 2: " is currently 18°C"
partial chunk 3: " with partly cloudy skies."
final chunk:     "The weather in Tokyo is currently 18°C with partly cloudy skies."
```

Partial events are yielded to the caller **but not passed to `append_event()`** — they are free (no session I/O).

> `after_model_callback` fires after the final (non-partial) chunk arrives.

**Event #4 — the final authoritative event, yielded and persisted:**

```python
Event(
    id="evt-004",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    timestamp=1741996802.891,
    partial=False,
    content=Content(
        role="model",
        parts=[Part(text="The weather in Tokyo is currently 18°C with partly cloudy skies.")]
    ),
    actions=EventActions(state_delta={}),   # empty — no output_key on this agent
    usage_metadata=GenerateContentResponseUsageMetadata(
        prompt_token_count=87, candidates_token_count=18, total_token_count=105
    ),
    finish_reason=FinishReason.STOP,
)
# is_final_response() = True — text only, partial=False → flow loop exits
```

---

### [ ] Step 8 — Session After the Request

```python
Session(
    id="sess-abc123",
    state={},   # unchanged — no state_delta was applied in this turn
    events=[
        Event(id="evt-001", author="user",          content="What's the weather in Tokyo?"),
        Event(id="evt-002", author="weather_agent", content=FunctionCall(get_weather, city=Tokyo)),
        Event(id="evt-003", author="weather_agent", content=FunctionResponse(get_weather, {temp_c:18,…})),
        Event(id="evt-004", author="weather_agent", content="The weather in Tokyo is currently 18°C…"),
    ],
)
```

---

## Full Sequence Diagram

All callbacks and session writes shown in order. A callback returning non-None short-circuits the step it guards.

```
Caller       Runner          BaseAgent      BaseLlmFlow     GeminiLLM    get_weather()
  │             │                │               │               │              │
  │─run_async()►│                │               │               │              │
  │             │─get_session()──────────────────────────────────────── SESSION READ
  │             │◄─Session───────│               │               │              │
  │             │─append_event(user_msg)──────────────────────────────── SESSION WRITE
  │             │─agent.run_async(ctx)──►         │               │              │
  │             │                │               │               │              │
  │             │         ┌── before_agent_callback ──────────────────────────────────
  │             │         │  plugins → agent list │ stop at first non-None       │
  │             │         │  None → continue      │ Content → yield+skip agent   │
  │             │         └───────────────────────────────────────────────────────────
  │             │                │               │               │              │
  │             │                │─_llm_flow────►│               │              │
  │             │                │               │               │              │
  │             │                │    ┌─ LOOP ───┤               │              │
  │             │                │    │ preprocess│               │              │
  │             │                │    │  reads session.events ─────────── SESSION READ
  │             │                │    │           │               │              │
  │             │                │    ├── before_model_callback ───────────────────────
  │             │                │    │  None → call LLM │ LlmResponse → skip LLM│
  │             │                │    ├───────────────────────────────────────────────
  │             │                │    │           │── LlmRequest─►│              │
  │             │                │    │           │  (loop 1)     │              │
  │             │                │    │           │◄─FunctionCall─│              │
  │             │                │    ├── on_model_error_callback (only on error) ───
  │             │                │    │  None → re-raise │ LlmResponse → suppress │
  │             │                │    ├───────────────────────────────────────────────
  │             │                │    ├── after_model_callback ────────────────────────
  │             │                │    │  None → use response │ LlmResponse → swap │
  │             │                │    ├───────────────────────────────────────────────
  │◄─evt-002────│◄───────────────────────── Event(FuncCall)       │              │
  │             │─append_event()──────────────────────────────────────── SESSION WRITE
  │             │                │    │           │               │              │
  │             │                │    ├── before_tool_callback ────────────────────────
  │             │                │    │  None → run tool │ dict → skip tool      │
  │             │                │    ├───────────────────────────────────────────────
  │             │                │    │           │──────────────────────────────►│
  │             │                │    ├── on_tool_error_callback (only on error) ────
  │             │                │    │  None → re-raise │ dict → suppress error │
  │             │                │    ├───────────────────────────────────────────────
  │             │                │    │           │◄─────────────────────────────-│
  │             │                │    ├── after_tool_callback ─────────────────────────
  │             │                │    │  None → keep result │ dict → replace result│
  │             │                │    ├───────────────────────────────────────────────
  │◄─evt-003────│◄───────────────────────── Event(FuncResp)       │              │
  │             │─append_event()──────────────────────────────────────── SESSION WRITE
  │             │                │    │           │               │              │
  │             │                │    │ preprocess│               │              │
  │             │                │    │  (now has fc+fr in history) ────── SESSION READ
  │             │                │    ├── before_model_callback (loop 2) ─────────────
  │             │                │    │           │── LlmRequest─►│              │
  │             │                │    │           │  (loop 2)     │              │
  │             │                │    ├── after_model_callback ────────────────────────
  │◄─evt-004a───│◄───────────────────────── Event(partial)        │              │
  │◄─evt-004b───│◄───────────────────────── Event(partial)        │              │
  │◄─evt-004c───│◄───────────────────────── Event(partial)        │              │
  │◄─evt-004────│◄───────────────────────── Event(final)          │              │
  │             │─append_event()──────────────────────────────────────── SESSION WRITE
  │             │                │    └───────────┤               │              │
  │             │                │               │               │              │
  │             │         ┌── after_agent_callback ──────────────────────────────────
  │             │         │  None → done │ Content → yield extra event          │
  │             │         └───────────────────────────────────────────────────────────
```

---

## Reference: Callbacks

All callbacks follow the same execution pattern: **plugins run first** (stop at first non-None), then the agent's own list (stop at first non-None). Each can be a single function or a `list`.

### [ ] Signatures and Return Effects

```python
# ── AGENT ────────────────────────────────────────────────────────────────────

# Before _run_async_impl(). Non-None → skip agent entirely.
def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]: ...

# After _run_async_impl(). Non-None → yield one more Event with that content.
def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]: ...


# ── MODEL ────────────────────────────────────────────────────────────────────

# After LlmRequest built, before LLM call. Non-None → skip the LLM.
# llm_request may be mutated in place.
def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]: ...

# After LLM returns. Non-None → replace the response.
def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]: ...

# When LLM call raises. Non-None → suppress error, use this response.
def on_model_error_callback(callback_context: CallbackContext, llm_request: LlmRequest, error: Exception) -> Optional[LlmResponse]: ...


# ── TOOL ─────────────────────────────────────────────────────────────────────

# Before tool.run_async(). Non-None → skip tool, use dict as result.
# args may be mutated in place.
def before_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> Optional[dict]: ...

# After tool succeeds. Non-None → replace the result.
def after_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: dict) -> Optional[dict]: ...

# When tool raises. Non-None → suppress error, use dict as result.
def on_tool_error_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, error: Exception) -> Optional[dict]: ...
```

### [ ] Quick Reference

| Callback | None | Non-None |
|---|---|---|
| `before_agent_callback` | proceed | yield Event with content, skip agent (`end_invocation=True`) |
| `after_agent_callback` | nothing | yield extra Event with content |
| `before_model_callback` | call LLM | skip LLM, use returned `LlmResponse` |
| `after_model_callback` | use actual response | replace with returned `LlmResponse` |
| `on_model_error_callback` | re-raise | suppress, use returned `LlmResponse` |
| `before_tool_callback` | execute tool | skip tool, use returned `dict` |
| `after_tool_callback` | use actual result | replace with returned `dict` |
| `on_tool_error_callback` | re-raise | suppress, use returned `dict` |

### [ ] Plugin-Only Callbacks

Plugins intercept all eight above plus four more:

| Plugin Callback | When |
|---|---|
| `on_user_message_callback` | User message received by Runner |
| `before_run_callback` | Before agent loop starts |
| `after_run_callback` | After agent loop ends |
| `on_event_callback` | On every yielded event |

---

## Reference: Session Service

**Source:** [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py)

### [ ] Session Calls Per Invocation

```
run_async()
  1. get_session()              ← load session.events + session.state
  2. [create_session()]         ← only if missing AND auto_create=True
  3. append_event(user_msg)     ← persist user message before agent starts
  ┌─ agent loop ─────────────────────────────────────────────────────┐
  │  4+. append_event(event)   ← for EVERY non-partial yielded event │
  └──────────────────────────────────────────────────────────────────┘
  5. [append_event(plugin)]     ← if before_run_callback short-circuits
  6. [append_event(rewind)]     ← if rewind_async() is called
  7. [compaction]               ← optional App plugin post-invocation
```

Calls 4+ are the hot path. A tool-call turn generates 3–4+ `append_event` calls minimum.

### [ ] What `append_event()` Does

```python
async def append_event(session: Session, event: Event) -> Event:
    if event.partial:
        return event                           # 1. Partial events are free — never persisted

    for key, value in event.actions.state_delta.items():
        if key.startswith("temp:"):
            session.state[key] = value         # 2. Write temp: keys to in-memory state immediately
                                               #    so later agents in this invocation can read them

    # 3. Strip temp: keys from the delta before writing to storage
    event.actions.state_delta = {
        k: v for k, v in event.actions.state_delta.items()
        if not k.startswith("temp:")
    }

    session.state.update(event.actions.state_delta)  # 4. Commit remaining state
    session.events.append(event)                      # 5. Add to in-memory history
    # subclass writes to its storage backend           # 6. Database / file / etc.
    return event
```

### [ ] State Key Scopes

| Prefix | Scope | Persisted? | Notes |
|---|---|---|---|
| _(none)_ | This session | Yes | |
| `app:` | All users of this app | Yes | Shared across users |
| `user:` | This user, all sessions | Yes | Shared across sessions |
| `temp:` | This invocation only | **No** | Stripped before storage |

```python
# From any callback or tool:
ctx.state["session_key"] = "survives the session"
ctx.state["temp:scratch"] = "gone after this invocation"
ctx.state["user:prefs"] = {"theme": "dark"}     # across all sessions for this user
ctx.state["app:config"] = {"max_results": 10}   # all users of the app
```

### [ ] Backend Comparison

| | `InMemorySessionService` | `DatabaseSessionService` |
|---|---|---|
| Storage | Python dicts | SQLAlchemy (SQLite / MySQL / PostgreSQL) |
| Persistence | Lost on restart | Durable |
| `append_event` cost | ~microseconds | ~milliseconds |
| `get_session` cost | `deepcopy()` of session | DB query |
| Concurrency | No locking | asyncio locks + DB row-level locks |

**Recommended default:** `InMemorySessionService` + `GetSessionConfig(num_recent_events=20)` — sub-millisecond writes, bounded memory.

---

## Variations

### [ ] LLM calls two tools in one response

`functions.py` receives a single Event with two `FunctionCall` parts, runs both tools (potentially in parallel), then yields a single Event with two `FunctionResponse` parts. The loop continues with both results in the next `LlmRequest`.

### [ ] `output_key="result"` set on the agent

After the final Event is yielded, `__maybe_save_output_to_state` runs:

```python
# LlmAgent._run_async_impl — final event's state_delta is written
event.actions.state_delta["result"] = "The weather in Tokyo is currently 18°C…"
# → applied by append_event() → session.state["result"] is now set
```

### [ ] Sub-agent transfer (AutoFlow)

The LLM returns a `transfer_to_agent` function call. `auto_flow.py` intercepts it, finds the target agent in the tree, and calls `sub_agent.run_async(ctx)`. The sub-agent runs its own full lifecycle (its own loop), emitting events with its own `author` and a child `branch`.

---

## Key Invariants

| Invariant | Source |
|---|---|
| Every Event gets a unique UUID | [`event.py:model_post_init`](../adk-python/src/google/adk/events/event.py#L77) |
| `invocation_id` ties all events in one `run_async()` call | [`runners.py`](../adk-python/src/google/adk/runners.py) |
| `partial=True` events are never passed to `append_event` | [`base_session_service.py:L105`](../adk-python/src/google/adk/sessions/base_session_service.py#L105) |
| `state_delta` is applied atomically on `append_event` | [`base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) |
| `temp:` keys are in-memory only — stripped from persisted delta | [`base_session_service.py:_apply_temp_state`](../adk-python/src/google/adk/sessions/base_session_service.py#L118) |
| LLM is never called directly — always through a flow | [`llm_agent.py:_run_async_impl`](../adk-python/src/google/adk/agents/llm_agent.py#L458) |
| Tool results feed into the next `LlmRequest.contents` | [`flows/llm_flows/contents.py`](../adk-python/src/google/adk/flows/llm_flows/contents.py) |
| Only `is_final_response()=True` events should be rendered | [`event.py:is_final_response`](../adk-python/src/google/adk/events/event.py#L83) |
| Callbacks: plugins first, agent list second; first non-None wins | [`base_agent.py:L434`](../adk-python/src/google/adk/agents/base_agent.py#L434) |

---

## Sources

[`runners.py`](../adk-python/src/google/adk/runners.py) ·
[`agents/base_agent.py`](../adk-python/src/google/adk/agents/base_agent.py) ·
[`agents/llm_agent.py`](../adk-python/src/google/adk/agents/llm_agent.py) ·
[`agents/invocation_context.py`](../adk-python/src/google/adk/agents/invocation_context.py) ·
[`agents/context.py`](../adk-python/src/google/adk/agents/context.py) ·
[`agents/callback_context.py`](../adk-python/src/google/adk/agents/callback_context.py) ·
[`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) ·
[`flows/llm_flows/functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py) ·
[`models/base_llm.py`](../adk-python/src/google/adk/models/base_llm.py) ·
[`models/llm_request.py`](../adk-python/src/google/adk/models/llm_request.py) ·
[`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py) ·
[`events/event.py`](../adk-python/src/google/adk/events/event.py) ·
[`events/event_actions.py`](../adk-python/src/google/adk/events/event_actions.py) ·
[`sessions/session.py`](../adk-python/src/google/adk/sessions/session.py) ·
[`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) ·
[`sessions/state.py`](../adk-python/src/google/adk/sessions/state.py) ·
[`tools/base_tool.py`](../adk-python/src/google/adk/tools/base_tool.py) ·
[`plugins/plugin_manager.py`](../adk-python/src/google/adk/plugins/plugin_manager.py)
