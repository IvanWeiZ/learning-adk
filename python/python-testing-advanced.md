# Python Testing & Mocking — Advanced Patterns

> **Part 1 is in [python-testing-and-mocking-guide.md](python-testing-and-mocking-guide.md)** — pytest basics, Mock/MagicMock/AsyncMock, patching, side_effect, spec/autospec, assertion methods, and fixtures.

---

### 8. Testing Async Code

#### Setup: pytest-asyncio

```bash
pip install pytest-asyncio
```

```python
# pyproject.toml — configure asyncio mode
# [tool.pytest.ini_options]
# asyncio_mode = "auto"    # auto-detect async tests (recommended)
```

#### Basic Async Tests

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# With asyncio_mode = "auto", just write async test functions
async def test_async_function():
    result = await some_async_function()
    assert result == "expected"

# Or explicitly mark (needed if asyncio_mode != "auto")
@pytest.mark.asyncio
async def test_explicit_async():
    result = await some_async_function()
    assert result == "expected"
```

#### Patching Async Functions

```python
# --- my_agents/llm_client.py ---
async def call_llm(prompt: str) -> str:
    # real implementation calls an API
    ...

# --- my_agents/agent.py ---
from my_agents.llm_client import call_llm

async def run_agent(query: str) -> str:
    response = await call_llm(query)
    return f"Agent says: {response}"

# --- tests/test_agent.py ---
@patch("my_agents.agent.call_llm", new_callable=AsyncMock)
async def test_run_agent(mock_call_llm):
    mock_call_llm.return_value = "hello world"
    result = await run_agent("test query")
    assert result == "Agent says: hello world"
    mock_call_llm.assert_awaited_once_with("test query")
```

#### AsyncMock-Specific Assertions

```python
mock = AsyncMock()
await mock("arg1")
await mock("arg2")

# These are like the sync versions but for await calls
mock.assert_awaited()                    # awaited at least once
mock.assert_awaited_once()               # awaited exactly once → FAILS (called twice)
mock.assert_awaited_with("arg2")         # last await matches
mock.assert_awaited_once_with("arg1")    # awaited once with these args → FAILS
mock.assert_any_await("arg1")            # at least one await matches
mock.await_count                          # 2
mock.await_args                           # call("arg2") — last await
mock.await_args_list                      # [call("arg1"), call("arg2")]
```

#### Testing asyncio.gather and Concurrency

```python
async def run_parallel_tools(tools: list, query: str) -> list:
    tasks = [tool.run(query) for tool in tools]
    return await asyncio.gather(*tasks)

async def test_parallel_execution():
    tool_a = AsyncMock(return_value="result_a")
    tool_b = AsyncMock(return_value="result_b")

    # Simulate tool_b taking longer
    async def slow_tool_b(query):
        await asyncio.sleep(0.1)
        return "result_b"
    tool_b.run = AsyncMock(side_effect=slow_tool_b)
    tool_a.run = AsyncMock(return_value="result_a")

    results = await run_parallel_tools([tool_a, tool_b], "test")
    assert results == ["result_a", "result_b"]
```

#### Testing Timeouts

```python
async def test_timeout_handling():
    mock_tool = AsyncMock(side_effect=asyncio.TimeoutError())

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(mock_tool(), timeout=1.0)
```

> **Note:** Testing a slow operation that actually takes time requires an async side_effect coroutine, not a lambda. `lambda: asyncio.sleep(10)` returns a coroutine object without awaiting it — use an `async def` instead:
>
> ```python
> async def slow_side_effect(*args, **kwargs):
>     await asyncio.sleep(10)
>
> @pytest.mark.asyncio
> async def test_graceful_timeout():
>     slow_mock = AsyncMock(side_effect=slow_side_effect)
>     result = await run_with_timeout(slow_mock, timeout=0.1)
>     assert result == {"error": "timeout"}
> ```

---

### 9. Mocking Generators and Async Generators

#### Mocking Sync Generators

```python
from unittest.mock import Mock, MagicMock

# Option 1: return_value with iter
def test_mocking_generator():
    mock_func = Mock(return_value=iter([1, 2, 3]))
    result = list(mock_func())
    assert result == [1, 2, 3]

# Option 2: MagicMock as an iterable
def test_mock_iterable():
    m = MagicMock()
    m.__iter__.return_value = iter(["event1", "event2", "event3"])
    assert list(m) == ["event1", "event2", "event3"]
