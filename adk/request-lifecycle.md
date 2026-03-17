# Request-to-Response Lifecycle

A complete trace of one user message through ADK — from the API call to the final streamed event — using a concrete weather agent example.

**Sources referenced throughout:**
[`runners.py`](../adk-python/src/google/adk/runners.py) ·
[`agents/llm_agent.py`](../adk-python/src/google/adk/agents/llm_agent.py) ·
[`agents/base_agent.py`](../adk-python/src/google/adk/agents/base_agent.py) ·
[`agents/invocation_context.py`](../adk-python/src/google/adk/agents/invocation_context.py) ·
[`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) ·
[`flows/llm_flows/functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py) ·
[`models/base_llm.py`](../adk-python/src/google/adk/models/base_llm.py) ·
[`models/llm_request.py`](../adk-python/src/google/adk/models/llm_request.py) ·
[`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py) ·
[`events/event.py`](../adk-python/src/google/adk/events/event.py) ·
[`events/event_actions.py`](../adk-python/src/google/adk/events/event_actions.py) ·
[`sessions/session.py`](../adk-python/src/google/adk/sessions/session.py) ·
[`tools/base_tool.py`](../adk-python/src/google/adk/tools/base_tool.py)

---

## The Example Agent

```python
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

def get_weather(city: str) -> dict:
    """Returns the current weather for a city."""
    # (real impl would call a weather API)
    return {"city": city, "temp_c": 18, "condition": "Partly cloudy"}

weather_agent = LlmAgent(
    name="weather_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful weather assistant. Use the get_weather tool when asked about weather.",
    tools=[get_weather],
)

session_service = InMemorySessionService()
runner = Runner(
    agent=weather_agent,
    app_name="weather_app",
    session_service=session_service,
)

session = await session_service.create_session(
    app_name="weather_app", user_id="user_42"
)

# The call that starts the lifecycle:
async for event in runner.run_async(
    user_id="user_42",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text="What's the weather in Tokyo?")]),
):
    print(event)
```

User message: **"What's the weather in Tokyo?"**

---

## Full Lifecycle Diagram

```
CALLER (your code)
  │
  │  runner.run_async(user_id, session_id, new_message)
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  RUNNER  [runners.py]                                                │
│                                                                      │
│  1. session_service.get_session()         → Session                 │
│  2. Create user Event, append_event()                               │
│  3. Create InvocationContext                                         │
│  4. agent.run_async(ctx)  ──────────────────────────────────────┐   │
│                                                                  │   │
│  yield Event ◄──────────────────────────────────────────────────┘   │
│  append_event() for each                                             │
└──────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BASE AGENT  [base_agent.py]                                         │
│                                                                      │
│  run_async(parent_ctx)                                               │
│    → before_agent_callback (plugins + agent callbacks)               │
│    → _run_async_impl(ctx)  ──────────────────────────────────────┐  │
│    → after_agent_callback                                         │  │
│                                                                   │  │
└───────────────────────────────────────────────────────────────────┘  │
                         │  ◄─────────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LLM AGENT  [llm_agent.py]                                           │
│                                                                      │
│  _run_async_impl(ctx)                                                │
│    → self._llm_flow.run_async(ctx)  ─────────────────────────────┐  │
│    → __maybe_save_output_to_state(event)                          │  │
│                                                                   │  │
└───────────────────────────────────────────────────────────────────┘  │
                         │  ◄─────────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  AUTO FLOW / BASE LLM FLOW  [base_llm_flow.py]                       │
│                                                                      │
│  ┌─ LOOP ────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  STEP 1:                                                      │  │
│  │   preprocess  → build LlmRequest                             │  │
│  │   call LLM    → stream LlmResponse (function call)           │  │
│  │   postprocess → dispatch tool → yield Events                 │  │
│  │                                                               │  │
│  │  STEP 2:                                                      │  │
│  │   preprocess  → build LlmRequest (now includes tool result)  │  │
│  │   call LLM    → stream LlmResponse (final text)              │  │
│  │   postprocess → yield final Event                            │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  GEMINI LLM  [models/gemini_llm.py]                                  │
│  generate_content_async(LlmRequest) → AsyncIterator[LlmResponse]     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Trace with Payloads

### Step 0 — Session State Before the Request

The session exists from a prior `create_session()` call. It's currently empty:

