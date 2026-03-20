# Python Testing & Mocking — Guide

> **ADK relevance:** Testing agents, tools, callbacks, and async generators requires specific mocking patterns | **Estimated time:** 3-4 hours

## At a Glance

```
+------------------------------------------------------------------+
|              Python Testing & Mocking Toolkit                      |
|                                                                    |
|  pytest                                                            |
|    +-- Assertions      Plain assert (no assertEquals needed)      |
|    +-- Fixtures         @pytest.fixture (DI for tests)            |
|    +-- Parametrize      @pytest.mark.parametrize                  |
|    +-- Async            @pytest.mark.asyncio                      |
|                                                                    |
|  unittest.mock                                                     |
|    +-- Mock             Basic mock, accepts any call              |
|    +-- MagicMock        Mock + magic methods (__len__, etc.)      |
|    +-- AsyncMock        For async def functions                   |
|    +-- patch()          Replace objects during test               |
|    +-- spec/autospec    Type-safe mocks (catch typos)             |
|                                                                    |
|  Key Rule: patch WHERE IT'S LOOKED UP, not where defined          |
|  Key Rule: Use AsyncMock for all async functions                  |
|  Key Rule: Use spec= to catch attribute typos                    |
+------------------------------------------------------------------+
```

Every mocking technique you need for ADK agent development. Covers the transition from JUnit/Mockito to pytest/unittest.mock, with special focus on async testing patterns that ADK requires.

## Core Concepts

### [ ] 1. pytest Fundamentals

#### [ ] Java → Python Comparison

```java
// JUnit
public class CalculatorTest {
    @Test
    void testAdd() {
        assertEquals(4, Calculator.add(2, 2));
    }

    @BeforeEach
    void setUp() { /* ... */ }
}
```

```python
# pytest — no class needed, no inheritance, just functions
def test_add():
    assert Calculator.add(2, 2) == 4

# But you CAN use classes for grouping (no inheritance required)
class TestCalculator:
    def test_add(self):
        assert Calculator.add(2, 2) == 4

    def test_subtract(self):
        assert Calculator.subtract(5, 3) == 2
```

#### [ ] Key Differences from JUnit

```python
# pytest uses plain `assert` — no assertEquals, assertTrue, etc.
def test_assertions():
    # Equality
    assert result == expected

    # Truthiness
    assert some_value
    assert not empty_list

    # Containment
    assert "hello" in greeting
    assert key in my_dict

    # Type checking
    assert isinstance(obj, MyClass)

    # Approximate equality (for floats)
    assert result == pytest.approx(3.14, rel=1e-2)

    # Exception testing (like JUnit's assertThrows)
    with pytest.raises(ValueError, match="invalid input"):
        parse_input("bad data")

    # Exception testing — capture and inspect
    with pytest.raises(ValueError) as exc_info:
        parse_input("bad data")
    assert "invalid" in str(exc_info.value)
    assert exc_info.value.args[0] == "invalid input"
```

#### [ ] Test Discovery

```
# pytest auto-discovers tests by convention:
# - Files named test_*.py or *_test.py
# - Functions named test_*
# - Classes named Test* (no __init__ method)
# - Methods named test_* inside Test* classes

# Run tests:
# pytest                          # run all
# pytest tests/test_agent.py      # run one file
# pytest -k "test_search"         # run by name pattern
# pytest -x                       # stop on first failure
# pytest -v                       # verbose output
# pytest --tb=short               # shorter tracebacks
```

---

### [ ] 2. Mock Basics — Mock, MagicMock, AsyncMock

#### [ ] Mock — The Foundation

```python
from unittest.mock import Mock

# Basic mock — accepts any attribute access and any call
m = Mock()
m.foo                    # returns another Mock
m.foo.bar.baz            # chain works infinitely
m(1, 2, 3)              # callable, returns a Mock
m.method(x=10)          # also works

# Mock with a return value
m = Mock(return_value=42)
assert m() == 42
assert m("anything", key="value") == 42  # always returns 42

# Mock with a name (for debugging)
m = Mock(name="llm_client")
print(m)  # <Mock name='llm_client' id='...'>
```

