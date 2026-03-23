# Testing — Deterministic Unit Tests for ADK Agents

> **Official docs:** [Evaluation](https://google.github.io/adk-docs/evaluate/) | **Source:** [`tests/unittests/testing_utils.py`](https://github.com/google/adk-python/blob/main/tests/unittests/testing_utils.py) | **Prereqs:** [04-agents.md](04-agents.md), [09-tools.md](09-tools.md)

> **Package availability warning:** `MockModel`, `InMemoryRunner` (test version), and `simplify_events` are internal test utilities in the adk-python source tree — they are **NOT** included in the `pip install google-adk` package. To use them: clone the [adk-python repo](https://github.com/google/adk-python) and add `src/` to your `PYTHONPATH`, or copy `tests/unittests/testing_utils.py` into your project.

ADK's test utilities enable deterministic agent tests without real LLM calls. Replace the LLM with `MockModel` (pre-loaded responses), wire into `InMemoryRunner`, assert on events. Tests run instantly and offline.

### Production vs. Test Stack

```
Production stack:            Test stack:
┌──────────────┐             ┌───────────────┐
│    Runner    │             │ InMemoryRunner │
├──────────────┤             ├───────────────┤
│    Agent     │ ← same ──→ │    Agent       │
├──────────────┤             ├───────────────┤
│  BaseLlmFlow │ ← same ──→ │  BaseLlmFlow  │
├──────────────┤             ├───────────────┤
│   Gemini     │             │  MockModel    │ ← swap point
│  (API call)  │             │ (canned list) │
└──────────────┘             └───────────────┘
       │                            │
  Google API               Pre-loaded responses
 (costs money,             (free, deterministic,
 non-deterministic)         no API key needed)
```

**Simplest possible test — no API key needed:**

```python
from google.adk.agents.llm_agent import Agent
from tests.unittests.testing_utils import InMemoryRunner, MockModel, simplify_events

def test_hello():
    mock = MockModel.create(responses=["Hello back!"])
    agent = Agent(name="greeter", model=mock)
    runner = InMemoryRunner(root_agent=agent)
    events = runner.run("Hello")
    assert simplify_events(events) == [("greeter", "Hello back!")]
```

---

## Test Utilities Reference

**Quick picker:** For most tests, use `InMemoryRunner` (multi-turn, session reuse) or `TestInMemoryRunner` (isolated, new session per call). Use `create_invocation_context` only for low-level unit tests that need direct access to `InvocationContext` without a full runner. See [22b-testing-context-setup.md](22b-testing-context-setup.md) for full context setup patterns.

ADK provides two categories of test utilities:

1. **Production in-memory services** (shipped with `google-adk` package) — lightweight implementations for sessions, artifacts, memory, and credentials
2. **Test-only utilities** (in `tests/unittests/testing_utils.py`) — `MockModel`, `InMemoryRunner` (test version), `simplify_events`, and helper functions

### Production In-Memory Services

These are part of the `google.adk` package and available to all users:

| Service | Class | Package Path |
|---|---|---|
| Sessions | `InMemorySessionService` | `google.adk.sessions.in_memory_session_service` |
| Artifacts | `InMemoryArtifactService` | `google.adk.artifacts.in_memory_artifact_service` |
| Memory | `InMemoryMemoryService` | `google.adk.memory.in_memory_memory_service` |
| Credentials | `InMemoryCredentialService` | `google.adk.auth.credential_service.in_memory_credential_service` |
| Runner | `InMemoryRunner` | `google.adk.runners` |

The production `InMemoryRunner` (in `google.adk.runners`) wires all three in-memory services automatically:

```python
# From google.adk.runners (production code, line 1596)
class InMemoryRunner(Runner):
    """An in-memory Runner for testing and development."""

    def __init__(
        self,
        agent: BaseAgent | None = None,
        *,
        app_name: str | None = None,       # defaults to 'InMemoryRunner'
        plugins: list[BasePlugin] | None = None,
        app: App | None = None,
        plugin_close_timeout: float = 5.0,
    ):
        super().__init__(
            app_name=app_name or 'InMemoryRunner',
            agent=agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
            plugins=plugins,
            app=app,
            plugin_close_timeout=plugin_close_timeout,
        )
```

### Test-Only Utilities (testing_utils.py)

These live in the adk-python source tree and must be copied or imported from the cloned repo:

| Utility | Purpose |
|---|---|
| `MockModel` | Drop-in LLM replacement with canned responses |
| `MockLlmConnection` | Live connection mock for streaming tests |
| `InMemoryRunner` (test) | Sync runner with session reuse for multi-turn tests |
| `TestInMemoryRunner` | Async runner with new session per call |
| `create_invocation_context()` | Builds a fully wired `InvocationContext` for low-level tests |
| `simplify_events()` | Collapses events into `(author, content)` tuples |
| `simplify_contents()` | Collapses content lists into `(role, content)` tuples |
| `simplify_resumable_app_events()` | Includes agent state and `end_of_agent` markers |
| `ModelContent` | Wraps parts with `role='model'` |
| `UserContent` | Wraps a string with `role='user'` |
| `append_user_content()` | Adds user messages to an existing session |

---

## MockModel

`MockModel` extends `BaseLlm` as a drop-in LLM replacement. Yields canned `LlmResponse` objects in order and records every `LlmRequest` for inspection.

### Class Interface

```python
class MockModel(BaseLlm):
    model: str = 'mock'
    requests: list[LlmRequest] = []       # every request received (for assertions)
    responses: list[LlmResponse]           # pre-loaded responses to yield
    error: Exception | None = None         # if set, raised instead of yielding
    response_index: int = -1               # auto-incremented on each call

    @classmethod
    def supported_models(cls) -> list[str]:
        return ['mock']
```

### Creating a MockModel

The `MockModel.create()` class method accepts several convenient input formats:

```python
from tests.unittests.testing_utils import MockModel

# From plain strings — each string becomes a text Part inside an LlmResponse
mock = MockModel.create(responses=['Hello!', 'Goodbye!'])

# From types.Part objects — useful for function calls
from google.genai import types
mock = MockModel.create(responses=[
    types.Part.from_function_call(name='get_weather', args={'city': 'London'}),
    'The weather in London is sunny.',
])

# From list[list[Part]] — multi-part responses
mock = MockModel.create(responses=[
    [types.Part.from_text(text='part1'), types.Part.from_text(text='part2')],
])

# From pre-built LlmResponse objects — full control
from google.adk.models.llm_response import LlmResponse
mock = MockModel.create(responses=[LlmResponse(content=...)])

# With an error — model raises on every call
mock = MockModel.create(responses=[], error=SystemError('API down'))
```

Each call to `generate_content_async` increments `response_index` and yields the next response. If `error` is set, it raises the error instead.

Test that a model error propagates correctly:

```python
import pytest
from google.adk.agents.llm_agent import Agent
from tests.unittests.testing_utils import InMemoryRunner, MockModel

def test_model_error_propagates():
    mock = MockModel.create(responses=[], error=SystemError('API down'))
    agent = Agent(name='test', model=mock)
    runner = InMemoryRunner(root_agent=agent)
    with pytest.raises(SystemError, match='API down'):
        runner.run('Hello')
```

### Inspecting What the Model Received

`MockModel` records every `LlmRequest` for assertion:

```python
mock_model = MockModel.create(responses=['response'])
agent = Agent(name='test', model=mock_model, instruction='Be helpful.')
runner = InMemoryRunner(root_agent=agent)
runner.run('Hello')

# Assert on the LlmRequest sent to the model
assert len(mock_model.requests) == 1
request = mock_model.requests[0]

# Check system instruction
assert 'Be helpful' in request.config.system_instruction

# Check conversation contents
from tests.unittests.testing_utils import simplify_contents
assert simplify_contents(request.contents) == [('user', 'Hello')]
```

---

## InMemoryRunner (Test Version)

### InMemoryRunner — Synchronous, Session Reuse

Creates a session on first use and reuses it for subsequent `run()` calls. Ideal for multi-turn tests:

```python
from tests.unittests.testing_utils import InMemoryRunner, MockModel
from google.adk.agents.llm_agent import Agent

mock_model = MockModel.create(responses=['Hello!', 'How can I help?'])
agent = Agent(name='greeter', model=mock_model)

runner = InMemoryRunner(root_agent=agent)
events_turn1 = runner.run('Hi there')
events_turn2 = runner.run('Follow up')
# Both turns share the same session with accumulated history
```

Constructor options:

```python
runner = InMemoryRunner(
    root_agent=agent,                   # or app=App(...)
    plugins=[my_plugin],                # optional plugin list
    response_modalities=['TEXT'],        # optional modalities
)

# Also supports async and live mode:
events = await runner.run_async('message')
events = runner.run_live(live_request_queue)
```

### TestInMemoryRunner — Async, New Session per Call

Creates a **new session for each call**, ensuring full test isolation:

```python
from tests.unittests.testing_utils import TestInMemoryRunner

runner = TestInMemoryRunner(agent, plugins=[my_plugin])
events = await runner.run_async_with_new_session('test input')
```

---

## simplify_events and simplify_contents

### simplify_events

Collapses Events into `(author, content)` tuples for readable assertions:

```python
from tests.unittests.testing_utils import simplify_events

events = runner.run('test')
assert simplify_events(events) == [
    ('root_agent', 'Hello from the agent!'),
]
```

**Simplification rules:**
- Single text part → stripped text string
- Single non-text part (e.g., function_call) → the `Part` object
- Multiple parts → list of `Part` objects
- `function_call.id` and `function_response.id` → set to `None` (avoids flaky comparisons)
- Events with no `content` → filtered out

```python
from google.genai.types import Part

assert simplify_events(events) == [
    ('root_agent', Part.from_function_call(name='get_weather', args={'city': 'London'})),
    ('root_agent', Part.from_function_response(name='get_weather', response={'temp': 20})),
    ('root_agent', 'The weather in London is 20 degrees.'),
]
```

### simplify_contents

Collapses `LlmRequest.contents` for asserting what was sent to the model:

```python
from tests.unittests.testing_utils import simplify_contents

assert simplify_contents(mock_model.requests[0].contents) == [
    ('user', 'First message'),
]
```

### simplify_resumable_app_events

For testing resumability, preserves checkpoint events and `end_of_agent` markers:

```python
from tests.unittests.testing_utils import simplify_resumable_app_events

results = simplify_resumable_app_events(events)
# Returns: list of (author, content | agent_state_dict | 'end_of_agent')
```

---

*Context setup patterns (`create_invocation_context`, `ToolContext`, `ReadonlyContext`, manual `InvocationContext`) have been moved to [22b-testing-context-setup.md](22b-testing-context-setup.md).*

*Continued in [22c-testing-examples.md](22c-testing-examples.md) — comprehensive test examples for LlmAgent features, callbacks, plugins, tools, and best practices.*