```

#### Mocking Async Generators (Critical for ADK)

```python
from unittest.mock import AsyncMock, MagicMock
import pytest

# ADK agents return AsyncGenerator[Event, None]
# Here's how to mock that:

# Option 1: Create a real async generator function
async def fake_agent_run(*args, **kwargs):
    yield {"type": "thinking", "content": "Processing..."}
    yield {"type": "tool_call", "content": "search(query)"}
    yield {"type": "response", "content": "Final answer"}

async def test_async_generator_mock():
    mock_agent = MagicMock()
    mock_agent.run_async = fake_agent_run  # assign the async generator

    events = []
    async for event in mock_agent.run_async():
        events.append(event)

    assert len(events) == 3
    assert events[-1]["type"] == "response"


# Option 2: AsyncMock with __aiter__ for an object that's iterated
async def test_async_iterable_mock():
    events = [
        {"type": "start"},
        {"type": "response", "content": "hello"},
    ]

    # Create something that works with `async for`
    mock_stream = MagicMock()
    mock_stream.__aiter__.return_value = async_iter(events)

    collected = []
    async for event in mock_stream:
        collected.append(event)
    assert collected == events


# Helper: convert a list to an async iterator
async def async_iter(items):
    for item in items:
        yield item


# Option 3: Reusable async generator factory for tests — Recommended for ADK
# Place this in your project's conftest.py so all test files can use it.
def make_async_gen(*items):
    """Create an async generator function that yields the given items."""
    async def _gen(*args, **kwargs):
        for item in items:
            yield item
    return _gen

async def test_with_factory():
    mock_agent = MagicMock()
    mock_agent.run_async = make_async_gen(
        {"type": "start"},
        {"type": "tool_call", "tool": "search"},
        {"type": "end", "content": "done"},
    )

    events = [e async for e in mock_agent.run_async()]
    assert len(events) == 3
```

---

### 10. Mocking Context Managers

#### Sync Context Manager (`with`)

```python
from unittest.mock import MagicMock, patch

# MagicMock supports `with` out of the box
def test_context_manager():
    mock_file = MagicMock()
    mock_file.__enter__.return_value = mock_file
    mock_file.__exit__.return_value = False
    mock_file.read.return_value = "file contents"

    with mock_file as f:
        data = f.read()
    assert data == "file contents"

# Easier: patch open()
@patch("builtins.open", MagicMock())
def test_file_read():
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = "data"
    with patch("builtins.open", mock_open):
        with open("test.txt") as f:
            assert f.read() == "data"

# Easiest: use mock_open helper
from unittest.mock import mock_open

@patch("builtins.open", mock_open(read_data="file contents"))
def test_file_read_easy():
    with open("test.txt") as f:
        assert f.read() == "file contents"
```

#### Async Context Manager (`async with`)

```python
from unittest.mock import AsyncMock, MagicMock

# For ADK: mocking session services, MCP connections, etc.
# Place make_async_context_manager in your project's conftest.py — it's reusable
# across all ADK tests that need to mock async context managers.
def make_async_context_manager(return_value=None):
    """Helper to create a mock async context manager."""
    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=return_value or mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock

async def test_async_context_manager():
    mock_session = MagicMock()
    mock_session.id = "session-123"

    mock_service = make_async_context_manager(return_value=mock_session)

    async with mock_service as session:
        assert session.id == "session-123"

    mock_service.__aenter__.assert_awaited_once()
    mock_service.__aexit__.assert_awaited_once()


# Real-world example: mocking an MCP toolset connection
async def test_mcp_toolset():
    mock_tools = [MagicMock(name="search"), MagicMock(name="browse")]

    mock_toolset = MagicMock()
    mock_toolset.__aenter__ = AsyncMock(return_value=mock_toolset)
    mock_toolset.__aexit__ = AsyncMock(return_value=False)
    mock_toolset.get_tools = AsyncMock(return_value=mock_tools)

    async with mock_toolset as ts:
        tools = await ts.get_tools()
        assert len(tools) == 2
```

---

### 11. Mocking Properties and Attributes

#### Mocking a Property

```python
from unittest.mock import PropertyMock, patch

class Agent:
    @property
    def name(self) -> str:
        return "real_agent"

    @property
    def is_ready(self) -> bool:
        return self._check_readiness()

# Mock a property on a class
def test_property_mock():
    with patch.object(Agent, "name", new_callable=PropertyMock) as mock_name:
        mock_name.return_value = "mocked_agent"
        agent = Agent()
        assert agent.name == "mocked_agent"
        mock_name.assert_called()