**Java equivalent:** `Mockito.mock(SomeClass.class)` but far more permissive — no class needed.

#### [ ] MagicMock — Mock with Magic Methods

```python
from unittest.mock import MagicMock

# MagicMock pre-configures Python's "magic methods" (__str__, __len__, etc.)
m = MagicMock()

# These work on MagicMock but NOT on plain Mock:
len(m)           # returns 0 (default)
str(m)           # returns a string representation
bool(m)          # returns True (default)
iter(m)          # works (returns iter([]))
m[0]             # works (__getitem__)
m[0] = "value"   # works (__setitem__)

# Configure magic methods
m.__len__.return_value = 5
assert len(m) == 5

m.__str__.return_value = "hello"
assert str(m) == "hello"

m.__iter__.return_value = iter([1, 2, 3])
assert list(m) == [1, 2, 3]

# MagicMock is the default choice for most mocking needs
# Use plain Mock only when you specifically want magic methods to fail
```

#### [ ] AsyncMock — For Async Functions

```python
from unittest.mock import AsyncMock

# AsyncMock returns a coroutine that resolves to the return_value
m = AsyncMock(return_value={"status": "ok"})

# Must be awaited
result = await m()
assert result == {"status": "ok"}

# Tracks calls just like regular Mock
m.assert_called_once()
m.assert_called_with()

# Critical for ADK: mocking async methods
class MockLlm:
    generate_content = AsyncMock(return_value="LLM response")

result = await MockLlm.generate_content("prompt")
assert result == "LLM response"
```

**When to use which:**

| Type | Use When |
|------|----------|
| `Mock` | Simple return values, no magic methods needed |
| `MagicMock` | Need `len()`, `str()`, iteration, indexing, or `with` statements |
| `AsyncMock` | Mocking `async def` functions or methods |

---

### [ ] 3. Patching — Where and How

Patching temporarily replaces an object during a test. This is the most important mocking technique to understand correctly.

#### [ ] The Golden Rule: Patch Where It's LOOKED UP, Not Where It's DEFINED

```
Mock Patch Target Resolution — Import Graph

my_agents/http_client.py          my_agents/tools/web_search.py
┌────────────────────────┐        ┌────────────────────────────┐
│ def fetch(url): ...    │───────►│ from my_agents.http_client │
│                        │ import │     import fetch            │
│ (DEFINED here)         │        │                            │
└────────────────────────┘        │ async def search_web():    │
                                  │     await fetch(...)       │
                                  │     # ▲ LOOKED UP here     │
                                  └────────────────────────────┘

  patch("my_agents.http_client.fetch")      ← WRONG (patches the definition)
  patch("my_agents.tools.web_search.fetch") ← RIGHT (patches the lookup)

  Why? `from X import Y` copies a reference into the importing module's
  namespace. Patching the original doesn't change the copy.
```

```python
# --- my_agents/tools/web_search.py ---
from my_agents.http_client import fetch   # <-- defined in http_client

async def search_web(query: str) -> list[str]:
    response = await fetch(f"https://api.example.com/search?q={query}")
    return response["results"]

# --- test_web_search.py ---
from unittest.mock import patch, AsyncMock

# WRONG: patching where fetch is defined
@patch("my_agents.http_client.fetch")  # ❌ won't work!
async def test_search():
    ...

# RIGHT: patching where fetch is looked up (in web_search module)
@patch("my_agents.tools.web_search.fetch")  # ✅ correct!
async def test_search(mock_fetch):
    mock_fetch.return_value = {"results": ["result1", "result2"]}
    results = await search_web("python")
    assert results == ["result1", "result2"]
```

