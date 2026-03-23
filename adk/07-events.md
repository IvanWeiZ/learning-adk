# 07 — Events: The Universal Currency

> **Official docs:** [Events](https://google.github.io/adk-docs/events/) | **Source:** [`events/event.py`](https://github.com/google/adk-python/blob/main/src/google/adk/events/event.py) · [`events/event_actions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/events/event_actions.py) | **Prereqs:** [04-agents.md](04-agents.md), [05-flows.md](05-flows.md)

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

## At a Glance

```
┌─────────────────────────────────────────────────────────┐
│                    Event Lifecycle                       │
│  User msg → Runner → LLM → Tool → LLM → Final response │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Session.events []                       │
│  Event(user) → Event(func_call) → Event(func_response)  │
│             → Event(final, is_final_response=True)       │
│                                                         │
│  All events flow through as an ordered list              │
└─────────────────────────────────────────────────────────┘
```

`Event` is the universal data type in ADK. Every action — a user message, an LLM reply, a tool call, a tool result, or an agent transfer — produces an `Event`. A `Session` is simply an ordered list of Events. Each Event carries identity metadata, a content payload (text, function calls, function responses), and an `EventActions` envelope for side-effects like state mutations, agent transfers, and artifact uploads.

## Class Hierarchy

```
pydantic.BaseModel
 ↑
 LlmResponse (models/llm_response.py — contains content: Optional[types.Content])
 ↑
 Event (events/event.py — adds author, invocation_id, actions, branch)
```

`Event` extends `LlmResponse`. The `content` field (`Optional[types.Content]`) carries text, function calls, function responses, blobs, or thoughts.

## Key API

### Event Fields

```python
class Event(LlmResponse):
    invocation_id: str = '' # which Runner.run_async() call produced this (default empty, set before appending)
    author: str # 'user' or the agent's name
    actions: EventActions # side-effects: state changes, transfers, auth, etc.
    branch: Optional[str] # 'agent_1.agent_2.agent_3' — routing for multi-agent trees
    id: str # auto-generated UUID
    timestamp: float # unix timestamp, auto-set

    # Inherited from LlmResponse / Content:
    content: Optional[types.Content] # the actual payload (text, function calls, etc.)
    partial: Optional[bool] # True for streaming chunks, False for final

    # Defined on Event directly (NOT on LlmResponse):
    long_running_tool_ids: Optional[set[str]] # set of function call IDs for long-running tools;
    # when present, is_final_response() returns True
    # so the runner pauses and yields control to the caller

    # Inherited from LlmResponse (often populated on the final event):
    model_version: Optional[str] # the model version used to generate the response
    error_code: Optional[str] # error code if the response is an error (code varies by model)
    error_message: Optional[str] # error message if the response is an error
    turn_complete: Optional[bool] # whether the model response is complete (streaming mode only)
    interrupted: Optional[bool] # LLM was interrupted (e.g., user interruption during bidi streaming)
    finish_reason: Optional[types.FinishReason] # why generation stopped (STOP, MAX_TOKENS, SAFETY, etc.)
    usage_metadata: Optional[types.GenerateContentResponseUsageMetadata] # token counts (prompt, candidates, total)
    grounding_metadata: Optional[types.GroundingMetadata] # search grounding metadata from Google Search
    custom_metadata: Optional[dict[str, Any]] # arbitrary metadata; Runner merges RunConfig.custom_metadata here
    input_transcription: Optional[types.Transcription] # audio transcription of user input
    output_transcription: Optional[types.Transcription] # audio transcription of model output
    avg_logprobs: Optional[float] # average log probability of the generated tokens
    logprobs_result: Optional[types.LogprobsResult] # detailed log probabilities for chosen and top tokens
    cache_metadata: Optional[CacheMetadata] # context cache metadata if caching was used
    citation_metadata: Optional[types.CitationMetadata] # citation metadata for the response
```

### EventActions — The Side-Effect Envelope

Side-effects stored on `event.actions`:

```python
class EventActions(BaseModel):
    state_delta: dict[str, object] # key-value updates to session state
    artifact_delta: dict[str, int] # filename → new version (file uploads)
    transfer_to_agent: Optional[str] # route control to this named agent
    escalate: Optional[bool] # signal parent agent to take over
    skip_summarization: Optional[bool] # don't summarize this tool response
    requested_auth_configs: dict[str, AuthConfig] # tool is asking for OAuth credentials
    compaction: Optional[EventCompaction] # summary of compacted old events
    end_of_agent: Optional[bool] # agent finished its current run
    agent_state: Optional[dict[str, Any]] # checkpoint for resumable invocations
    requested_tool_confirmations: dict[str, ToolConfirmation] # human-in-the-loop confirmation
    # requests, keyed by function call ID
    rewind_before_invocation_id: Optional[str] # signals session rewind to before this invocation ID
    render_ui_widgets: Optional[list[UiWidget]] # UI widgets for frontend rendering
```

`state_delta` is how agents write to persistent session state.

### Key Methods on Event

```python
event.is_final_response() -> bool

event.get_function_calls() -> list[FunctionCall]
# Extract tool invocations the LLM requested.

event.get_function_responses() -> list[FunctionResponse]
# Extract tool results (after tools have run).

event.has_trailing_code_execution_result() -> bool
```

`is_final_response()` returns `True` when the event is the last thing an agent yields for this turn. It also returns `True` when `long_running_tool_ids` is set (runner pauses for long-running tools) or when `skip_summarization` is set. Returns `False` if the event has function calls, function responses, `partial=True`, or trailing code execution results.

## How It Works

### What's Inside an Event

```
┌─────────────────────────────────────────────────────┐
│ Event                                               │
│                                                     │
│ ┌─ Identity ──────────────────────────────────────┐ │
│ │ id: "auto-generated UUID"                       │ │
│ │ invocation_id: "ties all events in one run"     │ │
│ │ author: "weather_agent"                         │ │
│ │ branch: None                                    │ │
│ │ timestamp: 1741996801.891                       │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Payload ───────────────────────────────────────┐ │
│ │ content: Content(role="model", parts=[...])     │ │
│ │ partial: False                                  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Side Effects (EventActions) ───────────────────┐ │
│ │ state_delta: {"result": "18°C in Tokyo"}        │ │
│ │ transfer_to_agent: None                         │ │
│ │ escalate: None                                  │ │
│ │ artifact_delta: {}                              │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Events in a Single Turn

A tool-calling agent produces 4 events for one user turn:

```
User sends: "What's the weather in Tokyo?"
│
├── evt-001 — Event(author="user", content=user_msg)
│   └── persisted to session (not yielded to caller)
│
├── evt-002 — Event(author="weather_agent", content=FunctionCall)
│   └── LLM decides to call get_weather tool (yielded)
│
├── evt-003 — Event(author="weather_agent", content=FunctionResponse)
│   └── tool executes, returns weather data (yielded)
│
└── evt-004 — Event(author="weather_agent", content=final_text)
    └── is_final_response()=True — render this to user (yielded)
```

- **evt-001**: Runner creates the user event and appends it to the session, but does not yield it.
- **evt-002**: LLM decides it needs to call the `get_weather` tool — event contains a `FunctionCall`.
- **evt-003**: Tool executes and returns a `FunctionResponse` with the weather data.
- **evt-004**: LLM synthesizes the final answer. `is_final_response()` returns `True`, signaling the caller to render this event.

### The Branch Field

Sibling agents don't see each other's history. `branch` encodes the root-to-current path:

```
root_agent.search_agent.summarizer_agent
```

The flow filters events by branch so each agent sees only its own lineage.

#### Branch Filtering: Which Agent Sees Which Events

```
Session events (all stored together):
├── evt-001  author="user"          branch=None
├── evt-002  author="router"        branch=None              ← transfer_to_agent("search_agent")
├── evt-003  author="search_agent"  branch="search_agent"    ← tool call
├── evt-004  author="search_agent"  branch="search_agent"    ← tool response
├── evt-005  author="search_agent"  branch="search_agent"    ← final answer
├── evt-006  author="router"        branch=None              ← transfer_to_agent("write_agent")
├── evt-007  author="write_agent"   branch="write_agent"     ← final answer
└── evt-008  author="router"        branch=None              ← final answer

What each agent sees when building LlmRequest.contents:

router (branch=None):
  ├── evt-001  (branch=None)     ← sees this
  ├── evt-002  (branch=None)     ← sees this
  ├── evt-003  (branch=search)   ← HIDDEN (different branch)
  ├── evt-004  (branch=search)   ← HIDDEN
  ├── evt-005  (branch=search)   ← HIDDEN
  ├── evt-006  (branch=None)     ← sees this
  ├── evt-007  (branch=write)    ← HIDDEN
  └── evt-008  (branch=None)     ← sees this

search_agent (branch="search_agent"):
  ├── evt-001  (branch=None)     ← sees this (ancestor branch)
  ├── evt-002  (branch=None)     ← sees this (ancestor branch)
  ├── evt-003  (branch=search)   ← sees this (own branch)
  ├── evt-004  (branch=search)   ← sees this (own branch)
  └── evt-005  (branch=search)   ← sees this (own branch)
  (never sees evt-006, 007, 008 — created after search_agent finished)

write_agent (branch="write_agent"):
  ├── evt-001  (branch=None)     ← sees this (ancestor branch)
  ├── evt-006  (branch=None)     ← sees this (ancestor branch)
  └── evt-007  (branch=write)    ← sees this (own branch)
  (never sees search_agent events — different sibling branch)
```

### How Events Become LLM Context

The `contents.py` preprocessor filters events before each LLM call (see [23-advanced-internals.md](23-advanced-internals.md) for the full pipeline):

```
For each event in session.events:
├── Empty content?        → SKIP
├── Wrong branch?         → SKIP
├── Framework event?      → SKIP (auth, confirmation, framework internal)
├── Thought-only parts?   → SKIP (unless planning mode is active)
├── Compaction event?     → INCLUDE as summary
├── Rewind event?         → Undo previous events
└── Normal content?       → INCLUDE

Modes (set on LlmAgent):
├── include_contents='default' → full filtered history
└── include_contents='none'    → current turn only (stateless agent)
```

See [23-advanced-internals.md](23-advanced-internals.md) for the full processor pipeline.

## Examples

```python
async for event in runner.run_async(
    user_id="user1",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text="What's the weather?")]),
):
    print(f"[{event.author}] partial={event.partial}")

    if event.actions and event.actions.state_delta:
        print(f"  state_delta: {event.actions.state_delta}")

    if event.get_function_calls():
        for fc in event.get_function_calls():
            print(f"  tool call: {fc.name}({fc.args})")

    if event.is_final_response():
        print(f"  FINAL: {event.content.parts[0].text}")
```

## Gotchas

- The user event is persisted but **not yielded** by the runner — you won't see it in the async generator output.
- `branch` filtering means sibling agents cannot see each other's events — only their own lineage from the root.

## Related

- [`events/event_actions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/events/event_actions.py) — `EventActions` definition
- [`models/llm_response.py`](https://github.com/google/adk-python/blob/main/src/google/adk/models/llm_response.py) — parent class
- [`sessions/session.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/session.py) — stores `list[Event]`
- [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) — streams events to caller
