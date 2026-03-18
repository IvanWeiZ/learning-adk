# Testing — Deterministic Unit Tests for ADK Agents

**Source:** [`tests/unittests/testing_utils.py`](../adk-python/tests/unittests/testing_utils.py) · [`tests/unittests/agents/test_llm_agent_fields.py`](../adk-python/tests/unittests/agents/test_llm_agent_fields.py) · [`tests/unittests/agents/test_llm_agent_callbacks.py`](../adk-python/tests/unittests/agents/test_llm_agent_callbacks.py) · [`tests/unittests/agents/test_llm_agent_output_save.py`](../adk-python/tests/unittests/agents/test_llm_agent_output_save.py) · [`tests/unittests/agents/test_llm_agent_include_contents.py`](../adk-python/tests/unittests/agents/test_llm_agent_include_contents.py) · [`tests/unittests/flows/llm_flows/test_tool_callbacks.py`](../adk-python/tests/unittests/flows/llm_flows/test_tool_callbacks.py) · [`tests/unittests/tools/test_function_tool.py`](../adk-python/tests/unittests/tools/test_function_tool.py)

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

## Testing LlmAgent — Comprehensive Guide

`LlmAgent` (aliased as `Agent`) is the primary agent type. Here is how to test every major feature.

### Basic Response

```python
def test_basic_response():
    mock = MockModel.create(responses=['Hello!'])
    agent = Agent(name='greeter', model=mock)
    runner = InMemoryRunner(agent)
    assert simplify_events(runner.run('Hi')) == [('greeter', 'Hello!')]
```

### Instruction (Static String)

```python
async def test_static_instruction():
    agent = LlmAgent(name='test', instruction='You are helpful.')
    ctx = await _create_readonly_context(agent)

    instruction, bypass = await agent.canonical_instruction(ctx)
    assert instruction == 'You are helpful.'
    assert not bypass  # state injection not bypassed
```

### Instruction (Callable with State)

```python
async def test_callable_instruction():
    def _provider(ctx: ReadonlyContext) -> str:
        return f'Greet {ctx.state["user_name"]}'

    agent = LlmAgent(name='test', instruction=_provider)
    ctx = await _create_readonly_context(agent, state={'user_name': 'Alice'})

    instruction, bypass = await agent.canonical_instruction(ctx)
    assert instruction == 'Greet Alice'
    assert bypass  # callable bypasses state injection (already handled)
```

### Instruction (Async Callable)

```python
async def test_async_instruction():
    async def _provider(ctx: ReadonlyContext) -> str:
        return f'instruction: {ctx.state["key"]}'

    agent = LlmAgent(name='test', instruction=_provider)
    ctx = await _create_readonly_context(agent, state={'key': 'value'})

    instruction, bypass = await agent.canonical_instruction(ctx)
    assert instruction == 'instruction: value'
```

### Tools — Single Tool Call

```python
def test_single_tool():
    def get_weather(city: str) -> dict:
        return {'temp': 20, 'condition': 'sunny'}

    mock = MockModel.create(responses=[
        Part.from_function_call(name='get_weather', args={'city': 'London'}),
        'It is 20C and sunny in London.',
    ])
    agent = Agent(name='weather', model=mock, tools=[get_weather])
    runner = InMemoryRunner(agent)

    assert simplify_events(runner.run('weather?')) == [
        ('weather', Part.from_function_call(name='get_weather', args={'city': 'London'})),
        ('weather', Part.from_function_response(
            name='get_weather', response={'temp': 20, 'condition': 'sunny'}
        )),
        ('weather', 'It is 20C and sunny in London.'),
    ]
```

### Tools — State Manipulation via ToolContext

```python
def test_tool_writes_state():
    def save_note(text: str, tool_context: ToolContext) -> str:
        tool_context.state['note'] = text
        return 'Saved.'

    mock = MockModel.create(responses=[
        Part.from_function_call(name='save_note', args={'text': 'buy milk'}),
        'Done.',
    ])
    agent = Agent(name='test', model=mock, tools=[save_note])
    runner = InMemoryRunner(agent)
    runner.run('save a note')

    # State was persisted in the session
    assert runner.session.state.get('note') == 'buy milk'
```