```python
# [sessions/session.py] Session object in memory
Session(
    id="sess-abc123",
    app_name="weather_app",
    user_id="user_42",
    state={},           # no persistent state yet
    events=[],          # no history
    last_update_time=1741996800.0,
)
```

---

### Step 1 — Runner.run_async() Entry

**Source:** [`runners.py:Runner.run_async`](../adk-python/src/google/adk/runners.py)

Runner fetches the session, creates the user event, and sets up the `InvocationContext`.

```python
# runner.run_async(user_id="user_42", session_id="sess-abc123", new_message=...)
```

**User message `new_message`:**

```python
# types.Content (google.genai.types)
Content(
    role="user",
    parts=[Part(text="What's the weather in Tokyo?")]
)
```

**User Event created and persisted:**

```python
# [events/event.py] Event #1 — appended to session immediately
Event(
    id="evt-001",
    invocation_id="e-inv-9f2a",       # unique to this run_async() call
    author="user",
    branch=None,                        # root agent has no branch prefix
    timestamp=1741996801.234,
    partial=None,
    content=Content(
        role="user",
        parts=[Part(text="What's the weather in Tokyo?")]
    ),
    actions=EventActions(
        state_delta={},
        artifact_delta={},
    ),
)
```

**InvocationContext created:**

```python
# [agents/invocation_context.py] InvocationContext
InvocationContext(
    invocation_id="e-inv-9f2a",
    agent=weather_agent,              # the LlmAgent
    session=session,                  # Session with events=[Event #1]
    branch=None,
    user_content=Content(role="user", parts=[Part(text="What's the weather...")]),
    end_invocation=False,
    run_config=None,
    # injected services:
    session_service=InMemorySessionService(...),
    artifact_service=None,
    memory_service=None,
    plugin_manager=PluginManager(plugins=[]),
)
```

---

### Step 2 — BaseAgent.run_async() → Callbacks

**Source:** [`agents/base_agent.py:BaseAgent.run_async`](../adk-python/src/google/adk/agents/base_agent.py)

```
BaseAgent.run_async(parent_ctx)
  → _create_invocation_context(parent_ctx)  # copies ctx, sets agent=self
  → _handle_before_agent_callback(ctx)       # no callback set → None
  → _run_async_impl(ctx)                     # delegate to LlmAgent
  → _handle_after_agent_callback(ctx)        # no callback set → None
```

No callbacks are configured on this agent, so both return `None` — no short-circuiting.

---

### Step 3 — Flow: STEP 1 Preprocess — Building the LlmRequest

**Source:** [`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) · [`flows/llm_flows/instructions.py`](../adk-python/src/google/adk/flows/llm_flows/instructions.py) · [`flows/llm_flows/contents.py`](../adk-python/src/google/adk/flows/llm_flows/contents.py) · [`flows/llm_flows/functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py)

Each `BaseLlmRequestProcessor` mutates the `LlmRequest` in order:

**1. `instructions.py`** — injects the system prompt:
```python
# agent.instruction = "You are a helpful weather assistant..."
# No {variable} placeholders → no substitution needed
config.system_instruction = "You are a helpful weather assistant. Use the get_weather tool when asked about weather."
```

**2. `contents.py`** — injects conversation history (filtered by branch):
```python
# session.events filtered to current branch (None = root)
# Only Event #1 (the user message) exists so far
contents = [
    Content(role="user", parts=[Part(text="What's the weather in Tokyo?")])
]
```

**3. `functions.py`** — injects tool declarations:
```python
# get_weather Python function → FunctionTool → FunctionDeclaration
config.tools = [
    Tool(function_declarations=[
        FunctionDeclaration(
            name="get_weather",
            description="Returns the current weather for a city.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "city": Schema(type=Type.STRING, description="city")
                },
                required=["city"],
            ),
        )
    ])
]
tools_dict = {"get_weather": FunctionTool(func=get_weather)}
```

**Final `LlmRequest` sent to the model:**

```python
# [models/llm_request.py] LlmRequest — STEP 1
LlmRequest(
    model="gemini-2.5-flash",
    contents=[
        Content(
            role="user",
            parts=[Part(text="What's the weather in Tokyo?")]
        )
    ],
    config=GenerateContentConfig(
        system_instruction="You are a helpful weather assistant. Use the get_weather tool when asked about weather.",
        tools=[
            Tool(function_declarations=[
                FunctionDeclaration(
                    name="get_weather",
                    description="Returns the current weather for a city.",
                    parameters=Schema(
                        type="OBJECT",
                        properties={"city": Schema(type="STRING")},
                        required=["city"],
                    ),
                )
            ])
        ],
        temperature=None,   # not set → model default
    ),
    tools_dict={"get_weather": <FunctionTool>},
)
```

