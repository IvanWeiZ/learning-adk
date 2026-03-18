# Testing — Deterministic Unit Tests for ADK Agents

**Source:** [`tests/unittests/testing_utils.py`](../adk-python/tests/unittests/testing_utils.py) · [`tests/unittests/flows/llm_flows/test_model_callbacks.py`](../adk-python/tests/unittests/flows/llm_flows/test_model_callbacks.py) · [`tests/unittests/flows/llm_flows/test_tool_callbacks.py`](../adk-python/tests/unittests/flows/llm_flows/test_tool_callbacks.py) · [`tests/unittests/plugins/test_reflect_retry_tool_plugin.py`](../adk-python/tests/unittests/plugins/test_reflect_retry_tool_plugin.py)

---

> **Note:** `MockModel`, `InMemoryRunner`, and `simplify_events` are internal test utilities in the adk-python source tree — they are NOT included in the `pip install google-adk` package. To use them: clone the [adk-python repo](https://github.com/google/adk-python) and add `src/` to your PYTHONPATH, or copy `tests/unittests/testing_utils.py` into your project.

### Production vs. Test Stack

```
Production stack:                    Test stack:
┌──────────────┐                    ┌──────────────┐
│    Runner    │                    │ InMemoryRunner│
├──────────────┤                    ├──────────────┤
│    Agent     │  ← same agent →   │    Agent     │
├──────────────┤                    ├──────────────┤
│  BaseLlmFlow │  ← same flow →   │  BaseLlmFlow │
├──────────────┤                    ├──────────────┤
│   Gemini     │                    │  MockModel   │ ← swap point
│  (API call)  │                    │ (canned list)│
└──────────────┘                    └──────────────┘
      │                                   │
Google API                         Pre-loaded responses
(costs money,                      (free, deterministic,
 non-deterministic)                 no API key needed)
```

**Simplest possible test -- no API key needed:**

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

ADK provides a set of test utilities that let you write **fully deterministic** unit tests for agents without making any real LLM API calls. The core idea: replace the LLM with a `MockModel` that returns pre-loaded responses in order, wire it into an `InMemoryRunner` backed by in-memory services, and assert on the resulting events. Every test runs instantly, offline, and with predictable outputs.

---

## MockModel

`MockModel` extends `BaseLlm` and serves as a drop-in replacement for any real model. It holds a list of canned `LlmResponse` objects and yields them one at a time on each call to `generate_content_async`. It also records every `LlmRequest` it receives, so you can inspect what the agent sent to the model.

### Class Interface

```python
class MockModel(BaseLlm):
    model: str = 'mock'
    requests: list[LlmRequest] = []        # every request received (for assertions)
    responses: list[LlmResponse]           # pre-loaded responses to yield
    error: Exception | None = None         # if set, raised instead of yielding
    response_index: int = -1               # auto-incremented on each call
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

It also supports async via `run_async()`:

```python
events = await runner.run_async('Hi there')
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

## simplify_events

Raw `Event` objects contain verbose content structures. `simplify_events` collapses them into `(author, simplified_content)` tuples for readable assertions:

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

---

## Testing Callbacks

### before_model_callback — Short-Circuit the LLM

Return an `LlmResponse` from `before_model_callback` to skip the LLM entirely. The model is never called:

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

If the callback returns `None`, the LLM runs normally — useful for logging or request mutation.

### after_model_callback — Replace the LLM Response

Return an `LlmResponse` from `after_model_callback` to replace whatever the model returned:

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

## Testing Tool Callbacks

Tool callbacks intercept function calls before and after the tool runs. MockModel drives the test by emitting `function_call` parts.

### before_tool_callback — Short-Circuit or Mutate Args

**Short-circuit:** Return a dict to skip tool execution entirely. The dict becomes the function response:

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

**Mutate args:** Modify the `args` dict in-place and return `None` — the tool runs with the modified args:

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

Return a dict to replace the tool's response. Return `None` to keep the original:

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

Test error recovery when a tool raises an exception or when the LLM hallucinates a tool name:

```python
def simple_function_with_error() -> str:
    raise SystemError('tool broke')

async def recover_from_error(tool, args, tool_context, error):
    return {'result': 'recovered'}

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

## Testing Plugins

Plugins are tested by passing them to `TestInMemoryRunner` via the `plugins` parameter. The `ReflectAndRetryToolPlugin` tests show the pattern using `IsolatedAsyncioTestCase`:

```python
from unittest import IsolatedAsyncioTestCase
from google.adk.plugins.reflect_retry_tool_plugin import ReflectAndRetryToolPlugin
from tests.unittests.testing_utils import TestInMemoryRunner, MockModel
from google.adk.agents.llm_agent import LlmAgent

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
        # First call uses wrong name -> plugin catches error -> retry -> succeeds
        assert events[0].content.parts[0].function_call.name == 'wrong_name'
        assert events[1].content.parts[0].function_response.response['error_type'] == 'ValueError'
        assert events[2].content.parts[0].function_call.name == 'increase'
```

---

## Testing with pytest-asyncio

For async tests outside of `IsolatedAsyncioTestCase`, use the `@pytest.mark.asyncio` decorator. This is the pattern used throughout the ADK test suite:

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

Use the synchronous `InMemoryRunner` with plain `def test_*` functions when async is not needed:

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

A full working test that exercises a weather agent with tool calls, callbacks, and multi-turn conversation:

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
    # In tests this is driven by MockModel, but the function still
    # needs to return something for when the tool actually executes.
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
    # The tool was short-circuited with an error response
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
    # The request contains the conversation contents
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
| Inspect what model received | `mock_model.requests` |
| Test with plugins | `TestInMemoryRunner(agent, plugins=[...])` |
| Async test decorator | `@pytest.mark.asyncio` |
