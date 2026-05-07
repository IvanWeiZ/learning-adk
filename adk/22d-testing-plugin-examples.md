# Testing Examples — Plugins, Other Agent Types, Mocking, Best Practices

> **Official docs:** [Evaluation](https://google.github.io/adk-docs/evaluate/) | **Source:** [`tests/unittests/testing_utils.py`](https://github.com/google/adk-python/blob/main/tests/unittests/testing_utils.py) | **Prereqs:** [22c-testing-examples.md](22c-testing-examples.md)

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

_This file continues from [22c-testing-examples.md](22c-testing-examples.md), which covers LlmAgent testing, callbacks, and tools._

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

| Service     | In-Memory Class             | Auto-wired by                                 |
| ----------- | --------------------------- | --------------------------------------------- |
| Sessions    | `InMemorySessionService`    | `InMemoryRunner`, `create_invocation_context` |
| Artifacts   | `InMemoryArtifactService`   | `InMemoryRunner`, `create_invocation_context` |
| Memory      | `InMemoryMemoryService`     | `InMemoryRunner`, `create_invocation_context` |
| Credentials | `InMemoryCredentialService` | Manual wiring only                            |

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

| Goal                                | Approach                                                     |
| ----------------------------------- | ------------------------------------------------------------ |
| Test full agent behavior end-to-end | `InMemoryRunner` + `MockModel` + `simplify_events`           |
| Test a single LlmAgent field/config | `_create_readonly_context()` + direct method call            |
| Test a tool function in isolation   | `FunctionTool(fn).run_async(args, tool_context=MagicMock())` |
| Test callback logic in isolation    | Direct callback call with `CallbackContext`                  |
| Test agent-level callback wiring    | `_TestingAgent` + `create_invocation_context` + `mocker.spy` |
| Test plugin behavior                | `TestInMemoryRunner(agent, plugins=[...])`                   |
| Test multi-turn conversation        | `InMemoryRunner` (reuses session across `.run()` calls)      |
| Test session isolation              | `TestInMemoryRunner` (new session per call)                  |

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

| What you need                | What to use                                                              |
| ---------------------------- | ------------------------------------------------------------------------ |
| Fake LLM responses           | `MockModel.create(responses=[...])`                                      |
| Fake LLM error               | `MockModel.create(responses=[], error=...)`                              |
| Run agent (sync, multi-turn) | `InMemoryRunner(agent).run('msg')`                                       |
| Run agent (async, isolated)  | `await TestInMemoryRunner(agent).run_async_with_new_session('msg')`      |
| Readable event assertions    | `simplify_events(events)`                                                |
| Assert on model input        | `simplify_contents(mock.requests[N].contents)`                           |
| Inspect what model received  | `mock_model.requests`                                                    |
| Test with plugins            | `TestInMemoryRunner(agent, plugins=[...])`                               |
| Test tool in isolation       | `FunctionTool(fn).run_async(args, tool_context=MagicMock())`             |
| Create real ToolContext      | `ToolContext(invocation_context=await create_invocation_context(agent))` |
| Create mock ToolContext      | `ToolContext(invocation_context=MagicMock(spec=InvocationContext))`      |
| Mock external services       | `mock.patch(...)` or `AsyncMock()`                                       |
| Fake env vars                | `monkeypatch.setenv(...)` in conftest.py                                 |
| Async test decorator         | `@pytest.mark.asyncio`                                                   |
