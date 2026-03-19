# Python Testing & Mocking Guide

> **For:** Experienced Java developers transitioning to Python and ADK
> **Goal:** Master pytest and unittest.mock for testing ADK agents

---

pytest is Python's dominant test framework, combining the roles that JUnit and Mockito play separately in Java. Where Java requires annotations, base classes, and assertion libraries (AssertJ, Hamcrest), pytest uses plain functions, plain `assert` statements, and a powerful fixture system for dependency injection. Combined with Python's built-in `unittest.mock` module, you get a complete test toolkit with zero external mocking libraries.

---

## pytest Fundamentals

### Test Discovery

pytest auto-discovers tests by naming convention -- no registration or annotations needed:

```
# Files:    test_*.py  or  *_test.py
# Functions: test_*
# Classes:   Test*  (no __init__ method)
# Methods:   test_* inside Test* classes
```

```python
# test_weather.py -- pytest finds this automatically
def test_temperature_conversion():
    assert celsius_to_fahrenheit(0) == 32

class TestWeatherAgent:
    def test_parses_city(self):
        assert parse_city("weather in London") == "London"
```

**conftest.py** is pytest's convention for shared fixtures and hooks. Any file named `conftest.py` automatically applies to all tests in its directory and subdirectories -- no imports needed.

### Assertions

pytest uses plain `assert` -- no `assertEquals`, `assertTrue`, or `assertThat`:

```python
assert result == expected               # equality
assert "London" in response             # containment
assert score == pytest.approx(0.95)     # float comparison
with pytest.raises(ValueError, match="invalid city"):
    get_weather("!!!!")                 # exception testing
```

When an `assert` fails, pytest introspects the expression and shows a detailed diff.

### Fixtures

Fixtures replace JUnit's `@BeforeEach` and constructor injection. Injected by parameter name:

```python
@pytest.fixture
def sample_session():
    return {"id": "sess-001", "state": {}, "events": []}

def test_session_starts_empty(sample_session):
    assert sample_session["events"] == []
```

Scopes: `function` (default, like `@BeforeEach`), `module` (per file), `session` (once per run, like `@BeforeAll`).

**Yield fixtures** provide setup and teardown in one place:

```python
@pytest.fixture
def temp_database():
    db = create_test_db()       # SETUP
    yield db                     # test runs here
    db.drop_all()               # TEARDOWN (always runs)
```

**autouse** fixtures run for every test without being requested:

```python
@pytest.fixture(autouse=True)
def fake_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-tests")
```

### Parametrize

Like JUnit's `@ParameterizedTest` -- run the same test with different inputs:

```python
@pytest.mark.parametrize("city,expected", [
    ("London", "UK"),
    ("Tokyo", "Japan"),
    pytest.param("Paris", "France", id="french-capital"),
])
def test_city_lookup(city, expected):
    assert lookup_country(city) == expected
```

### Markers and Test Selection

```python
@pytest.mark.slow                                       # custom marker
def test_full_agent_pipeline(): ...

@pytest.mark.skipif(not has_api_key(), reason="No API key")
def test_live_llm_call(): ...
```

Run selectively: `pytest -k "test_weather"` (name pattern), `pytest -m "not slow"` (skip marked), `pytest -x` (stop on first failure).

---

## Async Testing

### pytest-asyncio Plugin

ADK is async-first -- every agent produces `AsyncGenerator[Event, None]`. Install `pytest-asyncio` and configure:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### @pytest.mark.asyncio Decorator

With `asyncio_mode = "auto"`, async tests just work. Otherwise mark explicitly:

```python
@pytest.mark.asyncio
async def test_session_creation():
    service = InMemorySessionService()
    session = await service.create_session(app_name="test", user_id="user-1")
    assert session.id is not None
```

### Async Fixtures

```python
@pytest.fixture
async def live_session():
    service = InMemorySessionService()
    session = await service.create_session(app_name="test", user_id="user-1")
    yield session
```

### Testing AsyncGenerators (Critical for ADK)

ADK agents yield events via `AsyncGenerator[Event, None]`. Collect with `async for`:

```python
@pytest.mark.asyncio
async def test_agent_event_stream():
    mock = MockModel.create(responses=["Hello!"])
    agent = Agent(name="greeter", model=mock)
    ctx = await create_invocation_context(agent, user_content="Hi")

    events = [e async for e in agent.run_async(ctx)]
    assert len(events) >= 1
    assert events[-1].content.parts[0].text == "Hello!"
```

To mock an async generator, assign a real async generator function:

```python
async def fake_run(*args, **kwargs):
    yield Event(author="agent", content="step 1")
    yield Event(author="agent", content="step 2")

mock_agent = MagicMock()
mock_agent.run_async = fake_run
events = [e async for e in mock_agent.run_async()]
```

