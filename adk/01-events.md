# Events — The Universal Currency

**Source:** [`events/event.py`](../adk-python/src/google/adk/events/event.py) · [`events/event_actions.py`](../adk-python/src/google/adk/events/event_actions.py)

---

## [x] What It Is
<!-- completed: 2026-03-18T03:27:24.773Z -->

`Event` is the single shared data type that flows through the entire ADK system. Every observable action produces an Event:

- A user sends a message → Event
- The LLM replies with text → Event
- The LLM calls a tool → Event
- The tool returns a result → Event
- An agent transfers control to a sub-agent → Event

A `Session` is essentially just an ordered list of Events. Everything else in the system reads, writes, or transforms Events.

---

## [x] Class Hierarchy
<!-- completed: 2026-03-18T03:27:24.773Z -->

```
google.genai.types.Content   (raw LLM content from genai SDK)
        ↑
    LlmResponse              (models/llm_response.py — wraps Content + metadata)
        ↑
      Event                  (events/event.py — adds author, invocation_id, actions, branch)
```

`Event` extends `LlmResponse` which extends the genai SDK's content type. This means an Event can carry anything an LLM response can: text, function calls, function responses, blobs, thoughts.

---

## [x] Key Fields
<!-- completed: 2026-03-18T03:27:24.773Z -->

```python
class Event(LlmResponse):
    invocation_id: str        # which Runner.run_async() call produced this
    author: str               # 'user' or the agent's name
    actions: EventActions     # side-effects: state changes, transfers, auth, etc.
    branch: Optional[str]     # 'agent_1.agent_2.agent_3' — routing for multi-agent trees
    id: str                   # auto-generated UUID
    timestamp: float          # unix timestamp, auto-set

    # Inherited from LlmResponse / Content:
    content: Optional[types.Content]   # the actual payload (text, function calls, etc.)
    partial: Optional[bool]            # True for streaming chunks, False for final
```

---

## [x] EventActions — The Side-Effect Envelope
<!-- completed: 2026-03-18T03:27:24.773Z -->

`EventActions` carries all side-effects that an event triggers. Stored on `event.actions`.

```python
class EventActions(BaseModel):
    state_delta: dict[str, object]      # key-value updates to session state
    artifact_delta: dict[str, int]      # filename → new version (file uploads)
    transfer_to_agent: Optional[str]    # route control to this named agent
    escalate: Optional[bool]            # signal parent agent to take over
    skip_summarization: Optional[bool]  # don't summarize this tool response
    requested_auth_configs: dict        # tool is asking for OAuth credentials
    compaction: Optional[EventCompaction]  # summary of compacted old events
    end_of_agent: Optional[bool]        # agent finished its current run
    agent_state: Optional[dict]         # checkpoint for resumable invocations
```

`state_delta` is especially important: this is how agents write to persistent session state (e.g., `output_key` on `LlmAgent` writes here).

---

## [x] Key Methods on Event
<!-- completed: 2026-03-18T03:27:24.773Z -->

```python
event.is_final_response() -> bool
# True when the event is the last thing an agent yields for this turn.
# False if: event has function calls, function responses, partial=True,
#           or has trailing code execution results.

event.get_function_calls() -> list[FunctionCall]
# Extract tool invocations the LLM requested.

event.get_function_responses() -> list[FunctionResponse]
# Extract tool results (after tools have run).

event.has_trailing_code_execution_result() -> bool
# True if the last part of content is a code execution result.
```

---

## [x] The Branch Field
<!-- completed: 2026-03-18T03:27:24.773Z -->

In a multi-agent tree, sibling agents should not see each other's conversation history. The `branch` field encodes the path from root to the current agent:

```
root_agent.search_agent.summarizer_agent
```

When building LLM context, the flow filters events by branch so each agent only sees its own lineage's history.

---

## [x] How Events Flow
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

## [x] Related Files
<!-- completed: 2026-03-18T03:27:24.773Z -->

- [`events/event_actions.py`](../adk-python/src/google/adk/events/event_actions.py) — `EventActions` definition
- [`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py) — parent class
- [`sessions/session.py`](../adk-python/src/google/adk/sessions/session.py) — stores `list[Event]`
- [`runners.py`](../adk-python/src/google/adk/runners.py) — streams events to caller