# Mock a read-only property
def test_readonly_property():
    with patch.object(Agent, "is_ready", new_callable=PropertyMock) as mock_ready:
        mock_ready.return_value = True
        agent = Agent()
        assert agent.is_ready is True
```

#### Setting Attributes Directly on Mocks

```python
from unittest.mock import MagicMock

# Sometimes you just set attributes directly (simpler than PropertyMock)
mock_agent = MagicMock()
mock_agent.name = "test_agent"
mock_agent.model = "gemini-2.5-flash"
mock_agent.sub_agents = []

assert mock_agent.name == "test_agent"
# Note: these won't track access like PropertyMock does
```

#### configure_mock — Set Multiple Attributes at Once

```python
mock_config = MagicMock()
mock_config.configure_mock(**{
    "model": "gemini-2.5-flash",
    "temperature": 0.7,
    "max_tokens": 1024,
    "generate.return_value": "response",
    "generate_stream.return_value": iter(["chunk1", "chunk2"]),
})

assert mock_config.model == "gemini-2.5-flash"
assert mock_config.generate() == "response"
```

---

### 12. Mocking Class Hierarchies and ABCs

#### Mocking Abstract Base Classes

```python
from abc import ABC, abstractmethod
from unittest.mock import MagicMock, AsyncMock, create_autospec

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def run_async(self, *, args: dict, tool_context: "ToolContext") -> str: ...

# You can't instantiate an ABC directly, but Mock doesn't care:
mock_tool = MagicMock(spec=BaseTool)
mock_tool.name = "mock_search"
mock_tool.run_async = AsyncMock(return_value="search results")

# Or use create_autospec for full signature checking
mock_tool = create_autospec(BaseTool, instance=True)
mock_tool.name = "mock_search"
mock_tool.run_async.return_value = "search results"  # autospec makes this async
```

#### Mocking the Constructor (return_value on the class mock)

```python
from unittest.mock import patch, MagicMock

class LlmClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        return "real response"

@patch("my_module.LlmClient")
def test_constructor_mock(MockLlmClient):
    # MockLlmClient is a mock of the CLASS itself
    # MockLlmClient() returns MockLlmClient.return_value (the INSTANCE mock)
    instance = MockLlmClient.return_value
    instance.generate.return_value = "mocked!"

    # Code under test creates a new LlmClient
    client = LlmClient("fake-key")  # returns the mock instance
    assert client.generate("hello") == "mocked!"

    MockLlmClient.assert_called_once_with("fake-key")
```

#### Spying — Wrapping a Real Object

```python
from unittest.mock import patch

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

# wraps= delegates to the real object but still tracks calls
def test_spy():
    real_calc = Calculator()

    with patch.object(Calculator, "add", wraps=real_calc.add) as spy:
        result = real_calc.add(2, 3)
        assert result == 5                    # real behavior
        spy.assert_called_once_with(2, 3)    # but tracked!
```

**Java equivalent:** `Mockito.spy(realObject)`

---

### 13. Parametrized Tests

```python
import pytest

# Like JUnit's @ParameterizedTest + @ValueSource
@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("", 0),
    ("world!", 6),
])
def test_string_length(input, expected):
    assert len(input) == expected

# Multiple parameters
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_add(a, b, expected):
    assert a + b == expected

# Parametrize with IDs for readable output
@pytest.mark.parametrize("query,expected_tool", [
    pytest.param("search for cats", "web_search", id="search-query"),
    pytest.param("what time is it", "clock", id="time-query"),
    pytest.param("calculate 2+2", "calculator", id="math-query"),
], )
async def test_tool_selection(query, expected_tool):
    tool = await select_tool(query)
    assert tool.name == expected_tool

# Parametrize with marks (e.g., expected failures)
@pytest.mark.parametrize("input", [
    "valid_input",
    pytest.param("edge_case", marks=pytest.mark.xfail),
    pytest.param("slow_input", marks=pytest.mark.slow),
])
def test_process(input):
    process(input)

# Combining parametrize decorators (cartesian product)
@pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-2.5-pro"])
@pytest.mark.parametrize("temperature", [0.0, 0.5, 1.0])
async def test_model_configs(model, temperature):
    # This runs 2 × 3 = 6 test cases
    result = await generate(model=model, temperature=temperature)
    assert result is not None
