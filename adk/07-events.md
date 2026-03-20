# Events — The Universal Currency

**Source:** [`events/event.py`](../adk-python/src/google/adk/events/event.py) · [`events/event_actions.py`](../adk-python/src/google/adk/events/event_actions.py)

---

## What It Is
<!-- completed: 2026-03-18T03:27:24.773Z -->

`Event` is the universal data type. Every action produces one:

- A user sends a message → Event
- The LLM replies with text → Event
- The LLM calls a tool → Event
- The tool returns a result → Event
- An agent transfers control to a sub-agent → Event

A `Session` is an ordered list of Events.

### [ ] What's Inside an Event

```
┌─────────────────────────────────────────────────────┐
│ Event │
│ │
│ ┌─ Identity ──────────────────────────────────────┐ │
│ │ id: "evt-002" │ │
│ │ invocation_id: "e-inv-9f2a" │ │
│ │ author: "weather_agent" │ │
│ │ branch: None │ │
│ │ timestamp: 1741996801.891 │ │
│ └─────────────────────────────────────────────────┘ │
│ │
│ ┌─ Payload ───────────────────────────────────────┐ │
│ │ content: Content(role="model", parts=[...]) │ │
│ │ partial: False │ │
│ └─────────────────────────────────────────────────┘ │
│ │
│ ┌─ Side Effects (EventActions) ───────────────────┐ │
│ │ state_delta: {"result": "18°C in Tokyo"} │ │
│ │ transfer_to_agent: None │ │
│ │ escalate: None │ │
│ │ artifact_delta: {} │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### [ ] Events in a Single Turn

A tool-calling agent produces 4 events for one user turn:

```
User sends: "What's the weather in Tokyo?"

 evt-001 evt-002 evt-003 evt-004
 ┌──────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
 │ user │───────►│ model │──────►│ tool │───────►│ model │
 │ msg │ │ func call│ │ response │ │ final text │
 └──────┘ └──────────┘ └──────────┘ └──────────────┘
 author: author: author: author:
 "user" "weather_agent" "weather_agent" "weather_agent"
 is_final_response()
 persisted persisted persisted = True ← render
 (not yielded) (yielded) (yielded) (yielded)
```

- **evt-001**: Runner creates the user event and appends it to the session, but does not yield it.
- **evt-002**: LLM decides it needs to call the `get_weather` tool — event contains a `FunctionCall`.
- **evt-003**: Tool executes and returns a `FunctionResponse` with the weather data.
- **evt-004**: LLM synthesizes the final answer. `is_final_response()` returns `True`, signaling the caller to render this event.

---

## Class Hierarchy
<!-- completed: 2026-03-18T03:27:24.773Z -->

```
pydantic.BaseModel
 ↑
 LlmResponse (models/llm_response.py — contains content: Optional[types.Content])
 ↑
 Event (events/event.py — adds author, invocation_id, actions, branch)
```

`Event` extends `LlmResponse` (contains `content: Optional[types.Content]`). Carries text, function calls, function responses, blobs, or thoughts.

---

## Key Fields
<!-- completed: 2026-03-18T03:27:24.773Z -->

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

---

## EventActions — The Side-Effect Envelope
<!-- completed: 2026-03-18T03:27:24.773Z -->

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

---

## Key Methods on Event
<!-- completed: 2026-03-18T03:27:24.773Z -->

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

---

## The Branch Field
<!-- completed: 2026-03-18T03:27:24.773Z -->

Sibling agents don't see each other's history. `branch` encodes the root-to-current path:

```
root_agent.search_agent.summarizer_agent
```

The flow filters events by branch so each agent sees only its own lineage.

---

## How Events Flow
<!-- completed: 2026-03-18T03:27:24.773Z -->

```
1. User sends message
 → Runner creates Event(author='user', content=user_message)
 → Appended to Session.events

2. LLM responds with text
 → Flow creates Event(author=agent.name, content=llm_text)
 → Appended to Session.events

3. LLM calls a tool
 → Flow creates Event(author=agent.name, content=[FunctionCall(...)])
 → Tool executes

4. Tool returns result
 → Flow creates Event(author=agent.name, content=[FunctionResponse(...)])
 → Appended to Session.events

5. All events stream back to caller via Runner.run_async()
```

---

## Related Files
<!-- completed: 2026-03-18T03:27:24.773Z -->

- [`events/event_actions.py`](../adk-python/src/google/adk/events/event_actions.py) — `EventActions` definition
- [`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py) — parent class
- [`sessions/session.py`](../adk-python/src/google/adk/sessions/session.py) — stores `list[Event]`
- [`runners.py`](../adk-python/src/google/adk/runners.py) — streams events to caller