---

## Mocking

### unittest.mock (Mock, MagicMock, AsyncMock)

Python's `unittest.mock` is built-in. Three core classes:

| Class | When to use |
|---|---|
| `Mock` | Simple stubs, no magic methods |
| `MagicMock` | Need `len()`, `iter()`, `with` statements |
| `AsyncMock` | Mocking `async def` methods |

```python
from unittest.mock import Mock, MagicMock, AsyncMock

m = Mock(return_value=42)
assert m("anything") == 42

m = AsyncMock(return_value={"temp": 20})
result = await m("London")         # must await
assert result == {"temp": 20}
```

### patch and patch.object

`patch` temporarily replaces an object during a test. **Patch where the name is looked up, not where it is defined:**

```python
# my_tools/weather.py
from my_tools.http_client import fetch     # fetch is looked up HERE

# test_weather.py -- patch the lookup site
@patch("my_tools.weather.fetch", new_callable=AsyncMock)
async def test_get_weather(mock_fetch):
    mock_fetch.return_value = {"temp": 20}
    result = await get_weather("London")
    assert result == {"temp": 20}
```

Also available: context manager form (`with patch(...) as m`) and `patch.object(cls, "attr")`.

### side_effect for Sequences

```python
# Different values on successive calls (like thenReturn().thenReturn())
m = Mock(side_effect=["first", "second", "third"])
assert m() == "first"
assert m() == "second"

# Raise an exception
m = Mock(side_effect=ValueError("bad input"))

# Custom logic (like Mockito's thenAnswer)
def fake_fetch(url: str) -> dict:
    if "weather" in url:
        return {"temp": 20}
    raise ValueError(f"Unknown: {url}")

m = Mock(side_effect=fake_fetch)
```

### spec and spec_set for Type Safety

```python
# Without spec: typos go undetected
mock_client = Mock()
mock_client.genrate("hello")        # typo -- no error!

# With spec: restricted to real attributes
mock_client = Mock(spec=LlmClient)
mock_client.genrate("hello")        # AttributeError -- typo caught

# spec_set: also prevents setting new attributes
mock_client = Mock(spec_set=LlmClient)
mock_client.new_attr = "x"          # AttributeError
```

---

## ADK-Specific Testing Patterns

### MockModel for Deterministic LLM Responses

`MockModel` replaces the real LLM with canned responses. It extends `BaseLlm`, plugging into the same slot Gemini or Claude would occupy:

```python
from tests.unittests.testing_utils import MockModel, InMemoryRunner, simplify_events
from google.adk.agents.llm_agent import Agent
from google.genai.types import Part

# Simple text response
mock = MockModel.create(responses=["Hello!"])
agent = Agent(name="greeter", model=mock)
runner = InMemoryRunner(agent)
assert simplify_events(runner.run("Hi")) == [("greeter", "Hello!")]

# Tool call then text (each entry = one LLM invocation)
mock = MockModel.create(responses=[
    Part.from_function_call(name="get_weather", args={"city": "London"}),
    "It is sunny in London.",
])

# Error simulation
mock = MockModel.create(responses=[], error=SystemError("API down"))

# Inspect what the model received
assert "Be helpful" in mock.requests[0].config.system_instruction
```

> **Note:** `MockModel` lives in `tests/unittests/testing_utils.py` in the adk-python repo and is not shipped with `pip install google-adk`. Copy it into your project or add the repo to your PYTHONPATH.

### Testing Tools with Mock ToolContext

```python
@pytest.fixture
def mock_tool_context() -> ToolContext:
    ctx = MagicMock(spec=InvocationContext)
    ctx.session = MagicMock(spec=Session)
    ctx.session.state = {"user_name": "Alice"}
    return ToolContext(invocation_context=ctx)

@pytest.mark.asyncio
async def test_greeting_tool(mock_tool_context):
    def greet(name: str, tool_context: ToolContext) -> str:
        return f"Hello {name}"

    tool = FunctionTool(greet)
    result = await tool.run_async(args={"name": "Bob"}, tool_context=mock_tool_context)
    assert result == "Hello Bob"
```

### Testing Agents End-to-End with InMemoryRunner

`InMemoryRunner` auto-wires `InMemorySessionService`, `InMemoryArtifactService`, and `InMemoryMemoryService`:

```python
def test_weather_agent_e2e():
    def get_weather(city: str) -> dict:
        return {"temp": 20}

    mock = MockModel.create(responses=[
        Part.from_function_call(name="get_weather", args={"city": "London"}),
        "20C in London.",
    ])
    agent = Agent(name="weather", model=mock, tools=[get_weather])
    runner = InMemoryRunner(agent)
    assert simplify_events(runner.run("Weather?"))[-1] == ("weather", "20C in London.")
```