```

---

## ADK in Practice

#### Testing an ADK-Style Agent

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

# Simplified ADK-like types for illustration
class Event:
    def __init__(self, author: str, content: str, tool_call: dict | None = None):
        self.author = author
        self.content = content
        self.tool_call = tool_call

class InvocationContext:
    def __init__(self, session, agent, services):
        self.session = session
        self.agent = agent
        self.services = services


# --- Fixture: reusable mock context ---
@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=InvocationContext)
    ctx.session = MagicMock()
    ctx.session.state = {}
    ctx.session.events = []
    ctx.agent = MagicMock()
    ctx.agent.name = "test_agent"
    ctx.services = MagicMock()
    ctx.services.session_service = AsyncMock()
    return ctx


# --- Test: agent produces expected events ---
async def test_agent_yields_events(mock_ctx):
    agent = MySearchAgent(model="gemini-2.5-flash")

    with patch.object(agent, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "The answer is 42"

        events = [e async for e in agent.run_async(mock_ctx)]

    assert len(events) >= 1
    assert events[-1].content == "The answer is 42"
    mock_llm.assert_awaited_once()


# --- Test: agent calls the right tool ---
async def test_agent_selects_correct_tool(mock_ctx):
    mock_ctx.session.state["query"] = "weather in Tokyo"
    agent = MyAgent()

    with patch.object(agent, "execute_tool", new_callable=AsyncMock) as mock_tool:
        mock_tool.return_value = {"temperature": "15°C"}

        events = [e async for e in agent.run_async(mock_ctx)]

    # Verify the tool was called with expected arguments
    mock_tool.assert_awaited_once()
    call_args = mock_tool.await_args
    assert call_args.kwargs["tool_name"] == "weather_api"
    assert "Tokyo" in str(call_args)


# --- Test: agent handles errors gracefully ---
async def test_agent_handles_llm_error(mock_ctx):
    agent = MyAgent()

    with patch.object(agent, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = RuntimeError("API rate limit exceeded")

        events = [e async for e in agent.run_async(mock_ctx)]

    # Agent should yield an error event, not crash
    assert any("error" in e.content.lower() for e in events)


# --- Test: state updates ---
async def test_agent_updates_session_state(mock_ctx):
    mock_ctx.session.state = {"counter": 0}
    agent = CounterAgent()

    events = [e async for e in agent.run_async(mock_ctx)]

    assert mock_ctx.session.state["counter"] == 1
```

#### Testing Callbacks

```python
async def test_before_agent_callback():
    callback = AsyncMock(return_value=None)  # None = don't skip agent

    agent = MagicMock()
    agent.before_agent_callback = callback

    # Simulate runner calling the callback
    result = await agent.before_agent_callback(mock_ctx)

    assert result is None  # agent should proceed
    callback.assert_awaited_once_with(mock_ctx)


async def test_callback_can_skip_agent():
    # If before_agent_callback returns an Event, the agent is skipped
    skip_event = Event(author="callback", content="Skipped by policy")
    callback = AsyncMock(return_value=skip_event)

    agent = MagicMock()
    agent.before_agent_callback = callback

    result = await agent.before_agent_callback(mock_ctx)
    assert result.content == "Skipped by policy"
```

#### Testing Tool Schema Generation

```python
import inspect
from typing import get_type_hints

def test_tool_schema_generation():
    """Verify that a tool function's type hints produce the correct schema."""

    async def search_web(query: str, max_results: int = 5) -> list[str]:
        """Search the web for information.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
        """
        ...

    hints = get_type_hints(search_web)
    sig = inspect.signature(search_web)

    # Verify type hints are correctly read
    assert hints["query"] is str
    assert hints["max_results"] is int
    assert hints["return"] == list[str]
    assert sig.parameters["max_results"].default == 5

    # Verify schema generation produces correct structure
    # Build a simple schema from the signature (mirrors ADK's approach via Pydantic)
    properties = {}
    required = []
    for param_name, param in sig.parameters.items():
        properties[param_name] = {"type": str(hints.get(param_name, str))}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    assert "query" in required
    assert "max_results" not in required  # has default=5
    assert set(properties.keys()) == {"query", "max_results"}
```

---

## Common Mistakes

#### Mistake 1: Mocking Everything