**Java equivalent:** This is like Mockito's `@InjectMocks` but manual. Java's DI makes this easier; Python requires you to understand the import graph.

#### [ ] Three Ways to Patch

##### Way 1: Decorator (`@patch`)

```python
from unittest.mock import patch

# The mock is injected as an argument (bottom decorator = first argument)
@patch("my_module.service_b")
@patch("my_module.service_a")
def test_with_decorators(mock_a, mock_b):
    # mock_a replaces my_module.service_a
    # mock_b replaces my_module.service_b
    mock_a.return_value = "a_result"
    mock_b.return_value = "b_result"
    result = my_function()
    assert result == ("a_result", "b_result")
```

##### Way 2: Context Manager (`with patch(...)`)

```python
def test_with_context_manager():
    with patch("my_module.service_a") as mock_a:
        mock_a.return_value = "mocked"
        result = my_function()
        assert result == "mocked"
    # After the `with` block, service_a is restored to original
```

##### Way 3: Manual Start/Stop

```python
def test_manual_patch():
    patcher = patch("my_module.service_a")
    mock_a = patcher.start()
    mock_a.return_value = "mocked"

    try:
        result = my_function()
        assert result == "mocked"
    finally:
        patcher.stop()  # always stop!
```

#### [ ] `patch.object` — Patching a Specific Attribute

```python
from unittest.mock import patch

class LlmClient:
    def generate(self, prompt: str) -> str:
        return "real response"

# Patch a specific method on a class
@patch.object(LlmClient, "generate", return_value="mocked response")
def test_llm(mock_generate):
    client = LlmClient()
    assert client.generate("hello") == "mocked response"
    mock_generate.assert_called_once_with("hello")
```

#### [ ] `patch.dict` — Patching Dictionaries (e.g., Environment Variables)

```python
import os
from unittest.mock import patch

# Patch environment variables
@patch.dict(os.environ, {"API_KEY": "test-key-123", "DEBUG": "true"})
def test_with_env_vars():
    assert os.environ["API_KEY"] == "test-key-123"
    assert os.environ["DEBUG"] == "true"

# Clear the dict and set only these values
@patch.dict(os.environ, {"API_KEY": "test"}, clear=True)
def test_clean_env():
    assert "HOME" not in os.environ  # cleared!
    assert os.environ["API_KEY"] == "test"
```

#### [ ] `patch.multiple` — Patching Multiple Attributes at Once

```python
from unittest.mock import patch, MagicMock

@patch.multiple(
    "my_module",
    service_a=MagicMock(return_value="a"),
    service_b=MagicMock(return_value="b"),
    CONFIG={"debug": True},
)
def test_multiple(**mocks):
    # mocks is a dict: {"service_a": mock, "service_b": mock, "CONFIG": {...}}
    result = my_function()
    assert result == ("a", "b")
```

---

### [ ] 4. side_effect — Dynamic Mock Behavior

`side_effect` is the most powerful Mock feature. It controls what happens when the mock is called.

#### [ ] Raise an Exception

```python
from unittest.mock import Mock

# Like Mockito's thenThrow()
m = Mock(side_effect=ValueError("invalid input"))
with pytest.raises(ValueError, match="invalid input"):
    m()
```

#### [ ] Return Different Values on Successive Calls

```python
# Like Mockito's thenReturn(a).thenReturn(b).thenReturn(c)
m = Mock(side_effect=["first", "second", "third"])
assert m() == "first"
assert m() == "second"
assert m() == "third"
# m()  # raises StopIteration if called again

# Mix returns and exceptions
m = Mock(side_effect=["ok", ValueError("fail"), "recovered"])
assert m() == "ok"
with pytest.raises(ValueError):
    m()
assert m() == "recovered"
```

#### [ ] Custom Logic — A Function as side_effect