---

### Step 4 — Flow: STEP 1 LLM Call → Function Call Response

**Source:** [`models/gemini_llm.py`](../adk-python/src/google/adk/models/gemini_llm.py) · [`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py)

The LLM decides to call `get_weather`. It streams back:

```
Streaming chunks (partial=True):
  chunk 1: LlmResponse(partial=True,  content=Content(role="model", parts=[Part(function_call=FunctionCall(name="get_weather", args={"city": "Tokyo"}))]))

Final chunk (partial=False):
  chunk 2: LlmResponse(partial=False, content=Content(role="model", parts=[Part(function_call=FunctionCall(name="get_weather", args={"city": "Tokyo"}))]))
```

**Model response Event created (Event #2):**

```python
# [events/event.py] Event #2 — LLM function call
Event(
    id="evt-002",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    branch=None,
    timestamp=1741996801.891,
    partial=False,
    content=Content(
        role="model",
        parts=[
            Part(
                function_call=FunctionCall(
                    id="fc-001",            # unique function call ID
                    name="get_weather",
                    args={"city": "Tokyo"},
                )
            )
        ]
    ),
    actions=EventActions(state_delta={}, artifact_delta={}),
    long_running_tool_ids=None,             # get_weather is not long-running
)
```

This event is **yielded to Runner** → Runner calls `append_event()` → persisted to session.

> **`is_final_response()` = False** — because the event contains a function call.
> The caller receives this event but typically skips rendering it (it's an intermediate step).

---

### Step 5 — Flow: STEP 1 Postprocess — Tool Dispatch

**Source:** [`flows/llm_flows/functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py)

The `functions.py` response processor sees the function call and dispatches it:

```
1. Extract FunctionCall: name="get_weather", args={"city": "Tokyo"}, id="fc-001"
2. Look up tool: tools_dict["get_weather"] → FunctionTool(func=get_weather)
3. Run before_tool_callback → None (not configured)
4. tool.run_async(args={"city": "Tokyo"}, tool_context=ToolContext(...))
```

**Tool execution:**

```python
# Your function is called:
get_weather(city="Tokyo")
# Returns:
{"city": "Tokyo", "temp_c": 18, "condition": "Partly cloudy"}
```