```python
# ❌ BAD: Testing mock behavior, not real code
async def test_over_mocked():
    mock_agent = AsyncMock()
    mock_agent.run.return_value = "result"
    result = await mock_agent.run("query")
    assert result == "result"
    # This test proves... nothing. You're testing the mock itself.

# ✅ GOOD: Mock only external dependencies, test real logic
async def test_real_logic():
    agent = MyAgent()
    with patch.object(agent, "_call_external_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = {"data": "value"}
        result = await agent.process("query")  # REAL logic runs
        assert result.formatted_output == "Processed: value"
```

#### Mistake 2: Misunderstanding patch with async functions

Since Python 3.8, `patch()` auto-detects `async def` targets and creates an
`AsyncMock` automatically. You do NOT need `new_callable=AsyncMock` when
patching a function that is already defined as `async def`:

```python
# ✅ Works automatically (Python 3.8+): patch detects the async target
@patch("my_module.async_function")  # auto-creates AsyncMock for async def targets
async def test_auto_detected(mock_func):
    mock_func.return_value = "result"
    result = await mock_func()  # works!

# When DO you need new_callable=AsyncMock?
# Only when patching a NON-async attribute that you want to behave as async:
@patch("my_module.some_attribute", new_callable=AsyncMock)
async def test_explicit(mock_func):
    mock_func.return_value = "result"
    result = await mock_func()  # works!
```

#### Mistake 3: Not Using spec

```python
# ❌ BAD: typos silently pass
mock = Mock()
mock.genrate("hello")  # typo, but no error!

# ✅ GOOD: spec catches typos
mock = Mock(spec=LlmClient)
mock.genrate("hello")  # AttributeError: Mock object has no attribute 'genrate'
```

#### Mistake 4: Testing Implementation Instead of Behavior

```python
# ❌ BAD: brittle test tied to exact implementation order
async def test_brittle():
    with patch("my_agent.step1") as m1, patch("my_agent.step2") as m2:
        await run_agent("query")
        # `assert_called_before` does NOT exist on Mock objects — this will AttributeError

# ✅ CORRECT: check call ordering with assert_has_calls (if you truly need ordering)
from unittest.mock import call, Mock

async def test_with_ordering():
    parent = Mock()
    parent.step1 = Mock(return_value="a")
    parent.step2 = Mock(return_value="b")

    with patch("my_agent.step1", parent.step1), patch("my_agent.step2", parent.step2):
        await run_agent("query")
        # assert_has_calls checks both presence and order
        parent.assert_has_calls([call.step1("query"), call.step2("a")])

# ✅ BEST: test observable outputs, not implementation order
async def test_behavior():
    events = [e async for e in agent.run_async(ctx)]
    assert events[-1].content == "expected response"
    assert ctx.session.state["result"] == "expected value"
```

#### Mistake 5: Shared Mutable Mock State Between Tests

```python
# ❌ BAD: module-level mock shared between tests
shared_mock = Mock(return_value=42)

def test_a():
    shared_mock()
    shared_mock.assert_called_once()  # passes

def test_b():
    shared_mock()
    shared_mock.assert_called_once()  # FAILS! call_count is now 2

# ✅ GOOD: use fixtures
@pytest.fixture
def fresh_mock():
    return Mock(return_value=42)

def test_a(fresh_mock):
    fresh_mock()
    fresh_mock.assert_called_once()  # passes

def test_b(fresh_mock):
    fresh_mock()
    fresh_mock.assert_called_once()  # passes (fresh instance)
```

---

## Quick Reference Card

```
Mock()              Basic mock, accepts any call
MagicMock()         Mock + magic methods (__len__, __str__, etc.)
AsyncMock()         Mock that returns coroutines (for async def)

patch("a.b.c")      Replace a.b.c during test
patch.object(obj, "attr")  Replace obj.attr during test
patch.dict(d, values)      Temporarily modify a dict
patch.multiple("mod", a=Mock(), b=Mock())  Patch several at once

m.return_value       What m() returns
m.side_effect        Exception, list of returns, or callable
m.spec / spec_set    Restrict mock to real interface
autospec=True        Full signature checking

m.assert_called()                Called at least once
m.assert_called_once()           Called exactly once
m.assert_called_with(args)       Last call matches
m.assert_awaited_once_with(args) Async: last await matches
m.call_count                     Total calls
m.call_args_list                 All calls recorded
ANY                              Matches anything in assertions
call(args)                       Represents a single call for matching

create_autospec(cls)  Auto-generate spec'd mock from class
PropertyMock()        Mock a @property
mock_open()           Mock file open()
```

---

