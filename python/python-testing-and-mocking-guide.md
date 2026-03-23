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

### 1. pytest Fundamentals

#### Java → Python Comparison

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

#### Key Differences from JUnit

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

#### Test Discovery

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

### 2. Mock Basics — Mock, MagicMock, AsyncMock

#### Mock — The Foundation

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

#### MagicMock — Mock with Magic Methods

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

#### AsyncMock — For Async Functions

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

### 3. Patching — Where and How

Patching temporarily replaces an object during a test. This is the most important mocking technique to understand correctly.

#### The Golden Rule: Patch Where It's LOOKED UP, Not Where It's DEFINED

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

#### Three Ways to Patch

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

#### `patch.object` — Patching a Specific Attribute

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

#### `patch.dict` — Patching Dictionaries (e.g., Environment Variables)

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

#### `patch.multiple` — Patching Multiple Attributes at Once

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

### 4. side_effect — Dynamic Mock Behavior

`side_effect` is the most powerful Mock feature. It controls what happens when the mock is called.

#### Raise an Exception

```python
from unittest.mock import Mock

# Like Mockito's thenThrow()
m = Mock(side_effect=ValueError("invalid input"))
with pytest.raises(ValueError, match="invalid input"):
    m()
```

#### Return Different Values on Successive Calls

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

#### Custom Logic — A Function as side_effect

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

#### Async side_effect

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

#### side_effect That Also Records Calls (Passthrough)

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

### 5. spec and spec_set — Type-Safe Mocks

Without `spec`, mocks accept any attribute. This can hide bugs:

```python
# DANGEROUS: no spec
mock_client = Mock()
mock_client.generat("hello")  # typo! But Mock doesn't care — no error!
mock_client.generat.assert_called()  # passes! Bug hidden.
```

#### spec — Mock Follows an Interface

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

#### spec_set — Even Stricter (No Setting New Attributes)

```python
mock_client = Mock(spec_set=LlmClient)
mock_client.generate.return_value = "ok"   # ✅ fine
mock_client.new_attribute = "value"         # ❌ AttributeError!
```

#### auto-spec with patch

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

### 6. Assertion Methods — Verifying Calls

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

#### Using `call` for Nested/Chained Assertions

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

#### Using `ANY` for Partial Matching

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

### 7. Fixtures — Dependency Injection for Tests

#### Basic Fixtures

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

#### Fixture Scopes

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

#### Fixtures Using Yield (Setup + Teardown)

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

#### conftest.py — Shared Fixtures

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

#### Fixture Composition (Fixtures Using Other Fixtures)

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

#### Fixture Chain with Teardown

Use `yield` in a fixture to run cleanup code after the test:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
async def mock_session_service():
    """Session service fixture with setup and teardown."""
    service = AsyncMock()
    service.sessions = {}

    # Setup: create a test session
    session = MagicMock()
    session.id = "test-session-1"
    session.state = {}
    service.get_or_create_session = AsyncMock(return_value=session)
    service.save_session = AsyncMock()

    yield service  # test runs here

    # Teardown: verify session was saved
    service.save_session.assert_awaited()


@pytest.mark.asyncio
async def test_agent_persists_session(mock_session_service):
    session = await mock_session_service.get_or_create_session("user-1", "app-1")
    session.state["result"] = "done"
    await mock_session_service.save_session(session)
    assert session.state["result"] == "done"
```

---


> **Continued in [python-testing-advanced.md](python-testing-advanced.md)** — async testing, mocking generators and async generators, context managers, properties, class hierarchies, parametrized tests, ADK testing patterns, and common mistakes.