### Tools — Asserting on Args Sent to Model

```python
def test_tool_args_in_model_request():
    def my_tool(x: int) -> int:
        return x + 1

    mock = MockModel.create(responses=[
        Part.from_function_call(name='my_tool', args={'x': 5}),
        'Result is 6.',
    ])
    agent = Agent(name='test', model=mock, tools=[my_tool])
    runner = InMemoryRunner(agent)
    runner.run('increment 5')

    # Second request to model includes the function response
    second_request_contents = simplify_contents(mock.requests[1].contents)
    # Contains: user message, model function_call, user function_response
    assert any(
        isinstance(content, Part) and content.function_response
        for _, content in second_request_contents
    )
```

### Model Inheritance (Sub-Agent Inherits Parent Model)

```python
def test_model_inheritance():
    sub = LlmAgent(name='sub')
    parent = LlmAgent(name='parent', model='gemini-pro', sub_agents=[sub])

    assert sub.canonical_model == parent.canonical_model
```

### output_key — Save Output to State

```python
def test_output_key():
    agent = LlmAgent(name='test_agent', output_key='result')
    event = Event(
        invocation_id='inv',
        author='test_agent',
        content=types.Content(role='model', parts=[types.Part.from_text(text='Hello')]),
        actions=EventActions(),
    )

    agent._LlmAgent__maybe_save_output_to_state(event)

    assert event.actions.state_delta['result'] == 'Hello'
```

Output is NOT saved when:
- Event author differs from agent name (case-sensitive)
- `output_key` is not set
- Response is partial (streaming chunk, not final)
- Content is empty or whitespace-only

### output_schema — Structured Output via Pydantic

```python
from pydantic import BaseModel

class PersonSchema(BaseModel):
    name: str
    age: int

def test_output_schema():
    agent = LlmAgent(name='test', output_key='result', output_schema=PersonSchema)
    event = Event(
        invocation_id='inv',
        author='test',
        content=types.Content(
            role='model',
            parts=[types.Part.from_text(text='{"name": "Alice", "age": 30}')]
        ),
        actions=EventActions(),
    )

    agent._LlmAgent__maybe_save_output_to_state(event)

    assert event.actions.state_delta['result'] == {'name': 'Alice', 'age': 30}
```

### output_schema + tools (Allowed)

```python
def test_output_schema_with_tools():
    class Schema(BaseModel):
        pass

    def _a_tool():
        pass

    # Does not throw — output_schema is now allowed alongside tools
    LlmAgent(name='test', output_schema=Schema, tools=[_a_tool])
```

### include_contents — Conversation History Control

**`include_contents='default'`** — full history preserved across turns:

```python
@pytest.mark.asyncio
async def test_include_contents_default():
    def simple_tool(message: str) -> dict:
        return {'result': f'Processed: {message}'}

    mock = MockModel.create(responses=[
        types.Part.from_function_call(name='simple_tool', args={'message': 'first'}),
        'First response',
        'Second response',
    ])
    agent = LlmAgent(name='test', model=mock, include_contents='default', tools=[simple_tool])

    runner = InMemoryRunner(agent)
    runner.run('First message')
    runner.run('Second message')

    # Second turn sees full history from first turn
    second_turn = simplify_contents(mock.requests[2].contents)
    assert ('user', 'First message') in second_turn
    assert ('model', 'First response') in second_turn
    assert ('user', 'Second message') in second_turn
```

**`include_contents='none'`** — no history, only current input:

```python
@pytest.mark.asyncio
async def test_include_contents_none():
    mock = MockModel.create(responses=['First', 'Second'])
    agent = LlmAgent(name='test', model=mock, include_contents='none')

    runner = InMemoryRunner(agent)
    runner.run('First message')
    runner.run('Second message')

    # Second turn does NOT see first turn
    assert simplify_contents(mock.requests[1].contents) == [
        ('user', 'Second message'),
    ]
```

**`include_contents='none'` with SequentialAgent** — agent2 doesn't see user input but sees agent1 output:

```python
@pytest.mark.asyncio
async def test_include_contents_none_sequential():
    agent1_model = MockModel.create(responses=['Agent1 response: XYZ'])
    agent1 = LlmAgent(name='agent1', model=agent1_model)

    agent2_model = MockModel.create(responses=['Agent2 final'])
    agent2 = LlmAgent(name='agent2', model=agent2_model, include_contents='none')

    seq = SequentialAgent(name='seq', sub_agents=[agent1, agent2])
    runner = InMemoryRunner(seq)
    events = runner.run('Original request')

    # Agent2 does NOT see 'Original request'
    agent2_contents = simplify_contents(agent2_model.requests[0].contents)
    assert not any('Original request' in str(c) for _, c in agent2_contents)
    # But DOES see Agent1's output
    assert any('Agent1 response' in str(c) for _, c in agent2_contents)
```

### generate_content_config — Validation Rules

```python
# Allowed: thinking_config
LlmAgent(
    name='test',
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    ),
)

# NOT allowed: tools (use Agent.tools instead)
with pytest.raises(ValueError):
    LlmAgent(
        name='test',
        generate_content_config=types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=[])]
        ),
    )

# NOT allowed: system_instruction (use Agent.instruction instead)
with pytest.raises(ValueError):
    LlmAgent(
        name='test',
        generate_content_config=types.GenerateContentConfig(
            system_instruction='nope'
        ),
    )

# NOT allowed: response_schema (use Agent.output_schema instead)
with pytest.raises(ValueError):
    LlmAgent(
        name='test',
        generate_content_config=types.GenerateContentConfig(
            response_schema=MySchema
        ),
    )
```

### Agent Transfer

```python
def test_agent_transfer():
    sub = Agent(name='specialist', model=MockModel.create(responses=['handled']))
    mock = MockModel.create(responses=[
        Part.from_function_call(name='transfer_to_agent', args={'agent_name': 'specialist'}),
    ])
    router = Agent(name='router', model=mock, sub_agents=[sub])

    runner = InMemoryRunner(router)
    events = runner.run('help me')

    transfer_events = [e for e in events if e.actions and e.actions.transfer_to_agent]
    assert transfer_events[0].actions.transfer_to_agent == 'specialist'
```

### Transfer Flags

```python
def test_transfer_flags():
    sub = LlmAgent(name='sub')
    parent = LlmAgent(name='parent', sub_agents=[sub])

    # Transfers allowed by default
    assert not parent.disallow_transfer_to_parent
    assert not parent.disallow_transfer_to_peers
```

### Multi-Provider Model Strings

```python
# Gemini strings resolve to Gemini
agent = LlmAgent(name='test', model='gemini-2.0-flash')
assert isinstance(agent.canonical_model, Gemini)

# Claude strings resolve to Claude
agent = LlmAgent(name='test', model='claude-sonnet-4@20250514')
assert isinstance(agent.canonical_model, Claude)

# Provider-prefixed strings resolve to LiteLlm
agent = LlmAgent(name='test', model='openai/gpt-4o')
assert isinstance(agent.canonical_model, LiteLlm)
```

---

## Testing Agent Callbacks

### before_agent_callback — Bypass the Agent

Return `types.Content` to skip the agent entirely. Return `None` to let it run:

```python
def bypass_agent(callback_context: CallbackContext) -> types.Content:
    return types.Content(parts=[types.Part(text='bypassed')])

agent = _TestingAgent(
    name='test_agent',
    before_agent_callback=bypass_agent,
)
ctx = await create_invocation_context(agent)
events = [e async for e in agent.run_async(ctx)]

assert len(events) == 1
assert events[0].content.parts[0].text == 'bypassed'
```

Verify callback was called and `_run_async_impl` was skipped using `mocker.spy`:

```python
@pytest.mark.asyncio
async def test_before_agent_bypass(mocker):
    agent = _TestingAgent(name='test', before_agent_callback=bypass_agent)
    ctx = await create_invocation_context(agent)

    spy_run = mocker.spy(agent, '_run_async_impl')
    spy_cb = mocker.spy(agent, 'before_agent_callback')

    events = [e async for e in agent.run_async(ctx)]

    spy_cb.assert_called_once()
    spy_run.assert_not_called()  # agent was bypassed
```

### after_agent_callback — Append an Extra Event