**Tool result Event created (Event #3):**

```python
# [events/event.py] Event #3 — tool response
Event(
    id="evt-003",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    branch=None,
    timestamp=1741996802.045,
    partial=False,
    content=Content(
        role="user",                    # tool responses have role="user" per Gemini API
        parts=[
            Part(
                function_response=FunctionResponse(
                    id="fc-001",        # matches the function call ID
                    name="get_weather",
                    response={
                        "result": {"city": "Tokyo", "temp_c": 18, "condition": "Partly cloudy"}
                    },
                )
            )
        ]
    ),
    actions=EventActions(state_delta={}, artifact_delta={}),
)
```

This event is **yielded to Runner** → `append_event()` → persisted.

> **`is_final_response()` = False** — because the event contains a function response.

---

### Step 6 — Flow: STEP 2 Preprocess — Rebuilding the LlmRequest

**Source:** [`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py)

The flow loops. Now session has 3 events. A new `LlmRequest` is built with the full history:

```python
# [models/llm_request.py] LlmRequest — STEP 2
LlmRequest(
    model="gemini-2.5-flash",
    contents=[
        # Turn 1: user message
        Content(
            role="user",
            parts=[Part(text="What's the weather in Tokyo?")]
        ),
        # Turn 2: model requested a tool call
        Content(
            role="model",
            parts=[Part(function_call=FunctionCall(id="fc-001", name="get_weather", args={"city": "Tokyo"}))]
        ),
        # Turn 3: tool returned its result
        Content(
            role="user",
            parts=[Part(function_response=FunctionResponse(id="fc-001", name="get_weather", response={"result": {"city": "Tokyo", "temp_c": 18, "condition": "Partly cloudy"}}))]
        ),
    ],
    config=GenerateContentConfig(
        system_instruction="You are a helpful weather assistant...",
        tools=[Tool(function_declarations=[...])],   # same as before
    ),
    tools_dict={"get_weather": <FunctionTool>},
)
```

---

### Step 7 — Flow: STEP 2 LLM Call → Final Text Response

The LLM now has the tool result and generates the final answer. It streams back:

```
Streaming chunks (partial=True) — yielded immediately as they arrive:
  chunk 1: LlmResponse(partial=True,  content=Content(role="model", parts=[Part(text="The weather in Tokyo")]))
  chunk 2: LlmResponse(partial=True,  content=Content(role="model", parts=[Part(text=" is currently 18°C")]))
  chunk 3: LlmResponse(partial=True,  content=Content(role="model", parts=[Part(text=" with partly cloudy skies.")]))

Final chunk (partial=False):
  chunk 4: LlmResponse(partial=False, content=Content(role="model", parts=[Part(text="The weather in Tokyo is currently 18°C with partly cloudy skies.")]))
```

Each partial chunk is wrapped in an `Event` and **yielded to Runner in real time**.

**Partial streaming Events (Event #4a, #4b, #4c):**

```python
# Streaming events — yielded to caller but NOT appended to session (partial=True)
Event(
    id="evt-004a",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    partial=True,       # ← streaming chunk
    content=Content(role="model", parts=[Part(text="The weather in Tokyo")]),
    actions=EventActions(),
)
# ... more partial events ...
```

**Final response Event (Event #4 — the one that matters):**

```python
# [events/event.py] Event #4 — final agent response
Event(
    id="evt-004",
    invocation_id="e-inv-9f2a",
    author="weather_agent",
    branch=None,
    timestamp=1741996802.891,
    partial=False,          # ← complete, authoritative
    content=Content(
        role="model",
        parts=[Part(text="The weather in Tokyo is currently 18°C with partly cloudy skies.")]
    ),
    actions=EventActions(
        state_delta={},     # no output_key set on this agent
        artifact_delta={},
    ),
    usage_metadata=GenerateContentResponseUsageMetadata(
        prompt_token_count=87,
        candidates_token_count=18,
        total_token_count=105,
    ),
    finish_reason=FinishReason.STOP,
)
```

> **`is_final_response()` = True** — no function calls, no function responses, `partial=False`.

This event is **yielded to Runner** → `append_event()` → persisted. The flow loop exits.

---

### Step 8 — Session State After the Request

```python
# [sessions/session.py] Session — after invocation
Session(
    id="sess-abc123",
    app_name="weather_app",
    user_id="user_42",
    state={},           # unchanged (no state_delta was applied)
    last_update_time=1741996802.891,
    events=[
        Event(id="evt-001", author="user",          content="What's the weather in Tokyo?"),
        Event(id="evt-002", author="weather_agent", content=FunctionCall(get_weather, city=Tokyo)),
        Event(id="evt-003", author="weather_agent", content=FunctionResponse(get_weather, {temp_c:18,...})),
        Event(id="evt-004", author="weather_agent", content="The weather in Tokyo is currently 18°C..."),
    ],
)
```

---

## Event Stream Seen by the Caller

This is what your `async for event in runner.run_async(...)` receives:

```
┌───────────┬──────────────────┬───────────────────────────────────────────────┬──────────────────────┐
│  Event    │  author          │  content summary                              │  is_final_response() │
├───────────┼──────────────────┼───────────────────────────────────────────────┼──────────────────────┤
│  evt-002  │  weather_agent   │  FunctionCall(get_weather, city="Tokyo")      │  False               │
│  evt-003  │  weather_agent   │  FunctionResponse(get_weather, {temp_c:18})   │  False               │
│  evt-004a │  weather_agent   │  "The weather in Tokyo"  [partial]            │  False               │
│  evt-004b │  weather_agent   │  " is currently 18°C"   [partial]            │  False               │
│  evt-004c │  weather_agent   │  " with partly cloudy skies." [partial]      │  False               │
│  evt-004  │  weather_agent   │  "The weather in Tokyo is currently 18°C..."  │  True  ← render this │
└───────────┴──────────────────┴───────────────────────────────────────────────┴──────────────────────┘
```

> **Note:** `evt-001` (user message) is appended to the session but is **not** yielded back to the caller — it was created from `new_message` by the Runner itself.

**Typical caller pattern:**

```python
async for event in runner.run_async(...):
    if event.is_final_response() and event.content:
        print(event.content.parts[0].text)
    elif event.partial and event.content:
        print(event.content.parts[0].text, end="", flush=True)  # stream to UI
```

---

## Sequence Diagram

```
Caller          Runner          BaseAgent       LlmAgent        BaseLlmFlow      GeminiLLM       get_weather()
  │                │               │               │                │                │                │
  │─run_async()───►│               │               │                │                │                │
  │                │─get_session()─►               │                │                │                │
  │                │◄─Session──────                │                │                │                │
  │                │─append_event(user_msg)         │                │                │                │
  │                │─run_async(ctx)─►               │                │                │                │
  │                │                │─run_async()──►│                │                │                │
  │                │                │               │─_llm_flow─────►│                │                │
  │                │                │               │                │                │                │
  │                │                │               │                │── LlmRequest ─►│                │
  │                │                │               │                │  (step 1)      │                │
  │                │                │               │                │◄─FunctionCall──│                │
  │                │                │               │                │                │                │
  │◄─evt-002───────│◄──────────────────────────────────────────────Event(FuncCall)   │                │
  │                │─append_event() │               │                │                │                │
  │                │                │               │                │─run_async()───────────────────►│
  │                │                │               │                │◄─{temp:18,...}────────────────-│
  │◄─evt-003───────│◄──────────────────────────────────────────────Event(FuncResp)   │                │
  │                │─append_event() │               │                │                │                │
  │                │                │               │                │── LlmRequest ─►│                │
  │                │                │               │                │  (step 2)      │                │
  │◄─evt-004a──────│◄──────────────────────────────────────────────Event(partial)    │                │
  │◄─evt-004b──────│◄──────────────────────────────────────────────Event(partial)    │                │
  │◄─evt-004c──────│◄──────────────────────────────────────────────Event(partial)    │                │
  │◄─evt-004───────│◄──────────────────────────────────────────────Event(final)      │                │
  │                │─append_event() │               │                │                │                │
  │                │                │               │                │                │                │
```

---

## What Changes With More Tools / Agents

### If the LLM calls two tools in one response

The flow receives a single Event with two `FunctionCall` parts. The `functions.py` postprocessor runs both tools (potentially in parallel), then yields a single Event with two `FunctionResponse` parts. The loop continues with both results in the next LlmRequest.

### If `output_key="result"` is set on the agent

In Step 7, after the final event is yielded, `__maybe_save_output_to_state` runs:

```python
# In LlmAgent._run_async_impl:
event.actions.state_delta["result"] = "The weather in Tokyo is currently 18°C..."
# session_service.append_event applies state_delta → session.state["result"] is now set
```

### If a sub-agent is involved (AutoFlow)

After step 4 (LLM responds with a `transfer_to_agent` function call), `auto_flow.py` intercepts it, finds the target agent by name in the tree, and calls `sub_agent.run_async(ctx)`. The sub-agent runs its own full lifecycle (its own loop), yielding events with its own `author` name and a child `branch`.

### If `before_model_callback` is set

Between Step 3 (LlmRequest built) and Step 4 (LLM called), the callback fires:

```python
def my_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # Can inspect/mutate llm_request
    # Return an LlmResponse to skip the LLM entirely
    return None  # None = proceed normally
```

---

## Key Invariants

| Invariant | Where enforced |
|-----------|---------------|
| Every Event gets a unique UUID | [`event.py:model_post_init`](../adk-python/src/google/adk/events/event.py#L77) |
| `invocation_id` ties all events in one `run_async()` call | [`runners.py`](../adk-python/src/google/adk/runners.py) |
| `state_delta` is applied atomically on `append_event` | [`base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) |
| LLM is never called directly — always through a flow | [`llm_agent.py:_run_async_impl`](../adk-python/src/google/adk/agents/llm_agent.py#L458) |
| Tool results feed back into the next LlmRequest's `contents` | [`flows/llm_flows/contents.py`](../adk-python/src/google/adk/flows/llm_flows/contents.py) |
| `partial=True` events stream to caller but are not the source of truth | [`base_llm.py`](../adk-python/src/google/adk/models/base_llm.py#L67) |
| Only `is_final_response()=True` events should be stored/displayed | [`event.py:is_final_response`](../adk-python/src/google/adk/events/event.py#L83) |
