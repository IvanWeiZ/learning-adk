# 16 — Error Reference: Every Error Path

> **Official docs:** [Runtime](https://google.github.io/adk-docs/runtime/) | **Source:** [`base_llm_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/base_llm_flow.py) · [`functions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/functions.py) · [`runners.py`](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py) · [`agents/run_config.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/run_config.py) | **Prereqs:** [01-request-lifecycle.md](01-request-lifecycle.md), [03-runners.md](03-runners.md)

---

## At a Glance

```
Error occurs in ADK
│
├── Tier 1: RECOVERABLE
│      callback fires — you can intercept and continue
│      on_model_error_callback → return LlmResponse to suppress
│      on_tool_error_callback  → return dict to suppress
│
├── Tier 2: FATAL
│      propagates uncaught to run_async() caller
│      no callback opportunity
│      handle with try/except in your code
│
└── Tier 3: SILENT
       no exception raised, no callback fired
       data silently lost or skipped
       only clue: check logs
```

ADK errors fall into three tiers. **Tier 1 (Recoverable):** errors that fire a callback (`on_model_error_callback`, `on_tool_error_callback`), giving your code a chance to intercept and continue. **Tier 2 (Fatal):** errors that propagate uncaught to the `run_async()` caller with no callback opportunity. **Tier 3 (Silent):** errors that produce no exception and no callback -- data is silently lost or skipped, and only log output reveals the problem.

---

## Class Hierarchy

| Class | Source File | Inherits From | Purpose |
|---|---|---|---|
| `LlmCallsLimitExceededError` | [`agents/invocation_context.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/invocation_context.py) | `Exception` | `RunConfig.max_llm_calls` exceeded |
| `SessionNotFoundError` | [`errors/session_not_found_error.py`](https://github.com/google/adk-python/blob/main/src/google/adk/errors/session_not_found_error.py) | `ValueError` | Session lookup failed, `auto_create_session=False` |
| `AlreadyExistsError` | [`errors/already_exists_error.py`](https://github.com/google/adk-python/blob/main/src/google/adk/errors/already_exists_error.py) | `Exception` | Duplicate `session_id` on `create_session()` |
| `ToolExecutionError` | [`errors/tool_execution_error.py`](https://github.com/google/adk-python/blob/main/src/google/adk/errors/tool_execution_error.py) | `Exception` | Tool authors raise with optional `error_type` |
| `_ResourceExhaustedError` | [`models/google_llm.py`](https://github.com/google/adk-python/blob/main/src/google/adk/models/google_llm.py) | `ClientError` | Gemini HTTP 429, adds mitigation link |

---

## Key API

### Error Flow Detail

```
run_async() invocation
│
├─ LLM call error
│   ├─ on_model_error_callback fires
│   ├─ Return LlmResponse → suppressed, continue with fallback
│   └─ Return None → re-raise (fatal)
│
├─ Tool call error
│   ├─ on_tool_error_callback fires
│   ├─ Return dict → suppressed, LLM sees error dict as tool result
│   └─ Return None → re-raise (fatal)
│
├─ LlmCallsLimitExceededError → no callback → fatal
├─ SessionNotFoundError → no callback → fatal
└─ Callback exception → no callback → fatal
```

### Common Errors & Best Handling

| Error | Tier | Best Handling | Alternative |
|-------|------|--------------|-------------|
| Gemini 429 (rate limit) | 1 | `on_model_error_callback` → return fallback `LlmResponse` | Catch in `try/except`, retry with backoff |
| Gemini 400/500 | 1 | `on_model_error_callback` → log + return user-friendly response | Let propagate, catch at top level |
| Tool raises exception | 1 | `on_tool_error_callback` → return error dict for LLM to retry | Wrap tool internals in try/except |
| Tool name hallucinated | 1 | `on_tool_error_callback` → return `{"error": "unknown tool"}` | LLM self-corrects on next loop |
| `LlmCallsLimitExceededError` | 2 | `try/except` around `run_async()` | Reduce `max_llm_calls` or simplify task |
| `SessionNotFoundError` | 2 | Pre-create session or `auto_create_session=True` | `try/except` with session creation fallback |
| Callback exception | 2 | Defensive coding in callbacks (try/except inside) | No alternative — always fatal |
| Agent transfer to unknown name | 2 | Validate `sub_agents` names match instruction | `try/except ValueError` around `run_async` |
| Silent event drop (InMemory) | 3 | Use `DatabaseSessionService` in production | Monitor logs for `WARNING` |
| Auth credential failure | 3 | Set up auth correctly; monitor logs | `on_tool_error_callback` catches downstream |

See Examples section below for copy-paste error handling patterns.

---

## How It Works

### Tier 1: Recoverable (Callback-Interceptable)

Both follow the same recovery pipeline: plugins fire first (in registration order), then the agent's own callback. If all return `None`, the exception re-raises and becomes fatal.

| Error source | Callback | Return to suppress | Common errors |
|-------------|----------|-------------------|---------------|
| LLM API (`generate_content_async`) | `on_model_error_callback` | `LlmResponse` | `ClientError` (400/403/500), `_ResourceExhaustedError` (429) |
| Tool execution (`tool.run_async`) | `on_tool_error_callback` | `dict` | Any tool exception, hallucinated tool name |

> **Tool-not-found:** when the LLM hallucinates a tool name not in the agent's registry, ADK catches it and fires `on_tool_error_callback` — same pipeline as a real tool exception.

### Tier 2: Fatal (No Callback Recovery)

These propagate directly to the `run_async()` caller. Must handle with `try/except`.

| Error | When | Fix |
|-------|------|-----|
| `LlmCallsLimitExceededError` | All allowed LLM calls exhausted (default: 500). Fires **before** the API call — `on_model_error_callback` never sees it. | Catch in `try/except`; reduce limit or simplify task |
| `SessionNotFoundError` | `get_session()` returns `None`, `auto_create_session=False` | Pre-create session or set `auto_create_session=True` |
| Callback exception | Any exception inside a callback | Code callbacks defensively (no `on_agent_error_callback` exists) |
| Agent transfer to unknown name | LLM transfers to a name not in the agent tree | Ensure `sub_agents` names match the instruction |
| Constructor validation | Invalid agent `name`, duplicate sub-agent instance, or `tools`/`system_instruction` in `generate_content_config` | Fix at construction time; see [04-agents.md](04-agents.md) |

### Tier 3: Silent Failures

No exception raised, no callback fired. Only logs reveal the problem.

| Failure | What happens | Mitigation |
|---------|-------------|------------|
| `InMemorySessionService.append_event()` with missing session | Events log `WARNING` but are not persisted. Appear to succeed but vanish on reload. | Use `DatabaseSessionService` in production |
| Toolset auth resolution | `ValueError` from `get_auth_credential()` is swallowed. Tool proceeds unauthenticated, fails on API call later. | Set up auth correctly; monitor logs for warnings |

---

## Examples

### Complete Error Handling Pattern

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.errors.session_not_found_error import SessionNotFoundError
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# Tier 1: Recoverable — use callbacks
async def handle_model_error(callback_context, llm_request, error):
    """Return LlmResponse to suppress error; return None to re-raise."""
    if "429" in str(error) or "ResourceExhausted" in type(error).__name__:
        await asyncio.sleep(2)  # brief backoff
        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text="The AI service is busy. Please try again.")]
            )
        )
    return None  # re-raise all other errors

async def handle_tool_error(tool, args, tool_context, error):
    """Return dict to suppress error (LLM sees it as tool result)."""
    return {"error": f"Tool '{tool.name}' failed: {error}"}

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    on_model_error_callback=handle_model_error,
    on_tool_error_callback=handle_tool_error,
)

# Tier 2: Fatal — wrap run_async
try:
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content,
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)
except LlmCallsLimitExceededError:
    print("Too many LLM calls — simplify the task or increase max_llm_calls")
except SessionNotFoundError:
    print("Session not found — create one first or set auto_create_session=True")
```

---

## Related

- [Request Lifecycle](01-request-lifecycle.md) — full traced request showing where errors can occur at each stage
- [Runners](03-runners.md) — `Runner.run_async()` orchestration and session lookup
- [Tools](09-tools.md) — tool execution model and `FunctionTool` error handling