```python
def append_reply(callback_context: CallbackContext) -> types.Content:
    return types.Content(parts=[types.Part(text='After-callback reply.')])

agent = _TestingAgent(name='test', after_agent_callback=append_reply)
ctx = await create_invocation_context(agent)
events = [e async for e in agent.run_async(ctx)]

assert len(events) == 2
assert events[0].content.parts[0].text == 'Hello, world!'  # from agent
assert events[1].content.parts[0].text == 'After-callback reply.'
```

### Callback Chains (Lists of Callbacks)

Pass a list. First non-`None` return wins (short-circuits):

```python
from unittest import mock
from functools import partial

mock_cb_1 = mock.Mock(side_effect=partial(sync_cb, ret_value=None))
mock_cb_2 = mock.AsyncMock(side_effect=partial(async_cb, ret_value='cb2'))
mock_cb_3 = mock.Mock(side_effect=partial(sync_cb, ret_value='cb3'))

agent = _TestingAgent(
    name='test',
    before_agent_callback=[mock_cb_1, mock_cb_2, mock_cb_3],
)
ctx = await create_invocation_context(agent)
events = [e async for e in agent.run_async(ctx)]

mock_cb_1.assert_called_once()       # ran, returned None
mock_cb_2.assert_awaited_once()      # returned 'cb2' → wins
mock_cb_3.assert_not_called()        # never reached
```

---

## Testing Model Callbacks

### before_model_callback — Short-Circuit the LLM

```python
def my_before_model(callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse:
    return LlmResponse(content=ModelContent([types.Part.from_text(text='intercepted')]))

mock = MockModel.create(responses=['should not appear'])
agent = Agent(name='root', model=mock, before_model_callback=my_before_model)

runner = InMemoryRunner(agent)
assert simplify_events(runner.run('test')) == [('root', 'intercepted')]
```

### after_model_callback — Replace the LLM Response

```python
def my_after_model(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse:
    return LlmResponse(content=ModelContent([types.Part.from_text(text='replaced')]))

agent = Agent(name='root', model=mock, after_model_callback=my_after_model)
```

### on_model_error_callback — Handle LLM Errors

```python
mock = MockModel.create(responses=[], error=SystemError('API down'))

def handle_error(callback_context, llm_request, error) -> LlmResponse:
    return LlmResponse(content=ModelContent([types.Part.from_text(text='fallback')]))

agent = Agent(name='root', model=mock, on_model_error_callback=handle_error)

runner = TestInMemoryRunner(agent)
events = await runner.run_async_with_new_session('test')
assert simplify_events(events) == [('root', 'fallback')]
```

---

## Testing Tool Callbacks

### before_tool_callback — Short-Circuit or Mutate Args

Return dict → skip tool (dict becomes the function response). Return `None` → tool runs.

```python
def simple_function(input_str: str) -> str:
    return {'result': input_str}

def intercept(tool: BaseTool, args: dict, tool_context: ToolContext):
    return {'intercepted': True}  # tool never runs

mock = MockModel.create(responses=[
    types.Part.from_function_call(name='simple_function', args={}),
    'done',
])
agent = Agent(name='root', model=mock, before_tool_callback=intercept, tools=[simple_function])

assert simplify_events(InMemoryRunner(agent).run('test'))[1] == (
    'root', Part.from_function_response(name='simple_function', response={'intercepted': True})
)
```

Mutate args in-place, return `None`:

```python
def mutate(tool, args, tool_context):
    args['input_str'] = 'modified'
    return None  # tool runs with modified args
```

### after_tool_callback / on_tool_error_callback

```python
# Replace tool response
def modify_response(tool, args, tool_context, tool_response=None):
    tool_response['result'] = 'modified'
    return tool_response

# Recover from tool errors (async also works)
async def recover(tool, args, tool_context, error):
    return {'result': 'recovered'}
```

---

## Testing Tools Directly

### FunctionTool — ToolContext Auto-Injection

A parameter named `tool_context` or typed `ToolContext` / `Context` is auto-injected and hidden from the LLM schema:

```python
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.context import Context

# Detected by parameter name
def tool_a(query: str, tool_context: ToolContext) -> str: ...
assert FunctionTool(tool_a)._context_param_name == 'tool_context'

# Detected by type annotation — any name works
def tool_b(query: str, ctx: Context) -> str: ...
assert FunctionTool(tool_b)._context_param_name == 'ctx'

# Custom name with ToolContext type
def tool_c(query: str, my_ctx: ToolContext) -> str: ...
assert FunctionTool(tool_c)._context_param_name == 'my_ctx'
```

### Unit-Testing a FunctionTool

```python
@pytest.mark.asyncio
async def test_function_tool_isolated(mock_tool_context):
    def sample(expected_arg: str, tool_context: ToolContext):
        return {'received': expected_arg, 'has_ctx': bool(tool_context)}

    tool = FunctionTool(sample)
    result = await tool.run_async(
        args={'expected_arg': 'hello', 'parameters': 'filtered_out'},
        tool_context=mock_tool_context,
    )
    assert result == {'received': 'hello', 'has_ctx': True}
```

### Testing Tool Confirmation (Human-in-the-Loop)

```python
from google.adk.tools.tool_confirmation import ToolConfirmation

tool = FunctionTool(sample_func, require_confirmation=True)
tool_context = ToolContext(invocation_context=mock_invocation_context)
tool_context.function_call_id = 'fc_123'

# First call → requests confirmation
result = await tool.run_async(args={'arg1': 'hi'}, tool_context=tool_context)
assert result == {'error': 'This tool call requires confirmation, please approve or reject.'}

# Reject
tool_context.tool_confirmation = ToolConfirmation(confirmed=False)
result = await tool.run_async(args={'arg1': 'hi'}, tool_context=tool_context)
assert result == {'error': 'This tool call is rejected.'}

# Approve
tool_context.tool_confirmation = ToolConfirmation(confirmed=True)
result = await tool.run_async(args={'arg1': 'hi'}, tool_context=tool_context)
assert result == {'received_arg': 'hi'}
```

### Testing Parameter Validation Errors

```python
@pytest.mark.asyncio
async def test_missing_args():
    def my_func(arg1: str, arg2: str):
        return arg1

    tool = FunctionTool(my_func)
    result = await tool.run_async(args={'arg1': 'hello'}, tool_context=MagicMock())
    assert 'error' in result
    assert 'arg2' in result['error']
```

---

## Testing Plugins

### Plugin Callbacks Override Agent Callbacks

Plugin callbacks execute first. If a plugin returns a non-`None` value, the agent callback is skipped:

```python
from google.adk.plugins.base_plugin import BasePlugin

class MockPlugin(BasePlugin):
    def __init__(self):
        self.name = 'mock_plugin'
        self.enable_before_agent_callback = False

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> types.Content | None:
        if not self.enable_before_agent_callback:
            return None
        return types.Content(parts=[types.Part(text='plugin intercepted')])

mock_plugin = MockPlugin()
mock_plugin.enable_before_agent_callback = True

agent = _TestingAgent(name='test', before_agent_callback=bypass_agent)
ctx = await create_invocation_context(agent, plugins=[mock_plugin])
events = [e async for e in agent.run_async(ctx)]

# Plugin wins — agent callback never called
assert events[0].content.parts[0].text == 'plugin intercepted'
```

### Testing ReflectAndRetryToolPlugin

```python
from google.adk.plugins.reflect_retry_tool_plugin import ReflectAndRetryToolPlugin

async def test_reflect_retry():
    plugin = ReflectAndRetryToolPlugin(max_retries=3)

    def increase(x: int) -> int:
        return x + 1

    wrong_call = Part.from_function_call(name='wrong_name', args={'x': 1})
    correct_call = Part.from_function_call(name='increase', args={'x': 1})
    mock = MockModel.create(responses=[wrong_call, correct_call, 'done'])

    agent = LlmAgent(name='root', model=mock, tools=[increase])
    runner = TestInMemoryRunner(agent=agent, plugins=[plugin])
    events = await runner.run_async_with_new_session('test')

    # First call wrong → error → retry → correct
    assert events[0].content.parts[0].function_call.name == 'wrong_name'
    assert events[1].content.parts[0].function_response.response['error_type'] == 'ValueError'
    assert events[2].content.parts[0].function_call.name == 'increase'
```

---

## Testing Other Agent Types

### Custom BaseAgent