```python
# Like Mockito's thenAnswer()
def fake_fetch(url: str) -> dict:
    if "search" in url:
        return {"results": ["r1", "r2"]}
    elif "user" in url:
        return {"name": "you", "role": "developer"}
    raise ValueError(f"Unknown URL: {url}")

m = Mock(side_effect=fake_fetch)
assert m("https://api.com/search?q=test") == {"results": ["r1", "r2"]}
assert m("https://api.com/user/123") == {"name": "you", "role": "developer"}
```

#### [ ] Async side_effect

```python
from unittest.mock import AsyncMock

# Async function as side_effect
async def fake_generate(prompt: str) -> str:
    if "error" in prompt:
        raise RuntimeError("LLM error")
    return f"Response to: {prompt}"

mock_llm = AsyncMock(side_effect=fake_generate)
result = await mock_llm("hello")
assert result == "Response to: hello"

# Successive async returns
mock_llm = AsyncMock(side_effect=["response1", "response2"])
assert await mock_llm() == "response1"
assert await mock_llm() == "response2"
```

#### [ ] side_effect That Also Records Calls (Passthrough)

```python
original_function = some_module.real_function

def spy_side_effect(*args, **kwargs):
    # Do something extra (logging, assertions)
    print(f"Called with: {args}, {kwargs}")
    return original_function(*args, **kwargs)

m = Mock(side_effect=spy_side_effect)
# Now m works like the real function but is tracked
```

---

### [ ] 5. spec and spec_set — Type-Safe Mocks

Without `spec`, mocks accept any attribute. This can hide bugs:

```python
# DANGEROUS: no spec
mock_client = Mock()
mock_client.generat("hello")  # typo! But Mock doesn't care — no error!
mock_client.generat.assert_called()  # passes! Bug hidden.
```

#### [ ] spec — Mock Follows an Interface

```python
class LlmClient:
    def generate(self, prompt: str) -> str: ...
    def generate_stream(self, prompt: str): ...

# spec restricts the mock to only have attributes that LlmClient has
mock_client = Mock(spec=LlmClient)
mock_client.generate("hello")       # ✅ works
mock_client.generat("hello")        # ❌ AttributeError! Typo caught!
mock_client.nonexistent             # ❌ AttributeError!

# Works with patch too
@patch("my_module.LlmClient", spec=LlmClient)
def test_with_spec(MockLlmClient):
    instance = MockLlmClient.return_value
    instance.generate.return_value = "mocked"
    ...
```

#### [ ] spec_set — Even Stricter (No Setting New Attributes)

```python
mock_client = Mock(spec_set=LlmClient)
mock_client.generate.return_value = "ok"   # ✅ fine
mock_client.new_attribute = "value"         # ❌ AttributeError!
```

#### [ ] auto-spec with patch

```python
# autospec=True creates a mock that matches the FULL interface,
# including method signatures
@patch("my_module.LlmClient", autospec=True)
def test_with_autospec(MockLlmClient):
    instance = MockLlmClient.return_value
    instance.generate("hello")              # ✅ correct args
    instance.generate("hello", "extra")     # ❌ TypeError! Wrong number of args
    instance.generate(prompt="hello")       # ✅ keyword args work too
```

**Java equivalent:** `Mockito.mock(LlmClient.class)` is always spec'd by default because Java is statically typed. Python needs `spec` to get the same safety.

---

### [ ] 6. Assertion Methods — Verifying Calls

```python
from unittest.mock import Mock, call

m = Mock()

# --- Was it called? ---
m(1, 2, key="value")

m.assert_called()                         # called at least once
m.assert_called_once()                    # called exactly once
m.assert_called_with(1, 2, key="value")   # last call matches
m.assert_called_once_with(1, 2, key="value")  # called once AND args match

# --- Was it NOT called? ---
m2 = Mock()
m2.assert_not_called()                    # never called

# --- Inspect call history ---
m.call_count                              # int: number of times called
m.call_args                               # last call: call(1, 2, key="value")
m.call_args_list                          # all calls: [call(1, 2, key="value")]
m.call_args.args                          # (1, 2)
m.call_args.kwargs                        # {"key": "value"}

# --- Multiple calls with assert_has_calls ---
m = Mock()
m(1)
m(2)
m(3)

# Assert these calls happened in order
m.assert_has_calls([call(1), call(2), call(3)])

# Assert these calls happened (any order)
m.assert_has_calls([call(3), call(1)], any_order=True)

# --- assert_any_call: at least one call matches ---
m.assert_any_call(2)  # ✅ m(2) happened at some point

# --- Reset mock ---
m.reset_mock()
m.assert_not_called()  # fresh start
m.call_count == 0
```

