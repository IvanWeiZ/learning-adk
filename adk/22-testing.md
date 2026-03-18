# Testing — Deterministic Unit Tests for ADK Agents

**Source:** [`tests/unittests/testing_utils.py`](../adk-python/tests/unittests/testing_utils.py) · [`tests/unittests/agents/test_base_agent.py`](../adk-python/tests/unittests/agents/test_base_agent.py) · [`tests/unittests/flows/llm_flows/test_model_callbacks.py`](../adk-python/tests/unittests/flows/llm_flows/test_model_callbacks.py) · [`tests/unittests/flows/llm_flows/test_tool_callbacks.py`](../adk-python/tests/unittests/flows/llm_flows/test_tool_callbacks.py) · [`tests/unittests/tools/test_function_tool.py`](../adk-python/tests/unittests/tools/test_function_tool.py)

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
    def create(
        cls,
        responses: list[str] | list[types.Part] | list[LlmResponse] | list[list[types.Part]],
        error: Exception | None = None,
    ) -> 'MockModel': ...

    # Implements both sync and async generation:
    def generate_content(self, llm_request, stream=False) -> Generator[LlmResponse, None, None]: ...
    async def generate_content_async(self, llm_request, stream=False) -> AsyncGenerator[LlmResponse, None]: ...

    # Live connection support:
    async def connect(self, llm_request) -> BaseLlmConnection: ...

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

---

## InMemoryRunner

The test utilities provide two runner variants. Both wire together `InMemorySessionService`, `InMemoryArtifactService`, and `InMemoryMemoryService` so no external storage is needed.

### InMemoryRunner (Synchronous)

The `InMemoryRunner` in `testing_utils` provides a synchronous `run()` method for simple tests:

```python
from tests.unittests.testing_utils import InMemoryRunner, MockModel
from google.adk.agents.llm_agent import Agent

mock_model = MockModel.create(responses=['Hello from the agent!'])
agent = Agent(name='greeter', model=mock_model)

runner = InMemoryRunner(agent)
events = runner.run('Hi there')
# events is a list[Event] — the full conversation trace
```

Internally, `InMemoryRunner` creates a session on first use and reuses it for subsequent `run()` calls within the same runner instance. This lets you test multi-turn conversations:

```python
events_turn1 = runner.run('Hello')
events_turn2 = runner.run('Follow up question')
# Both turns share the same session with accumulated history
```

It also supports async via `run_async()`, live mode via `run_live()`, and accepts an `App` instance:

```python
# Async
events = await runner.run_async('Hi there')

# With an App object
from google.adk.apps.app import App
app = App(name='my_app', root_agent=agent)
runner = InMemoryRunner(app=app)

# With plugins
runner = InMemoryRunner(agent, plugins=[my_plugin])
```

### TestInMemoryRunner (Async, Session-per-Call)

`TestInMemoryRunner` extends the framework's own `InMemoryRunner` and creates a **new session for each call**, making tests fully isolated:

```python
from tests.unittests.testing_utils import TestInMemoryRunner, MockModel
from google.adk.agents.llm_agent import Agent

mock_model = MockModel.create(responses=['response'])
agent = Agent(name='root_agent', model=mock_model)

runner = TestInMemoryRunner(agent)
events = await runner.run_async_with_new_session('test input')
```

It also accepts `plugins` for testing plugin behavior:

```python
runner = TestInMemoryRunner(agent=agent, plugins=[my_plugin])
```

---

## Helper Classes and Functions

### ModelContent and UserContent

```python
from tests.unittests.testing_utils import ModelContent, UserContent

# ModelContent wraps parts with role='model'
content = ModelContent([types.Part.from_text(text='Hello')])

# UserContent wraps a string with role='user'
content = UserContent('Hello')
```

### create_invocation_context

Creates a fully wired `InvocationContext` for low-level tests that don't need a full runner:

```python
from tests.unittests.testing_utils import create_invocation_context

ctx = await create_invocation_context(
    agent=my_agent,
    user_content='test message',
    run_config=RunConfig(),
    plugins=[my_plugin],
)
# ctx has InMemorySessionService, InMemoryArtifactService, InMemoryMemoryService
```

### simplify_events

`simplify_events` collapses Events into `(author, content)` tuples:

```python
from tests.unittests.testing_utils import simplify_events

events = runner.run('test')
assert simplify_events(events) == [
    ('root_agent', 'Hello from the agent!'),
]
```

### Simplification Rules

The underlying `simplify_content` function applies these rules:

- If content has a **single text part**, return the stripped text string
- If content has a **single non-text part** (e.g., function_call), return the `Part` object
- If content has **multiple parts**, return the list of `Part` objects
- `function_call.id` and `function_response.id` are set to `None` to avoid flaky comparisons
- Events with no `content` are filtered out entirely

This means you can assert against plain strings for text responses and against `Part` objects for tool calls:

```python
from google.genai.types import Part

assert simplify_events(events) == [
    ('root_agent', Part.from_function_call(name='get_weather', args={'city': 'London'})),
    ('root_agent', Part.from_function_response(name='get_weather', response={'temp': 20})),
    ('root_agent', 'The weather in London is 20 degrees.'),
]
```

### simplify_resumable_app_events

For testing resumability, use `simplify_resumable_app_events`. It preserves checkpoint events and `end_of_agent` markers:

```python
from tests.unittests.testing_utils import simplify_resumable_app_events

results = simplify_resumable_app_events(events)
# Returns: list of (author, content | agent_state_dict | 'end_of_agent')
```

---

## Testing Agents by Type

### LlmAgent (Primary Agent)

The most common test pattern — swap the LLM with `MockModel`:

```python
from google.adk.agents.llm_agent import Agent
from tests.unittests.testing_utils import InMemoryRunner, MockModel, simplify_events

def test_llm_agent_basic():
    mock = MockModel.create(responses=['Hello!'])
    agent = Agent(name='greeter', model=mock)
    runner = InMemoryRunner(agent)
    assert simplify_events(runner.run('Hi')) == [('greeter', 'Hello!')]
```

Test instructions, model inheritance, and output_key:

```python
def test_agent_with_instruction():
    mock = MockModel.create(responses=['I am a weather bot.'])
    agent = Agent(
        name='weather_bot',
        model=mock,
        instruction='You are a helpful weather assistant.',
        output_key='last_response',
    )
    runner = InMemoryRunner(agent)
    events = runner.run('Who are you?')
    assert simplify_events(events) == [('weather_bot', 'I am a weather bot.')]
    # output_key writes the text response to session state
```

### Custom BaseAgent

Subclass `BaseAgent`, implement `_run_async_impl`, and test the yielded events directly:

```python
from typing import AsyncGenerator
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types
from typing_extensions import override

class _TestingAgent(BaseAgent):
    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            branch=ctx.branch,
            invocation_id=ctx.invocation_id,
            content=types.Content(parts=[types.Part(text='Hello, world!')]),
        )

# Test at the low level with InvocationContext:
@pytest.mark.asyncio
async def test_custom_agent():
    agent = _TestingAgent(name='test_agent')
    ctx = await create_invocation_context(agent)
    events = [e async for e in agent.run_async(ctx)]
    assert len(events) == 1
    assert events[0].author == 'test_agent'
    assert events[0].content.parts[0].text == 'Hello, world!'
```

### SequentialAgent

Sub-agents run in order. Assert on event sequence:

```python
from google.adk.agents.sequential_agent import SequentialAgent

agent_1 = _TestingAgent(name='agent_1')
agent_2 = _TestingAgent(name='agent_2')
sequential = SequentialAgent(name='seq', sub_agents=[agent_1, agent_2])

# Without resumability: 2 events (one per sub-agent)
ctx = await create_invocation_context(sequential)
events = [e async for e in sequential.run_async(ctx)]
assert len(events) == 2
assert events[0].author == 'agent_1'
assert events[1].author == 'agent_2'
```

With resumability, checkpoint events are emitted:

```python
from google.adk.apps.app import ResumabilityConfig

ctx = await create_invocation_context(sequential)
ctx.resumability_config = ResumabilityConfig(is_resumable=True)
events = [e async for e in sequential.run_async(ctx)]
# 5 events: checkpoint, agent_1, checkpoint, agent_2, final checkpoint (end_of_agent)
```

### ParallelAgent

Sub-agents run concurrently. Faster agents produce events first:

```python
from google.adk.agents.parallel_agent import ParallelAgent

agent_1 = _TestingAgent(name='agent_1')
agent_2 = _TestingAgent(name='agent_2')
parallel = ParallelAgent(name='par', sub_agents=[agent_1, agent_2])

ctx = await create_invocation_context(parallel)
events = [e async for e in parallel.run_async(ctx)]
# Both agents produce events; order depends on completion time
authors = {e.author for e in events if e.content}
assert authors == {'agent_1', 'agent_2'}
```

### LoopAgent

Runs sub-agents repeatedly up to `max_iterations`. Sub-agent can break early with `escalate`:

