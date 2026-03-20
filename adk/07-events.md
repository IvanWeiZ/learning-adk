# 07 — Events: The Universal Currency

> **Official docs:** [Events](https://google.github.io/adk-docs/events/) | **Source:** [`events/event.py`](https://github.com/google/adk-python/blob/main/src/google/adk/events/event.py), [`events/event_actions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/events/event_actions.py) | **Prereqs:** 04, 05

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

`Event` extends `LlmResponse` (contains `content: Optional[types.Content]`). Carries text, function calls, function responses, blobs, or thoughts.

## Key API

### [ ] Event Fields

```python
class Event(LlmResponse):
    invocation_id: str # which Runner.run_async() call produced this
    author: str # 'user' or the agent's name
    actions: EventActions # side-effects: state changes, transfers, auth, etc.
    branch: Optional[str] # 'agent_1.agent_2.agent_3' — routing for multi-agent trees
    id: str # auto-generated UUID
    timestamp: float # unix timestamp, auto-set

    # Inherited from LlmResponse / Content:
    content: Optional[types.Content] # the actual payload (text, function calls, etc.)
    partial: Optional[bool] # True for streaming chunks, False for final

    # Inherited from LlmResponse (often populated on the final event):
    long_running_tool_ids: Optional[set[str]] # set of function call IDs for long-running tools;
    # when present, is_final_response() returns True
    # so the runner pauses and yields control to the caller
    finish_reason: Optional[types.FinishReason] # why generation stopped (STOP, MAX_TOKENS, SAFETY, etc.)
    usage_metadata: Optional[types.GenerateContentResponseUsageMetadata] # token counts (prompt, candidates, total)
    grounding_metadata: Optional[types.GroundingMetadata] # search grounding metadata from Google Search
    custom_metadata: Optional[dict[str, Any]] # arbitrary metadata; Runner merges RunConfig.custom_metadata here
```

### [ ] EventActions — The Side-Effect Envelope

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
    agent_state: Optional[dict] # checkpoint for resumable invocations
    requested_tool_confirmations: dict[str, ToolConfirmation] # human-in-the-loop confirmation
    # requests, keyed by function call ID
    rewind_before_invocation_id: Optional[str] # signals session rewind to before this invocation ID
    render_ui_widgets: Optional[list[UiWidget]] # UI widgets for frontend rendering
```

`state_delta` is how agents write to persistent session state.

### [ ] Key Methods on Event

```python
event.is_final_response() -> bool
# True when the event is the last thing an agent yields for this turn.
# Also returns True when long_running_tool_ids is set (runner pauses for
# long-running tools) or when skip_summarization is set on the event actions.
# False if: event has function calls, function responses, partial=True,
# or has trailing code execution results.

event.get_function_calls() -> list[FunctionCall]
# Extract tool invocations the LLM requested.

event.get_function_responses() -> list[FunctionResponse]
# Extract tool results (after tools have run).

event.has_trailing_code_execution_result() -> bool
# True if the last part of content is a code execution result.
```

## How It Works

### [ ] What's Inside an Event

```
┌─────────────────────────────────────────────────────┐
│ Event                                               │
│                                                     │
│ ┌─ Identity ──────────────────────────────────────┐ │
│ │ id: "evt-002"                                   │ │
│ │ invocation_id: "e-inv-9f2a"                     │ │
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

`Event` is the universal data type. Every action produces one:

- A user sends a message → Event
- The LLM replies with text → Event
- The LLM calls a tool → Event
- The tool returns a result → Event
- An agent transfers control to a sub-agent → Event

A `Session` is an ordered list of Events.

### [ ] Events in a Single Turn

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

### [ ] The Branch Field

Sibling agents don't see each other's history. `branch` encodes the root-to-current path:

```
root_agent.search_agent.summarizer_agent
```

The flow filters events by branch so each agent sees only its own lineage.

#### [ ] Branch Filtering: Which Agent Sees Which Events

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

### [ ] How Events Flow End-to-End

```
Runner.run_async(user_id, session_id, new_message)
│
├── 1. User sends message
│   └── Runner creates Event(author='user', content=user_message)
│       └── appended to Session.events
│
├── 2. LLM responds with text
│   └── Flow creates Event(author=agent.name, content=llm_text)
│       └── appended to Session.events
│
├── 3. LLM calls a tool
│   └── Flow creates Event(author=agent.name, content=[FunctionCall(...)])
│       └── tool executes
│
├── 4. Tool returns result
│   └── Flow creates Event(author=agent.name, content=[FunctionResponse(...)])
│       └── appended to Session.events
│
└── 5. All events stream back to caller via Runner.run_async()
```

## Examples

A tool-calling agent produces 4 events for one user turn (see "Events in a Single Turn" diagram above). The key pattern:

1. Runner creates the user event and appends it to the session (not yielded)
2. LLM decides to call a tool — event contains a `FunctionCall` (yielded)
3. Tool executes and returns a `FunctionResponse` (yielded)
4. LLM synthesizes the final answer — `is_final_response()` returns `True` (yielded, rendered to user)

## Gotchas

- `is_final_response()` also returns `True` when `long_running_tool_ids` is set (runner pauses for long-running tools) or when `skip_summarization` is set — not just on the final text response.
- The user event (evt-001) is persisted but **not yielded** by the runner — you won't see it in the async generator output.
- `branch` filtering means sibling agents cannot see each other's events — only their own lineage from the root.

## Related

- [`events/event_actions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/events/event_actions.py) — `EventActions` definition
- [`models/llm_response.py`](https://github.com/google/adk-python/blob/main/src/google/adk/models/llm_response.py) — parent class
- [`sessions/session.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/session.py) — stores `list[Event]`
- [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) — streams events to caller