#### [ ] Using `call` for Nested/Chained Assertions

```python
from unittest.mock import Mock, call

m = Mock()
m.agent.run("query1")
m.agent.run("query2")
m.agent.stop()

# Assert chain of calls
m.agent.run.assert_has_calls([
    call("query1"),
    call("query2"),
])
m.agent.stop.assert_called_once()
```

#### [ ] Using `ANY` for Partial Matching

```python
from unittest.mock import ANY

m = Mock()
m.log("error", "Something failed", timestamp=1234567890)

# Don't care about timestamp
m.log.assert_called_with("error", "Something failed", timestamp=ANY)

# Don't care about the second argument either
m.log.assert_called_with("error", ANY, timestamp=ANY)
```

---

### [ ] 7. Fixtures — Dependency Injection for Tests

#### [ ] Basic Fixtures

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

# Fixtures are pytest's version of @BeforeEach + dependency injection
@pytest.fixture
def mock_session():
    session = MagicMock()
    session.id = "test-session-123"
    session.state = {"user_name": "you"}
    session.events = []
    return session

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate_content_async.return_value = "LLM response"
    return llm

# Fixtures are injected by parameter name
def test_agent_uses_session(mock_session):
    assert mock_session.id == "test-session-123"

async def test_llm_call(mock_llm):
    result = await mock_llm.generate_content_async("hello")
    assert result == "LLM response"
```

#### [ ] Fixture Scopes

```python
# function (default) — created fresh for each test
@pytest.fixture(scope="function")
def fresh_mock():
    return Mock()

# class — shared across all tests in a class
@pytest.fixture(scope="class")
def shared_client():
    return create_test_client()

# module — shared across all tests in a file
@pytest.fixture(scope="module")
def db_connection():
    conn = create_connection()
    yield conn          # yield = setup + teardown
    conn.close()        # this runs after all tests in the module

# session — shared across the entire test run
@pytest.fixture(scope="session")
def expensive_resource():
    resource = load_large_model()
    yield resource
    resource.cleanup()
```

#### [ ] Fixtures Using Yield (Setup + Teardown)

```python
# Java equivalent: @BeforeEach + @AfterEach combined
@pytest.fixture
def temp_database():
    db = Database.create_temp()    # SETUP
    db.seed_test_data()
    yield db                        # test runs here
    db.drop_all_tables()           # TEARDOWN (always runs, even on failure)
    db.close()
```

#### [ ] conftest.py — Shared Fixtures

```python
# tests/conftest.py — fixtures here are available to ALL tests in the directory
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_invocation_context():
    ctx = MagicMock()
    ctx.session = MagicMock()
    ctx.session.state = {}
    ctx.agent = MagicMock()
    ctx.services = MagicMock()
    ctx.services.session_service = AsyncMock()
    return ctx

@pytest.fixture
def mock_tool_context():
    ctx = MagicMock()
    ctx.state = {}
    ctx.actions = MagicMock()
    return ctx
```

#### [ ] Fixture Composition (Fixtures Using Other Fixtures)

```python
@pytest.fixture
def mock_session():
    return MagicMock(id="session-1", state={}, events=[])

@pytest.fixture
def mock_agent():
    return MagicMock(name="test_agent")

