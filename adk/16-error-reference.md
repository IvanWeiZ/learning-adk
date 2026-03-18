# Error Reference

Every exception, silent failure, and recovery point in the ADK execution pipeline.

**Source:** [`base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) · [`functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py) · [`runners.py`](../adk-python/src/google/adk/runners.py) · [`run_config.py`](../adk-python/src/google/adk/agents/run_config.py)

---

## Error Architecture

ADK errors fall into three tiers:

- **Tier 1 — Recoverable**: errors that fire a callback, giving your code a chance to intercept and continue.
- **Tier 2 — Fatal**: errors that propagate uncaught to the `run_async()` caller.
- **Tier 3 — Silent**: errors that produce no exception and no callback -- data is silently lost or skipped.

```
                    Error occurs
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  Tier 1  │ │  Tier 2  │ │  Tier 3  │
     │RECOVERABLE│ │  FATAL  │ │  SILENT  │
     └────┬─────┘ └────┬─────┘ └────┬─────┘
          │             │             │
     callback       propagates     no exception
     can intercept  to caller      no callback
          │             │             │
     on_model_error  try/except    data silently
     on_tool_error   in your code  lost or skipped
```

### Minimum Error Handling (Copy-Paste Starter)

```python
from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.errors.session_not_found_error import SessionNotFoundError

# Tier 1: Recoverable — use callbacks
agent = LlmAgent(
    on_model_error_callback=lambda ctx, req, err: LlmResponse(
        content=Content(parts=[Part(text="Sorry, the AI service is temporarily unavailable.")])
    ) if isinstance(err, ClientError) else None,
)

# Tier 2: Fatal — wrap run_async
try:
    async for event in runner.run_async(...):
        if event.is_final_response():
            print(event.content.parts[0].text)
except LlmCallsLimitExceededError:
    print("Too many LLM calls — simplify the task")
except SessionNotFoundError:
    print("Session not found — create one first")

# Tier 3: Silent — use DatabaseSessionService in production
# InMemorySessionService can silently drop events (see docs)
```

### Previous Detailed View

```
run_async() invocation
│
├─ LLM call ──→ exception ──→ on_model_error_callback ──→ handled? ──→ continue
│                                                      └─ not handled ──→ re-raise (fatal)
│
├─ Tool call ──→ exception ──→ on_tool_error_callback ──→ handled? ──→ continue
│                                                      └─ not handled ──→ re-raise (fatal)
│
├─ LlmCallsLimitExceededError ──→ (no callback) ──→ fatal, propagates directly
│
├─ SessionNotFoundError ──→ (no callback) ──→ fatal, propagates directly
│
└─ Callback exception ──→ (no callback) ──→ fatal, propagates directly
```

---

## Custom Exception Classes

| Class | Source File | Inherits From | Purpose |
|---|---|---|---|
| `LlmCallsLimitExceededError` | [`run_config.py`](../adk-python/src/google/adk/agents/run_config.py) | `Exception` | `RunConfig.max_llm_calls` exceeded |
| `SessionNotFoundError` | [`runners.py`](../adk-python/src/google/adk/runners.py) | `ValueError` | Session lookup failed, `auto_create_session=False` |
| `AlreadyExistsError` | [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) | `Exception` | Duplicate `session_id` on `create_session()` |
| `ToolExecutionError` | [`errors/tool_execution_error.py`](../adk-python/src/google/adk/errors/tool_execution_error.py) | `Exception` | Tool authors raise with optional `error_type` |
| `_ResourceExhaustedError` | [`models/google_llm.py`](../adk-python/src/google/adk/models/google_llm.py) | `ClientError` | Gemini HTTP 429, adds mitigation link |

---

## Recoverable Errors (Callback-Interceptable)

### LLM API Errors

Any exception from `llm.generate_content_async()` is caught by `_run_and_handle_error()` in [`base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py).

**Recovery pipeline:**

1. Plugin `on_model_error_callback` hooks fire first (in registration order)
2. Agent-level `on_model_error_callback` fires next
3. If all callbacks return `None`, the exception is re-raised (becomes fatal)

**Common errors:**

- `ClientError` — Gemini 400/403/500 responses
- `_ResourceExhaustedError` — Gemini 429 (rate limit). Includes a link to quota increase docs in the error message.

### Tool Execution Errors

Any exception from `tool.run_async()` is caught in [`functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py).