### Asserting Event Sequences

Use `simplify_events` for readable assertions (strips internal IDs) and `simplify_contents` for model input:

```python
assert simplify_events(events) == [("agent_name", "response text")]
assert simplify_contents(mock.requests[0].contents) == [("user", "Hello")]
```

### Mocking External API Calls in Tools

Patch the HTTP client at the tool's import site:

```python
@patch("my_tools.httpx.AsyncClient")
async def test_stock_tool(MockClient):
    instance = AsyncMock()
    instance.get.return_value = MagicMock(json=Mock(return_value={"price": 150.0}))
    instance.__aenter__.return_value = instance
    instance.__aexit__.return_value = False
    MockClient.return_value = instance

    result = await fetch_stock_price("GOOG")
    assert result == {"price": 150.0}
```

---

## Test Organization

### conftest.py for Shared Fixtures

Place reusable fixtures in `tests/conftest.py`. They apply to all tests in the directory without imports:

```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

@pytest.fixture
def mock_tool_context() -> ToolContext:
    ctx = MagicMock(spec=InvocationContext)
    ctx.session = MagicMock(spec=Session)
    ctx.session.state = {}
    return ToolContext(invocation_context=ctx)
```

### Fixture Composition and tmp_path

Fixtures can depend on other fixtures. Use pytest's built-in `tmp_path` for file isolation:

```python
@pytest.fixture
def mock_context(mock_session):       # depends on another fixture
    ctx = MagicMock(spec=InvocationContext)
    ctx.session = mock_session
    return ctx

def test_artifact_storage(tmp_path):  # built-in, unique per test
    (tmp_path / "output.json").write_text('{"ok": true}')
```

---

## Common Pitfalls

### 1. Forgetting to Await

```python
result = service.fetch("query")       # WRONG: missing await, result is a coroutine
result = await service.fetch("query") # RIGHT
```

### 2. Mock Not Resetting Between Tests

Use fixtures (`scope="function"`) instead of module-level mocks. Each test gets a fresh instance.

### 3. Patching the Wrong Import Path

Patch where the name is **looked up** (the importing module), not where it is **defined** (the source module). See the `patch` section above.

### 4. asyncio Event Loop Scope Issues

Keep async fixtures at `function` scope (the default) to avoid cross-loop problems.

### 5. Forgetting new_callable=AsyncMock

```python
@patch("my_module.async_func")                        # WRONG: MagicMock, can't await
@patch("my_module.async_func", new_callable=AsyncMock) # RIGHT
```

---

## Java Comparison Table

| JUnit / Mockito | pytest / unittest.mock |
|---|---|
| `@Test` | `def test_*()` |
| `@BeforeEach` / `@AfterEach` | `@pytest.fixture` with `yield` |
| `@BeforeAll` | `@pytest.fixture(scope="module")` |
| `assertEquals(expected, actual)` | `assert actual == expected` |
| `assertThrows(Ex.class, ...)` | `with pytest.raises(Ex):` |
| `@ParameterizedTest` | `@pytest.mark.parametrize` |
| `@Disabled` | `@pytest.mark.skip` |
| `@Tag("slow")` | `@pytest.mark.slow` |
| `Mockito.mock(Foo.class)` | `Mock(spec=Foo)` |
| `when(m.x()).thenReturn(v)` | `m.x.return_value = v` |
| `when(m.x()).thenThrow(e)` | `m.x.side_effect = e` |
| `verify(m).x(arg)` | `m.x.assert_called_with(arg)` |
| `verify(m, never()).x()` | `m.x.assert_not_called()` |
| `ArgumentCaptor<T>` | `m.x.call_args` |
| `@Spy` | `patch.object(cls, "m", wraps=real.m)` |
| `@Mock` field | `@pytest.fixture` returning `Mock()` |
| `Mockito.reset(m)` | `m.reset_mock()` |

---

## Cross-References

- [adk/22-testing.md](adk/22-testing.md) -- MockModel, InMemoryRunner, simplify_events, full ADK testing patterns
- [adk/15-evaluation.md](adk/15-evaluation.md) -- agent quality evaluation with EvalCase, EvalSet, AgentEvaluator
- [python-asyncio-deep-dive.md](python/python-asyncio-deep-dive.md) -- async/await fundamentals, AsyncGenerator patterns
- [python-for-adk-learning-plan.md](python/python-for-adk-learning-plan.md) -- 2-week Python curriculum including testing milestones

---

*Part of the Python for ADK learning series -- March 2026*
