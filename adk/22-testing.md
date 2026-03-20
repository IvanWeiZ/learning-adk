# Testing — Deterministic Unit Tests for ADK Agents

> **Official docs:** [Evaluation](https://google.github.io/adk-docs/evaluate/) | **Source:** [`tests/unittests/testing_utils.py`](https://github.com/google/adk-python/blob/main/tests/unittests/testing_utils.py) | **Prereqs:** [04-agents.md](04-agents.md), [09-tools.md](09-tools.md)

---

> **Note:** `MockModel`, `InMemoryRunner`, and `simplify_events` are internal test utilities in the adk-python source tree — they are NOT included in the `pip install google-adk` package. To use them: clone the [adk-python repo](https://github.com/google/adk-python) and add `src/` to your PYTHONPATH, or copy `tests/unittests/testing_utils.py` into your project.

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
    runner = InMemoryRunner(agent)
    events = runner.run("Hello")
    assert simplify_events(events) == [("greeter", "Hello back!")]
```

---

## What It Is

ADK's test utilities enable deterministic agent tests without real LLM calls. Replace the LLM with `MockModel` (pre-loaded responses), wire into `InMemoryRunner`, assert on events. Tests run instantly and offline.

---

## Test Utilities Reference

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

### Inspecting What the Model Received

`MockModel` records every `LlmRequest` for assertion:

```python
mock_model = MockModel.create(responses=['response'])
agent = Agent(name='test', model=mock_model, instruction='Be helpful.')
runner = InMemoryRunner(agent)
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

runner = InMemoryRunner(agent)
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

## Creating Dependencies

### create_invocation_context — Full Context Without a Runner

For low-level tests that need direct access to `InvocationContext` without a full runner:

```python
from tests.unittests.testing_utils import create_invocation_context

ctx = await create_invocation_context(
    agent=my_agent,
    user_content='test message',         # optional
    run_config=RunConfig(),              # optional
    plugins=[my_plugin],                 # optional
)
# ctx has:
#   ctx.artifact_service  → InMemoryArtifactService
#   ctx.session_service   → InMemorySessionService
#   ctx.memory_service    → InMemoryMemoryService
#   ctx.plugin_manager    → PluginManager(plugins)
#   ctx.session           → fresh session with app_name='test_app', user_id='test_user'
```

### Creating a ToolContext (Context)

**Important:** `ToolContext` is an alias for `Context` (see `tool_context.py` line 30: `ToolContext = Context`). `Context` extends `ReadonlyContext` and adds mutable state, artifacts, credentials, memory, and tool confirmation.

#### Option A: Via MagicMock (unit-level, for isolated tool testing)

```python
from unittest.mock import MagicMock
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.session import Session
from google.adk.tools.tool_context import ToolContext  # alias for Context

@pytest.fixture
def mock_tool_context() -> ToolContext:
    mock_invocation_context = MagicMock(spec=InvocationContext)
    mock_invocation_context.session = MagicMock(spec=Session)
    mock_invocation_context.session.state = MagicMock()
    return ToolContext(invocation_context=mock_invocation_context)
```

This is the simplest approach. Use it when you just need a `ToolContext` parameter and don't need real state or artifact operations.

#### Option B: Via create_invocation_context (integration-level, real services)

```python
from tests.unittests.testing_utils import create_invocation_context
from google.adk.tools.tool_context import ToolContext

async def make_real_tool_context() -> ToolContext:
    agent = LlmAgent(name='test_agent')
    ctx = await create_invocation_context(agent)
    return ToolContext(invocation_context=ctx)
```

This gives you real in-memory services, so `tool_context.state`, `tool_context.save_artifact()`, etc. all work.

#### Option C: Via InMemoryRunner (full integration, tools execute in agent loop)

```python
# No manual ToolContext creation needed — the runner wires everything
mock = MockModel.create(responses=[
    Part.from_function_call(name='my_tool', args={'x': 1}),
    'done',
])
agent = Agent(name='test', model=mock, tools=[my_tool])
runner = InMemoryRunner(agent)
events = runner.run('do it')
```

### Creating a ReadonlyContext (for instruction/field tests)

```python
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.in_memory_session_service import InMemorySessionService

async def _create_readonly_context(
    agent: LlmAgent, state: dict[str, Any] | None = None
) -> ReadonlyContext:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name='test_app', user_id='test_user', state=state
    )
    invocation_context = InvocationContext(
        invocation_id='test_id',
        agent=agent,
        session=session,
        session_service=session_service,
    )
    return ReadonlyContext(invocation_context)
```

### Creating an InvocationContext Manually

For maximum control, build `InvocationContext` directly:

```python
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.plugins.plugin_manager import PluginManager

session_service = InMemorySessionService()
session = await session_service.create_session(
    app_name='test_app', user_id='test_user'
)

ctx = InvocationContext(
    invocation_id='test_invocation_id',
    agent=my_agent,
    session=session,
    session_service=session_service,
    artifact_service=InMemoryArtifactService(),       # optional
    memory_service=InMemoryMemoryService(),            # optional
    plugin_manager=PluginManager(plugins=[]),           # optional
    run_config=RunConfig(),                             # optional
)
```

---

*Continued in [22b-testing-examples.md](22b-testing-examples.md) — comprehensive test examples for LlmAgent features, callbacks, plugins, tools, and best practices.*