**Recovery pipeline:**

1. Plugin `on_tool_error_callback` hooks fire first
2. Agent-level `on_tool_error_callback` fires next
3. If all callbacks return `None`, the exception is re-raised (becomes fatal)

**Also handles tool-not-found:** when the LLM hallucinates a tool name that does not exist in the agent's tool registry, this is caught and reported as a tool error.

---

## Fatal Errors (No Callback Recovery)

### `LlmCallsLimitExceededError`

Raised when the invocation has used all allowed LLM calls.

- **Critical gotcha**: this fires BEFORE the API call is made, so `on_model_error_callback` never sees it.
- Must catch in application code wrapping `run_async()`.
- Default limit: **500** (`RunConfig.max_llm_calls`).
- Typical cause: agent loops (tool → LLM → tool → LLM ...) that never reach a termination condition.

### `SessionNotFoundError`

Raised when `Runner.run_async()` calls `get_session()`, the service returns `None`, and `auto_create_session=False`.

- Fix: pre-create sessions before calling `run_async()`, or set `auto_create_session=True` on the `Runner`.

### Callback Exceptions

If any `before_agent_callback`, `after_agent_callback`, `before_model_callback`, `after_model_callback`, `before_tool_callback`, or `after_tool_callback` raises an exception, it crashes the entire invocation.

- There is **no** `on_agent_error_callback`.
- Only `on_model_error_callback` and `on_tool_error_callback` exist as recovery points — and they only fire for model/tool errors, **not** for callback errors.
- Defensive coding inside callbacks is essential.

### Agent Transfer Errors

When the LLM issues a transfer to an agent name that does not exist in the agent tree:

```
ValueError("Agent 'X' not found")
```

This propagates uncaught. Mitigation: ensure `sub_agents` names match what the LLM has been instructed to use.

### Constructor Validation Errors

These fire at agent construction time (before any `run_async()` call):

- Agent `name` must be a valid Python identifier — `"user"` is reserved by ADK.
- The same agent instance cannot appear as a sub-agent of two different parents. Use `clone()` to reuse.
- `generate_content_config` must **not** contain `tools`, `system_instruction`, or `response_schema` — these are managed by ADK internally.

---

## Silent Failures

### `InMemorySessionService.append_event()`

If the backing store does not contain the session (e.g., session was deleted between calls), events log a `WARNING` but are **not** persisted. No exception is raised.

This is the most dangerous silent failure in the pipeline — it causes **silent data loss**. Events appear to succeed but vanish on reload.

### Toolset Auth Resolution

`ValueError` from `CredentialManager.get_auth_credential()` is caught and swallowed. A warning is logged, and the toolset proceeds without authentication.

The tool will likely fail later when it tries to call the authenticated API. That failure **is** caught by `on_tool_error_callback`, so it is recoverable — but the root cause (missing credentials) can be hard to diagnose.

---

## Error Handling Patterns

### Recommended Pattern

```python
from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.runners import Runner

# Catch fatal errors that bypass callbacks
try:
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        process(event)
except LlmCallsLimitExceededError:
    # max_llm_calls exceeded — on_model_error_callback does NOT fire for this
    log.error("Agent exceeded LLM call limit")
except SessionNotFoundError:
    # session not found and auto_create_session=False
    log.error("Session does not exist")

# Use callbacks for recoverable errors
async def handle_model_error(
    callback_context, llm_request, error
):
    if isinstance(error, _ResourceExhaustedError):
        await asyncio.sleep(5)
        return None  # returning None re-raises; return LlmResponse to recover
    return None

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    on_model_error_callback=handle_model_error,
    on_tool_error_callback=my_tool_error_handler,
)
```

---

## Cross-References

- [Request Lifecycle](01-request-lifecycle.md) — full traced request showing where errors can occur at each stage
- [Runners](03-runners.md) — `Runner.run_async()` orchestration and session lookup
- [Tools](09-tools.md) — tool execution model and `FunctionTool` error handling