```python
from typing import AsyncGenerator
from google.adk.agents.base_agent import BaseAgent
from typing_extensions import override

class _TestingAgent(BaseAgent):
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            branch=ctx.branch,
            invocation_id=ctx.invocation_id,
            content=types.Content(parts=[types.Part(text='Hello, world!')]),
        )

@pytest.mark.asyncio
async def test_custom_agent():
    agent = _TestingAgent(name='test')
    ctx = await create_invocation_context(agent)
    events = [e async for e in agent.run_async(ctx)]
    assert events[0].content.parts[0].text == 'Hello, world!'
```

### SequentialAgent, ParallelAgent, LoopAgent

See the _Testing Agents by Type_ section in the prior version for SequentialAgent, ParallelAgent, and LoopAgent patterns.

---

## Faking and Mocking Dependencies

### In-Memory Service Summary

| Service | In-Memory Class | Auto-wired by |
|---|---|---|
| Sessions | `InMemorySessionService` | `InMemoryRunner`, `create_invocation_context` |
| Artifacts | `InMemoryArtifactService` | `InMemoryRunner`, `create_invocation_context` |
| Memory | `InMemoryMemoryService` | `InMemoryRunner`, `create_invocation_context` |
| Credentials | `InMemoryCredentialService` | Manual wiring only |

`InMemoryCredentialService` stores credentials in a nested dict: `app_name → user_id → credential_key → AuthCredential`. Use it when testing tools that call `tool_context.save_credential()` or `tool_context.load_credential()`:

```python
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService

ctx = InvocationContext(
    invocation_id='test',
    agent=agent,
    session=session,
    session_service=session_service,
    credential_service=InMemoryCredentialService(),
)
```

### mock.patch for External Services

```python
from unittest import mock

# Patch google.auth.default for VertexAI tests
@mock.patch(
    'google.auth.default',
    mock.MagicMock(return_value=('credentials', 'project')),
)
async def test_vais_tool():
    # test code that needs auth
    ...

# Patch module-level functions
with mock.patch(
    'google.adk.flows.llm_flows.basic.can_use_output_schema_with_tools',
    mock.MagicMock(return_value=False),
):
    # test code
    ...
```

### AsyncMock for Async Methods

```python
from unittest.mock import AsyncMock

mock_service = AsyncMock()
mock_service.save_artifact.return_value = 1
# Use in InvocationContext: artifact_service=mock_service
```

### mocker.spy (pytest-mock)

```python
spy = mocker.spy(agent, '_run_async_impl')
events = [e async for e in agent.run_async(ctx)]
spy.assert_called_once()
```

### Fake Environment Variables

```python
# conftest.py
@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY', 'fake_key')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'fake_project')
    monkeypatch.setenv('GOOGLE_CLOUD_LOCATION', 'fake_location')
```

---

## Best Practices

### 1. Choose the Right Test Level

| Goal | Approach |
|---|---|
| Test full agent behavior end-to-end | `InMemoryRunner` + `MockModel` + `simplify_events` |
| Test a single LlmAgent field/config | `_create_readonly_context()` + direct method call |
| Test a tool function in isolation | `FunctionTool(fn).run_async(args, tool_context=MagicMock())` |
| Test callback logic in isolation | Direct callback call with `CallbackContext` |
| Test agent-level callback wiring | `_TestingAgent` + `create_invocation_context` + `mocker.spy` |
| Test plugin behavior | `TestInMemoryRunner(agent, plugins=[...])` |
| Test multi-turn conversation | `InMemoryRunner` (reuses session across `.run()` calls) |
| Test session isolation | `TestInMemoryRunner` (new session per call) |

### 2. Prefer simplify_events Over Manual Event Inspection

```python
# Good — readable, ignores IDs
assert simplify_events(events) == [('agent', 'response')]

# Avoid — brittle, tied to internal structure
assert events[0].content.parts[0].text == 'response'
```

Use `simplify_contents(mock.requests[N].contents)` to assert on what the model received.

### 3. Use MockModel Response Sequences to Drive Multi-Step Flows

Each response maps to one model invocation. Plan the sequence:

```python
# Step 1: model calls tool  →  Step 2: model responds with text
mock = MockModel.create(responses=[
    Part.from_function_call(name='tool', args={}),   # invocation 1
    'Final answer.',                                   # invocation 2
])
```

For multi-agent transfer:

```python
mock = MockModel.create(responses=[
    Part.from_function_call(name='transfer_to_agent', args={'agent_name': 'sub'}),
])
```

### 4. Use InMemoryRunner for State/Artifact Tests

`InMemoryRunner` wires real in-memory services — `tool_context.state`, `tool_context.save_artifact()`, etc. all work without additional mocking:

```python
runner = InMemoryRunner(agent)
runner.run('do something')
# Check session state
assert runner.session.state.get('key') == 'value'
```

### 5. Use MagicMock for Isolated Tool Tests

When you only need a `ToolContext` parameter and don't care about real state:

```python
result = await tool.run_async(args={'x': 1}, tool_context=MagicMock())
```

When you need `session.state` to exist (e.g., tool reads state):

```python
mock_ctx = MagicMock(spec=InvocationContext)
mock_ctx.session = MagicMock(spec=Session)
mock_ctx.session.state = {'existing_key': 'value'}
tool_context = ToolContext(invocation_context=mock_ctx)
```

### 6. Test Callback Chains with mock.Mock / mock.AsyncMock

Use `functools.partial` to control return values and assert call counts:

```python
from functools import partial
cb = mock.AsyncMock(side_effect=partial(my_cb_fn, ret_value='response'))
```

### 7. Always Set Fake Environment Variables

Prevent accidental real API calls in unit tests:

```python
# conftest.py
@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY', 'fake')
```

### 8. Use pytest.mark.asyncio for Async Tests

```python
@pytest.mark.asyncio
async def test_async():
    runner = TestInMemoryRunner(agent)
    events = await runner.run_async_with_new_session('hello')
```

Sync alternative when async isn't needed:

```python
def test_sync():
    runner = InMemoryRunner(agent)
    events = runner.run('hello')
```

### 9. Test Error Paths Explicitly

```python
# Model errors
mock = MockModel.create(responses=[], error=SystemError('down'))

# Tool errors
def broken_tool():
    raise RuntimeError('broke')

# Missing tool (model calls nonexistent function)
mock = MockModel.create(responses=[
    Part.from_function_call(name='nonexistent', args={}),
])

# Missing args
result = await FunctionTool(my_fn).run_async(args={}, tool_context=MagicMock())
assert 'error' in result
```

### 10. Name Agents with Valid Python Identifiers

Agent names must be valid Python identifiers. `"user"` is reserved by ADK. Tests verify this:

```python
with pytest.raises(ValueError):
    BaseAgent(name='not an identifier')
```

---

## Quick Reference

| What you need | What to use |
|---|---|
| Fake LLM responses | `MockModel.create(responses=[...])` |
| Fake LLM error | `MockModel.create(responses=[], error=...)` |
| Run agent (sync, multi-turn) | `InMemoryRunner(agent).run('msg')` |
| Run agent (async, isolated) | `await TestInMemoryRunner(agent).run_async_with_new_session('msg')` |
| Readable event assertions | `simplify_events(events)` |
| Assert on model input | `simplify_contents(mock.requests[N].contents)` |
| Resumability assertions | `simplify_resumable_app_events(events)` |
| Inspect what model received | `mock_model.requests` |
| Test with plugins | `TestInMemoryRunner(agent, plugins=[...])` |
| Test LlmAgent field | `_create_readonly_context(agent, state={...})` |
| Test tool in isolation | `FunctionTool(fn).run_async(args, tool_context=MagicMock())` |
| Create real ToolContext | `ToolContext(invocation_context=await create_invocation_context(agent))` |
| Create mock ToolContext | `ToolContext(invocation_context=MagicMock(spec=InvocationContext))` |
| Test tool confirmation | `FunctionTool(fn, require_confirmation=True)` + `ToolConfirmation` |
| Mock external services | `mock.patch(...)` or `AsyncMock()` |
| Fake env vars | `monkeypatch.setenv(...)` in conftest.py |
| Verify method called | `mocker.spy(obj, 'method_name')` |
| Async test decorator | `@pytest.mark.asyncio` |