```python
from google.adk.agents.loop_agent import LoopAgent

agent = _TestingAgent(name='worker')
loop = LoopAgent(name='loop', max_iterations=3, sub_agents=[agent])

ctx = await create_invocation_context(loop)
events = [e async for e in loop.run_async(ctx)]
# Worker runs 3 times
content_events = [e for e in events if e.content]
assert len(content_events) == 3
```

Early exit via escalation:

```python
class EscalatingAgent(BaseAgent):
    @override
    async def _run_async_impl(self, ctx):
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            content=types.Content(parts=[types.Part(text='done')]),
            actions=EventActions(escalate=True),  # breaks the loop
        )
```

---

## Testing Agent Transfer

Use MockModel to emit `transfer_to_agent` function calls:

```python
from google.genai.types import Part

def test_agent_transfer():
    sub_agent = Agent(name='specialist', model=MockModel.create(responses=['handled']))
    mock = MockModel.create(responses=[
        Part.from_function_call(
            name='transfer_to_agent',
            args={'agent_name': 'specialist'}
        ),
    ])
    router = Agent(
        name='router',
        model=mock,
        sub_agents=[sub_agent],
    )

    runner = InMemoryRunner(router)
    events = runner.run('help me')
    # Check transfer happened
    transfer_events = [
        e for e in events
        if e.actions and e.actions.transfer_to_agent
    ]
    assert transfer_events[0].actions.transfer_to_agent == 'specialist'
```

---

## Testing Model Callbacks

### before_model_callback — Short-Circuit the LLM

Return `LlmResponse` to skip the LLM entirely:

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from tests.unittests.testing_utils import MockModel, InMemoryRunner, ModelContent, simplify_events
from google.adk.agents.llm_agent import Agent
from google.genai import types

