# Testing Examples — LlmAgent, Callbacks, Plugins, Tools

> **Official docs:** [Evaluation](https://google.github.io/adk-docs/evaluate/) | **Source:** [`tests/unittests/testing_utils.py`](https://github.com/google/adk-python/blob/main/tests/unittests/testing_utils.py) | **Prereqs:** [22-testing.md](22-testing.md)

*This file continues from [22-testing.md](22-testing.md), which covers MockModel, InMemoryRunner, simplify_events, and creating test dependencies.*

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

### Instruction (Static String / Callable / Async)

Test instruction behavior indirectly through `InMemoryRunner` — verify that the agent's output reflects the instruction, not internal method calls:

```python
def test_static_instruction():
    """Static instruction is passed to the LLM as system prompt."""
    mock = MockModel.create(responses=['I am helpful.'])
    agent = Agent(name='test', model=mock, instruction='You are helpful.')
    runner = InMemoryRunner(agent)
    events = runner.run('hello')
    # Verify the system instruction appeared in the model request
    assert mock.requests[0].config.system_instruction.parts[0].text == 'You are helpful.'

def test_callable_instruction():
    """Callable instruction is evaluated with state at runtime."""
    def _provider(ctx) -> str:
        return f'Greet {ctx.state["user_name"]}'

    mock = MockModel.create(responses=['Hello Alice!'])
    agent = Agent(name='test', model=mock, instruction=_provider)
    runner = InMemoryRunner(agent)
    # Pre-seed state so ctx.state["user_name"] doesn't raise KeyError
    session = runner.session_service.create_session(
        app_name=runner.app_name, user_id='test_user',
        state={'user_name': 'Alice'},
    )
    runner.run('hi', session_id=session.id, user_id='test_user')
    # Callable instruction was resolved with state
    assert 'Alice' in mock.requests[0].config.system_instruction.parts[0].text
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
    parent = LlmAgent(name='parent', model='gemini-2.5-flash', sub_agents=[sub])

    assert sub.canonical_model == parent.canonical_model
```

### output_key — Save Output to State

Test `output_key` through the runner — the private implementation method `_LlmAgent__maybe_save_output_to_state` is an anti-pattern (name-mangled, breaks on refactor). Use integration-level testing instead:

```python
def test_output_key():
    """output_key saves text output to session state."""
    mock = MockModel.create(responses=['Hello'])
    agent = Agent(name='test_agent', model=mock, output_key='result')
    runner = InMemoryRunner(agent)
    runner.run('go')
    assert runner.session.state.get('result') == 'Hello'

def test_output_key_not_saved_when_empty():
    """output_key is not set when model returns empty response."""
    mock = MockModel.create(responses=[''])
    agent = Agent(name='test_agent', model=mock, output_key='result')
    runner = InMemoryRunner(agent)
    runner.run('go')
    assert 'result' not in runner.session.state
```

### output_schema — Structured Output via Pydantic

```python
from pydantic import BaseModel

class PersonSchema(BaseModel):
    name: str
    age: int

def test_output_schema():
    """output_schema parses JSON response into Pydantic model and stores in state."""
    mock = MockModel.create(responses=['{"name": "Alice", "age": 30}'])
    agent = Agent(name='test', model=mock, output_key='result', output_schema=PersonSchema)
    runner = InMemoryRunner(agent)
    runner.run('describe a person')
    assert runner.session.state.get('result') == {'name': 'Alice', 'age': 30}
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
```

---


## Helper Classes for Agent Tests

The following helper class is used in tests throughout this file. It simulates a minimal `BaseAgent` that yields a single event — useful for testing callbacks without needing a full `LlmAgent`.

```python
class _TestingAgent(BaseAgent):
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            branch=ctx.branch,
            invocation_id=ctx.invocation_id,
            content=types.Content(parts=[types.Part(text='Hello, world!')]),
        )
```


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

mock = MockModel.create(responses=['original response'])
agent = Agent(name='root', model=mock, after_model_callback=my_after_model)
```

### on_model_error_callback — Handle LLM Errors

```python
mock = MockModel.create(responses=[], error=SystemError('API down'))

def handle_error(callback_context, llm_request, error) -> LlmResponse:
    return LlmResponse(content=ModelContent([types.Part.from_text(text='fallback')]))

agent = Agent(name='root', model=mock, on_model_error_callback=handle_error)

# TestInMemoryRunner creates a fresh session per call (unlike InMemoryRunner which
# reuses the same session). Use when you need isolation between test invocations.
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

---

## Testing Other Agent Types

### Custom BaseAgent

```python
from typing import AsyncGenerator
from google.adk.agents.base_agent import BaseAgent
from typing_extensions import override


@pytest.mark.asyncio
async def test_custom_agent():
    agent = _TestingAgent(name='test')
    ctx = await create_invocation_context(agent)
    events = [e async for e in agent.run_async(ctx)]
    assert events[0].content.parts[0].text == 'Hello, world!'
```

---

## Faking and Mocking Dependencies

### In-Memory Service Summary

| Service | In-Memory Class | Auto-wired by |
|---|---|---|
| Sessions | `InMemorySessionService` | `InMemoryRunner`, `create_invocation_context` |
| Artifacts | `InMemoryArtifactService` | `InMemoryRunner`, `create_invocation_context` |
| Memory | `InMemoryMemoryService` | `InMemoryRunner`, `create_invocation_context` |
| Credentials | `InMemoryCredentialService` | Manual wiring only |

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

### 3. Use MockModel Response Sequences to Drive Multi-Step Flows

```python
# Step 1: model calls tool  →  Step 2: model responds with text
mock = MockModel.create(responses=[
    Part.from_function_call(name='tool', args={}),   # invocation 1
    'Final answer.',                                   # invocation 2
])
```

### 4. Test Error Paths Explicitly

```python
# Model errors
mock = MockModel.create(responses=[], error=SystemError('down'))

# Missing tool (model calls nonexistent function)
mock = MockModel.create(responses=[
    Part.from_function_call(name='nonexistent', args={}),
])

# Missing args
result = await FunctionTool(my_fn).run_async(args={}, tool_context=MagicMock())
assert 'error' in result
```

### 5. Always Set Fake Environment Variables

```python
# conftest.py
@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY', 'fake')
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
| Inspect what model received | `mock_model.requests` |
| Test with plugins | `TestInMemoryRunner(agent, plugins=[...])` |
| Test tool in isolation | `FunctionTool(fn).run_async(args, tool_context=MagicMock())` |
| Create real ToolContext | `ToolContext(invocation_context=await create_invocation_context(agent))` |
| Create mock ToolContext | `ToolContext(invocation_context=MagicMock(spec=InvocationContext))` |
| Mock external services | `mock.patch(...)` or `AsyncMock()` |
| Fake env vars | `monkeypatch.setenv(...)` in conftest.py |
| Async test decorator | `@pytest.mark.asyncio` |