# This fixture depends on the two above
@pytest.fixture
def mock_context(mock_session, mock_agent):
    ctx = MagicMock()
    ctx.session = mock_session
    ctx.agent = mock_agent
    return ctx

def test_something(mock_context):
    # mock_context has mock_session and mock_agent already wired in
    assert mock_context.session.id == "session-1"
```

---

### [ ] 8. Testing Async Code

#### [ ] Setup: pytest-asyncio

```bash
pip install pytest-asyncio
```

```python
# pyproject.toml — configure asyncio mode
# [tool.pytest.ini_options]
# asyncio_mode = "auto"    # auto-detect async tests (recommended)
```

#### [ ] Basic Async Tests

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

#### [ ] Patching Async Functions

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

#### [ ] AsyncMock-Specific Assertions

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

#### [ ] Testing asyncio.gather and Concurrency

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

#### [ ] Testing Timeouts

```python
async def test_timeout_handling():
    mock_tool = AsyncMock(side_effect=asyncio.TimeoutError())

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(mock_tool(), timeout=1.0)

# Or test your own timeout wrapper
async def test_graceful_timeout():
    slow_mock = AsyncMock(side_effect=lambda: asyncio.sleep(10))

    result = await run_with_timeout(slow_mock, timeout=0.1)
    assert result == {"error": "timeout"}
```

---

### [ ] 9. Mocking Generators and Async Generators

#### [ ] Mocking Sync Generators

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

#### [ ] Mocking Async Generators (Critical for ADK)

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


# Option 3: Reusable async generator factory for tests
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

### [ ] 10. Mocking Context Managers

#### [ ] Sync Context Manager (`with`)

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

#### [ ] Async Context Manager (`async with`)

```python
from unittest.mock import AsyncMock, MagicMock

# For ADK: mocking session services, MCP connections, etc.
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

### [ ] 11. Mocking Properties and Attributes

#### [ ] Mocking a Property

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

#### [ ] Setting Attributes Directly on Mocks

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

#### [ ] configure_mock — Set Multiple Attributes at Once

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

### [ ] 12. Mocking Class Hierarchies and ABCs

#### [ ] Mocking Abstract Base Classes

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

#### [ ] Mocking the Constructor (return_value on the class mock)

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

#### [ ] Spying — Wrapping a Real Object

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

### [ ] 13. Parametrized Tests

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

#### [ ] Testing an ADK-Style Agent

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

#### [ ] Testing Callbacks

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

#### [ ] Testing Tool Schema Generation

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

    assert hints["query"] is str
    assert hints["max_results"] is int
    assert hints["return"] == list[str]
    assert sig.parameters["max_results"].default == 5
```

---

## Common Mistakes

#### [ ] Mistake 1: Mocking Everything

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

#### [ ] Mistake 2: Misunderstanding patch with async functions

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

#### [ ] Mistake 3: Not Using spec

```python
# ❌ BAD: typos silently pass
mock = Mock()
mock.genrate("hello")  # typo, but no error!

# ✅ GOOD: spec catches typos
mock = Mock(spec=LlmClient)
mock.genrate("hello")  # AttributeError: Mock object has no attribute 'genrate'
```

#### [ ] Mistake 4: Testing Implementation Instead of Behavior

```python
# ❌ BAD: brittle test tied to exact implementation
async def test_brittle():
    with patch("my_agent.step1") as m1, patch("my_agent.step2") as m2:
        await run_agent("query")
        # NOTE: `assert_called_before` does NOT exist on Mock objects.
        # If you need ordering, use mock_parent.assert_has_calls([call...])
        # with the calls in expected order. But usually ordering tests
        # are brittle — prefer testing observable outputs instead.

# ✅ GOOD: test the observable output
async def test_behavior():
    events = [e async for e in agent.run_async(ctx)]
    assert events[-1].content == "expected response"
    assert ctx.session.state["result"] == "expected value"
```

#### [ ] Mistake 5: Shared Mutable Mock State Between Tests

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