def my_before_model(callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse:
    return LlmResponse(
        content=ModelContent([types.Part.from_text(text='intercepted')])
    )

mock_model = MockModel.create(responses=['should not appear'])
agent = Agent(
    name='root_agent',
    model=mock_model,
    before_model_callback=my_before_model,
)

runner = InMemoryRunner(agent)
assert simplify_events(runner.run('test')) == [
    ('root_agent', 'intercepted'),
]
```

`None` return = LLM runs normally (useful for logging/mutation).

### after_model_callback — Replace the LLM Response

Return `LlmResponse` to replace the model's response:

```python
def my_after_model(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse:
    return LlmResponse(
        content=ModelContent([types.Part.from_text(text='replaced')])
    )

agent = Agent(
    name='root_agent',
    model=mock_model,
    after_model_callback=my_after_model,
)

runner = InMemoryRunner(agent)
assert simplify_events(runner.run('test')) == [
    ('root_agent', 'replaced'),
]
```

### on_model_error_callback — Handle LLM Errors

Inject errors via `MockModel.create(responses=[], error=...)`, then test your error handler:

```python
import pytest

mock_model = MockModel.create(responses=[], error=SystemError('API down'))

# Error callback that provides a fallback response
def handle_error(callback_context, llm_request, error) -> LlmResponse:
    return LlmResponse(
        content=ModelContent([types.Part.from_text(text='fallback response')])
    )

agent = Agent(
    name='root_agent',
    model=mock_model,
    on_model_error_callback=handle_error,
)

runner = TestInMemoryRunner(agent)
events = await runner.run_async_with_new_session('test')
assert simplify_events(events) == [('root_agent', 'fallback response')]
```

If the error callback returns `None`, the original exception propagates:

```python
mock_model = MockModel.create(responses=[], error=SystemError('error'))
agent = Agent(name='root_agent', model=mock_model, on_model_error_callback=lambda **kw: None)

runner = TestInMemoryRunner(agent)
with pytest.raises(SystemError):
    await runner.run_async_with_new_session('test')
```

---

## Testing Agent Callbacks

### before_agent_callback — Bypass the Agent

Return `types.Content` to skip the agent entirely. Return `None` to let it run:

```python
# Sync callback that bypasses the agent
def bypass_agent(callback_context: CallbackContext) -> types.Content:
    return types.Content(parts=[types.Part(text='agent run is bypassed.')])

# Async variant works identically
async def async_bypass_agent(callback_context: CallbackContext) -> types.Content:
    return types.Content(parts=[types.Part(text='agent run is bypassed.')])

agent = _TestingAgent(
    name='test_agent',
    before_agent_callback=bypass_agent,
)
ctx = await create_invocation_context(agent)
events = [e async for e in agent.run_async(ctx)]

assert len(events) == 1
assert events[0].content.parts[0].text == 'agent run is bypassed.'
```

Verify the callback was called and `_run_async_impl` was skipped using `mocker.spy`:

```python
@pytest.mark.asyncio
async def test_before_agent_callback_bypass(mocker):
    agent = _TestingAgent(
        name='test_agent',
        before_agent_callback=bypass_agent,
    )
    ctx = await create_invocation_context(agent)
    spy_run = mocker.spy(agent, '_run_async_impl')
    spy_cb = mocker.spy(agent, 'before_agent_callback')

    events = [e async for e in agent.run_async(ctx)]

    spy_cb.assert_called_once()
    spy_run.assert_not_called()  # Agent was bypassed
```

### after_agent_callback — Append an Extra Event

```python
def append_reply(callback_context: CallbackContext) -> types.Content:
    return types.Content(
        parts=[types.Part(text='Agent reply from after agent callback.')]
    )

agent = _TestingAgent(
    name='test_agent',
    after_agent_callback=append_reply,
)
ctx = await create_invocation_context(agent)
events = [e async for e in agent.run_async(ctx)]

assert len(events) == 2
assert events[0].content.parts[0].text == 'Hello, world!'  # from agent
assert events[1].content.parts[0].text == 'Agent reply from after agent callback.'
```

### Callback Chains (Lists of Callbacks)

Pass a list of callbacks. First non-`None` return wins (short-circuits the chain):

```python
from unittest import mock
from functools import partial

# Mix sync and async callbacks
mock_cb_1 = mock.Mock(side_effect=partial(mock_sync_cb, ret_value=None))      # passes through
mock_cb_2 = mock.AsyncMock(side_effect=partial(mock_async_cb, ret_value='cb2'))  # returns → wins
mock_cb_3 = mock.Mock(side_effect=partial(mock_sync_cb, ret_value='cb3'))      # never called

agent = _TestingAgent(
    name='test_agent',
    before_agent_callback=[mock_cb_1, mock_cb_2, mock_cb_3],
)
ctx = await create_invocation_context(agent)
events = [e async for e in agent.run_async(ctx)]

mock_cb_1.assert_called_once()       # ran, returned None → next
mock_cb_2.assert_awaited_once()      # ran, returned 'cb2' → short-circuit
mock_cb_3.assert_not_called()        # never reached
assert events[0].content.parts[0].text == 'cb2'
```

---

## Testing Tool Callbacks

MockModel drives tool callback tests by emitting `function_call` parts.

### before_tool_callback — Short-Circuit or Mutate Args

Return a dict to skip tool execution (dict becomes the function response):

```python
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai.types import Part

def simple_function(input_str: str) -> str:
    return {'result': input_str}

def my_before_tool(tool: BaseTool, args: dict, tool_context: ToolContext):
    return {'intercepted': True}  # tool never runs

responses = [
    types.Part.from_function_call(name='simple_function', args={}),
    'done',
]
mock_model = MockModel.create(responses=responses)
agent = Agent(
    name='root_agent',
    model=mock_model,
    before_tool_callback=my_before_tool,
    tools=[simple_function],
)

runner = InMemoryRunner(agent)
assert simplify_events(runner.run('test')) == [
    ('root_agent', Part.from_function_call(name='simple_function', args={})),
    ('root_agent', Part.from_function_response(name='simple_function', response={'intercepted': True})),
    ('root_agent', 'done'),
]
```

Modify `args` in-place, return `None` — tool runs with modified args:

```python
def mutate_args(tool: BaseTool, args: dict, tool_context: ToolContext):
    args['input_str'] = 'modified_input'
    return None  # tool runs with mutated args

responses = [
    types.Part.from_function_call(name='simple_function', args={}),
    'done',
]
mock_model = MockModel.create(responses=responses)
agent = Agent(
    name='root_agent',
    model=mock_model,
    before_tool_callback=mutate_args,
    tools=[simple_function],
)

runner = InMemoryRunner(agent)
assert simplify_events(runner.run('test')) == [
    ('root_agent', Part.from_function_call(name='simple_function', args={})),
    ('root_agent', Part.from_function_response(
        name='simple_function', response={'result': 'modified_input'}
    )),
    ('root_agent', 'done'),
]
```

### after_tool_callback — Replace or Modify the Response

Return dict to replace response, `None` to keep original:

```python
def my_after_tool(tool, args, tool_context, tool_response=None):
    tool_response['result'] = 'modified_output'
    return tool_response

agent = Agent(
    name='root_agent',
    model=mock_model,
    after_tool_callback=my_after_tool,
    tools=[simple_function],
)
```

### on_tool_error_callback — Handle Tool Failures

Test error recovery with both sync and async error callbacks:

```python
def simple_function_with_error() -> str:
    raise SystemError('tool broke')

# Async error callback (sync also works)
async def recover_from_error(tool, args, tool_context, error):
    if tool.name == 'simple_function_with_error':
        return {'result': 'recovered'}
    return None  # re-raises original error

responses = [
    types.Part.from_function_call(name='simple_function_with_error', args={}),
    'done',
]
mock_model = MockModel.create(responses=responses)
agent = Agent(
    name='root_agent',
    model=mock_model,
    on_tool_error_callback=recover_from_error,
    tools=[simple_function_with_error],
)

runner = InMemoryRunner(agent)
assert simplify_events(runner.run('test')) == [
    ('root_agent', Part.from_function_call(name='simple_function_with_error', args={})),
    ('root_agent', Part.from_function_response(
        name='simple_function_with_error', response={'result': 'recovered'}
    )),
    ('root_agent', 'done'),
]
```

---

## Testing Tools with ToolContext

### FunctionTool — ToolContext Auto-Injection

A parameter named `tool_context` (or typed `ToolContext` / `Context`) is automatically injected and hidden from the LLM schema:

```python
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

def save_note(text: str, tool_context: ToolContext) -> str:
    tool_context.state['note'] = text
    return 'Note saved.'

tool = FunctionTool(save_note)
assert tool._context_param_name == 'tool_context'
assert 'tool_context' in tool._ignore_params  # hidden from LLM
```

Context parameter detection supports custom names with type annotations:

```python
from google.adk.agents.context import Context

# Detected by type annotation — any parameter name works
def my_tool(query: str, ctx: Context) -> str:
    return query

tool = FunctionTool(my_tool)
assert tool._context_param_name == 'ctx'
```

### Testing FunctionTool Directly (Unit-Level)

Create a mock `ToolContext` using `MagicMock` for isolated tool tests:

```python
from unittest.mock import MagicMock
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.session import Session
from google.adk.tools.tool_context import ToolContext

@pytest.fixture
def mock_tool_context() -> ToolContext:
    mock_invocation_context = MagicMock(spec=InvocationContext)
    mock_invocation_context.session = MagicMock(spec=Session)
    mock_invocation_context.session.state = MagicMock()
    return ToolContext(invocation_context=mock_invocation_context)

@pytest.mark.asyncio
async def test_function_tool_with_context(mock_tool_context):
    def sample_func(expected_arg: str, tool_context: ToolContext):
        return {'received_arg': expected_arg, 'context_present': bool(tool_context)}

    tool = FunctionTool(sample_func)
    result = await tool.run_async(
        args={'expected_arg': 'world', 'parameters': 'should_be_filtered'},
        tool_context=mock_tool_context,
    )
    assert result == {'received_arg': 'world', 'context_present': True}
```

### Testing Tools with State (Integration-Level)

Use `InMemoryRunner` for tools that read/write session state — no extra mocking needed:

```python
def save_preference(key: str, value: str, tool_context: ToolContext) -> str:
    tool_context.state[key] = value
    return f'Saved {key}={value}'

def read_preference(key: str, tool_context: ToolContext) -> str:
    return tool_context.state.get(key, 'not set')

mock = MockModel.create(responses=[
    Part.from_function_call(name='save_preference', args={'key': 'theme', 'value': 'dark'}),
    Part.from_function_call(name='read_preference', args={'key': 'theme'}),
    'Your theme is dark.',
])
agent = Agent(name='prefs', model=mock, tools=[save_preference, read_preference])

runner = InMemoryRunner(agent)
events = runner.run('set theme to dark then read it')
assert simplify_events(events)[-1] == ('prefs', 'Your theme is dark.')
```

### Testing Tools with Artifacts

`InMemoryRunner` wires `InMemoryArtifactService` automatically:

```python
def upload_file(name: str, content: str, tool_context: ToolContext) -> str:
    artifact = types.Part.from_text(text=content)
    version = tool_context.save_artifact(name, artifact)
    return f'Saved {name} v{version}'
```

### Testing Tool Confirmation (Human-in-the-Loop)

```python
from google.adk.tools.tool_confirmation import ToolConfirmation

def sample_func(arg1: str):
    return {'received_arg': arg1}

tool = FunctionTool(sample_func, require_confirmation=True)

# Setup ToolContext with required mocks
mock_invocation_context = MagicMock(spec=InvocationContext)
mock_invocation_context.session = MagicMock(spec=Session)
mock_invocation_context.session.state = MagicMock()
mock_invocation_context.agent = MagicMock()
mock_invocation_context.agent.name = 'test_agent'
tool_context = ToolContext(invocation_context=mock_invocation_context)
tool_context.function_call_id = 'test_function_call_id'

# First call — requests confirmation
result = await tool.run_async(args={'arg1': 'hello'}, tool_context=tool_context)
assert result == {'error': 'This tool call requires confirmation, please approve or reject.'}

# User rejects
tool_context.tool_confirmation = ToolConfirmation(confirmed=False)
result = await tool.run_async(args={'arg1': 'hello'}, tool_context=tool_context)
assert result == {'error': 'This tool call is rejected.'}

# User approves
tool_context.tool_confirmation = ToolConfirmation(confirmed=True)
result = await tool.run_async(args={'arg1': 'hello'}, tool_context=tool_context)
assert result == {'received_arg': 'hello'}
```

### Testing Agent Transfer from a Tool

```python
def escalate(reason: str, tool_context: ToolContext) -> str:
    tool_context.actions.transfer_to_agent = 'supervisor_agent'
    return f'Escalating: {reason}'

# Assert on the event's actions field after running:
events = runner.run('this needs a supervisor')
transfer_events = [e for e in events if e.actions and e.actions.transfer_to_agent]
assert transfer_events[0].actions.transfer_to_agent == 'supervisor_agent'
```

---

## Testing Plugins

### Plugin Callbacks Override Agent Callbacks

Plugins implement `before_agent_callback`, `after_agent_callback`, `before_model_callback`, `after_model_callback`, `before_tool_callback`, `after_tool_callback`. Plugin callbacks take precedence over agent-level callbacks:

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
```

Test with `InMemoryRunner` or `create_invocation_context`:

```python
# Plugin response overrides agent callback
mock_plugin = MockPlugin()
mock_plugin.enable_before_agent_callback = True

agent = _TestingAgent(
    name='test_agent',
    before_agent_callback=bypass_agent,  # agent callback exists but is skipped
)
ctx = await create_invocation_context(agent, plugins=[mock_plugin])
events = [e async for e in agent.run_async(ctx)]

assert events[0].content.parts[0].text == 'plugin intercepted'
```

### Plugin with TestInMemoryRunner

```python
from google.adk.plugins.reflect_retry_tool_plugin import ReflectAndRetryToolPlugin
from unittest import IsolatedAsyncioTestCase

class TestMyPlugin(IsolatedAsyncioTestCase):
    async def test_plugin_intercepts_error(self):
        plugin = ReflectAndRetryToolPlugin(max_retries=3)

        def increase(x: int) -> int:
            return x + 1

        wrong_call = types.Part.from_function_call(name='wrong_name', args={'x': 1})
        correct_call = types.Part.from_function_call(name='increase', args={'x': 1})
        mock_model = MockModel.create(responses=[wrong_call, correct_call, 'done'])

        agent = LlmAgent(name='root_agent', model=mock_model, tools=[increase])
        runner = TestInMemoryRunner(agent=agent, plugins=[plugin])

        events = await runner.run_async_with_new_session('test')
        assert events[0].content.parts[0].function_call.name == 'wrong_name'
        assert events[1].content.parts[0].function_response.response['error_type'] == 'ValueError'
        assert events[2].content.parts[0].function_call.name == 'increase'
```

---

## Faking and Mocking Dependencies

### In-Memory Service Implementations

ADK provides drop-in in-memory implementations for all services. These are automatically wired by `InMemoryRunner`:

| Service | In-Memory Implementation | Storage |
|---|---|---|
| Sessions | `InMemorySessionService` | `dict[app → user → session_id → Session]` |
| Artifacts | `InMemoryArtifactService` | `dict[path → list[_ArtifactEntry]]` |
| Memory | `InMemoryMemoryService` | `dict[app/user → session_id → events]` (keyword match) |
| Credentials | `InMemoryCredentialService` | `dict[app → user → key → AuthCredential]` |

### Using MagicMock for ToolContext

For unit-testing tools in isolation (without a full runner):

```python
from unittest.mock import MagicMock

mock_invocation_context = MagicMock(spec=InvocationContext)
mock_invocation_context.session = MagicMock(spec=Session)
mock_invocation_context.session.state = MagicMock()
tool_context = ToolContext(invocation_context=mock_invocation_context)
```

### Using mock.patch for External Services

```python
from unittest import mock

# Patch a module-level function
with mock.patch(
    'google.adk.flows.llm_flows.basic.can_use_output_schema_with_tools',
    mock.MagicMock(return_value=False),
) as patched:
    # ... test code ...
    patched.assert_called_once()

# Patch an async engine for database tests
def fake_create_async_engine(db_url, **kwargs):
    fake_engine = mock.Mock()
    fake_engine.dialect.name = 'postgresql'
    return fake_engine

with mock.patch.object(
    database_session_service,
    'create_async_engine',
    side_effect=fake_create_async_engine,
):
    svc = DatabaseSessionService('postgresql://...')
```

### Recording Subclasses

Extend an in-memory service to capture calls:

```python
class RecordingSessionService(InMemorySessionService):
    def __init__(self):
        super().__init__()
        self.captured = {}

    async def create_session(self, *, app_name, user_id, **kwargs):
        self.captured['app_name'] = app_name
        return await super().create_session(
            app_name=app_name, user_id=user_id, **kwargs
        )
```

### AsyncMock for Async Methods

```python
from unittest.mock import AsyncMock

runner.plugin_manager.close = AsyncMock()
await runner.close()
runner.plugin_manager.close.assert_awaited_once()
```

### mocker.spy (pytest-mock) for Call Verification

```python
@pytest.mark.asyncio
async def test_with_spy(mocker):
    agent = _TestingAgent(name='test')
    ctx = await create_invocation_context(agent)

    spy = mocker.spy(agent, '_run_async_impl')
    events = [e async for e in agent.run_async(ctx)]

    spy.assert_called_once()
```

### Fake Environment Variables (conftest.py Pattern)

ADK's test suite sets fake credentials to prevent real API calls:

```python
# conftest.py
_ENV_VARS = {
    'GOOGLE_API_KEY': 'fake_google_api_key',
    'GOOGLE_CLOUD_PROJECT': 'fake_google_cloud_project',
    'GOOGLE_CLOUD_LOCATION': 'fake_google_cloud_location',
}

@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    for key, value in _ENV_VARS.items():
        monkeypatch.setenv(key, value)
```

---

## Testing with pytest-asyncio

For async tests, use `@pytest.mark.asyncio`:

```python
import pytest
from tests.unittests.testing_utils import TestInMemoryRunner, MockModel, simplify_events
from google.adk.agents.llm_agent import Agent

@pytest.mark.asyncio
async def test_async_agent_behavior():
    mock_model = MockModel.create(responses=['async response'])
    agent = Agent(name='root_agent', model=mock_model)

    runner = TestInMemoryRunner(agent)
    events = await runner.run_async_with_new_session('hello')

    assert simplify_events(events) == [
        ('root_agent', 'async response'),
    ]
```

Sync alternative with `InMemoryRunner`:

```python
def test_sync_agent_behavior():
    mock_model = MockModel.create(responses=['sync response'])
    agent = Agent(name='root_agent', model=mock_model)

    runner = InMemoryRunner(agent)
    assert simplify_events(runner.run('hello')) == [
        ('root_agent', 'sync response'),
    ]
```

---

## Example: Complete Test File

Full test: tool calls, callbacks, multi-turn:

```python
"""tests/unittests/agents/test_weather_agent.py"""

import pytest
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import Agent
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google.genai.types import Part

from tests.unittests.testing_utils import (
    InMemoryRunner,
    MockModel,
    ModelContent,
    TestInMemoryRunner,
    simplify_events,
)

# ---- Tool definitions ----

def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {'city': city, 'temp_c': 20, 'condition': 'sunny'}

def set_reminder(message: str) -> dict:
    """Set a reminder."""
    return {'status': 'ok', 'message': message}

# ---- Tests ----

def test_single_tool_call():
    """Agent calls get_weather, receives the result, then responds."""
    mock_model = MockModel.create(responses=[
        Part.from_function_call(name='get_weather', args={'city': 'London'}),
        'The weather in London is 20C and sunny.',
    ])
    agent = Agent(
        name='weather_agent',
        model=mock_model,
        tools=[get_weather],
    )

    runner = InMemoryRunner(agent)
    events = runner.run('What is the weather in London?')

    assert simplify_events(events) == [
        ('weather_agent', Part.from_function_call(name='get_weather', args={'city': 'London'})),
        ('weather_agent', Part.from_function_response(
            name='get_weather',
            response={'city': 'London', 'temp_c': 20, 'condition': 'sunny'},
        )),
        ('weather_agent', 'The weather in London is 20C and sunny.'),
    ]

def test_multiple_tool_calls():
    """Agent calls two tools in sequence."""
    mock_model = MockModel.create(responses=[
        Part.from_function_call(name='get_weather', args={'city': 'Paris'}),
        Part.from_function_call(name='set_reminder', args={'message': 'Bring umbrella'}),
        'Done! Weather checked and reminder set.',
    ])
    agent = Agent(
        name='weather_agent',
        model=mock_model,
        tools=[get_weather, set_reminder],
    )

    runner = InMemoryRunner(agent)
    events = runner.run('Check Paris weather and remind me about umbrella')

    simplified = simplify_events(events)
    assert simplified[0] == ('weather_agent', Part.from_function_call(
        name='get_weather', args={'city': 'Paris'}
    ))
    assert simplified[-1] == ('weather_agent', 'Done! Weather checked and reminder set.')

def test_before_model_callback_adds_context():
    """before_model_callback that returns None lets the model run normally."""
    captured_requests = []

    def capture_request(callback_context: CallbackContext, llm_request: LlmRequest):
        captured_requests.append(llm_request)
        return None  # pass through to model

    mock_model = MockModel.create(responses=['response'])
    agent = Agent(
        name='weather_agent',
        model=mock_model,
        before_model_callback=capture_request,
    )

    runner = InMemoryRunner(agent)
    events = runner.run('hello')

    assert simplify_events(events) == [('weather_agent', 'response')]
    assert len(captured_requests) == 1

def test_before_tool_callback_validates_args():
    """before_tool_callback rejects calls with missing required args."""
    def validate_args(tool: BaseTool, args: dict, tool_context: ToolContext):
        if 'city' not in args or not args['city']:
            return {'error': 'city is required'}
        return None  # let tool run

    mock_model = MockModel.create(responses=[
        Part.from_function_call(name='get_weather', args={}),
        'I need a city name to check the weather.',
    ])
    agent = Agent(
        name='weather_agent',
        model=mock_model,
        before_tool_callback=validate_args,
        tools=[get_weather],
    )

    runner = InMemoryRunner(agent)
    events = runner.run('weather?')

    simplified = simplify_events(events)
    assert simplified[1] == ('weather_agent', Part.from_function_response(
        name='get_weather', response={'error': 'city is required'}
    ))

@pytest.mark.asyncio
async def test_model_error_with_fallback():
    """on_model_error_callback provides a fallback when the model fails."""
    mock_model = MockModel.create(responses=[], error=ConnectionError('timeout'))

    def fallback(callback_context, llm_request, error):
        return LlmResponse(
            content=ModelContent([
                types.Part.from_text(text='Service temporarily unavailable.')
            ])
        )

    agent = Agent(
        name='weather_agent',
        model=mock_model,
        on_model_error_callback=fallback,
    )

    runner = TestInMemoryRunner(agent)
    events = await runner.run_async_with_new_session('weather in Tokyo?')

    assert simplify_events(events) == [
        ('weather_agent', 'Service temporarily unavailable.'),
    ]

def test_inspect_model_requests():
    """MockModel records requests so you can assert on what was sent."""
    mock_model = MockModel.create(responses=['response'])
    agent = Agent(
        name='weather_agent',
        model=mock_model,
        instruction='You are a helpful weather assistant.',
    )

    runner = InMemoryRunner(agent)
    runner.run('What is the weather?')

    # MockModel captured the LlmRequest
    assert len(mock_model.requests) == 1
    request = mock_model.requests[0]
    assert any(
        part.text and 'weather' in part.text.lower()
        for content in request.contents
        for part in content.parts
    )
```

---

## Quick Reference

| What you need | What to use |
|---|---|
| Fake LLM responses | `MockModel.create(responses=[...])` |
| Fake LLM error | `MockModel.create(responses=[], error=...)` |
| Run agent (sync) | `InMemoryRunner(agent).run('msg')` |
| Run agent (async, new session) | `await TestInMemoryRunner(agent).run_async_with_new_session('msg')` |
| Readable assertions | `simplify_events(events)` |
| Resumability assertions | `simplify_resumable_app_events(events)` |
| Inspect what model received | `mock_model.requests` |
| Test with plugins | `TestInMemoryRunner(agent, plugins=[...])` |
| Test custom BaseAgent | Subclass, implement `_run_async_impl`, use `create_invocation_context` |
| Test SequentialAgent | Compose sub-agents, assert event order |
| Test ParallelAgent | Compose sub-agents, assert all agents produced events |
| Test LoopAgent | Set `max_iterations`, assert iteration count |
| Test agent transfer | Check `event.actions.transfer_to_agent` |
| Test callback chains | Pass list of callbacks, verify call counts with `mock.spy` |
| Test tool with ToolContext | `InMemoryRunner` auto-wires state/artifacts/memory |
| Unit-test tool in isolation | `MagicMock(spec=InvocationContext)` → `ToolContext(...)` |
| Test tool confirmation | Set `require_confirmation=True`, check `ToolConfirmation` |
| Mock external services | `mock.patch(...)` or recording subclasses |
| Fake env vars | `monkeypatch.setenv(...)` in conftest.py |
| Async test decorator | `@pytest.mark.asyncio` |
| Verify method was called | `mocker.spy(obj, 'method_name')` |
