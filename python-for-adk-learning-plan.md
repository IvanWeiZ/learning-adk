# Python for ADK — 2-Week Learning Plan

For experienced Java developers transitioning to Python for ADK development.

**Prerequisites:** Strong Java background, familiarity with OOP, generics, and async concepts.

---

## Week 1: Python Fundamentals for ADK

### Day 1–2: Python Basics That Differ from Java

#### Key Differences

| Java | Python | Notes |
|------|--------|-------|
| `int x = 5;` | `x = 5` | No type declarations required, no semicolons |
| `{ ... }` | Indentation | Whitespace is significant (4 spaces standard) |
| `null` | `None` | Singleton, use `is None` not `== None` |
| `this` | `self` | Explicit first parameter in methods |
| `new MyClass()` | `MyClass()` | No `new` keyword |
| `public/private` | Convention (`_prefix`) | No enforced access modifiers |
| `final` | `@final` decorator | From `typing` module |
| `instanceof` | `isinstance()` | Function, not operator |

#### Classes and `__init__`

```python
# Java: public class Agent { private String name; public Agent(String name) { this.name = name; } }
# Python:
class Agent:
    def __init__(self, name: str, model: str = "gemini-2.5-flash"):
        self.name = name
        self.model = model  # default arguments are common

    def describe(self) -> str:
        return f"Agent {self.name} using {self.model}"
```

#### Modules and Packages

```python
# Java: import com.google.adk.agents.LlmAgent;
# Python:
from google.adk.agents import LlmAgent  # import specific class
from google.adk import agents           # import module
import google.adk.agents as agents      # import with alias
```

- A **module** = a `.py` file
- A **package** = a directory with `__init__.py`
- No classpath — use `PYTHONPATH` or install packages with `pip`

#### Common Gotchas

```python
# Mutable default arguments — Java devs often miss this
def bad(items: list = []):    # BUG: shared across all calls
    items.append(1)
    return items

def good(items: list | None = None):  # Correct
    if items is None:
        items = []
    items.append(1)
    return items

# Truthiness — Python is more flexible than Java
if []        : ...  # False (empty collection)
if [1, 2]    : ...  # True (non-empty)
if ""        : ...  # False (empty string)
if 0         : ...  # False
if None      : ...  # False
```

#### Practice

1. Rewrite a simple Java class hierarchy in Python
2. Create a module with 2-3 classes and import them from another file
3. Experiment with `dir()`, `help()`, and `type()` in the REPL

---

### Day 3: Type Hints and Python's Type System

Python is dynamically typed but supports optional type hints (like TypeScript for JavaScript).

```python
from typing import Optional, Any
from collections.abc import AsyncGenerator

# Basic hints
def greet(name: str) -> str:
    return f"Hello, {name}"

# Python 3.10+ union syntax (used throughout ADK)
def process(value: str | int | None) -> dict[str, Any]:
    return {"value": value}

# Generic collections (lowercase in 3.10+)
def get_tools() -> list[str]:
    return ["search", "calculate"]

agents: dict[str, list[str]] = {"root": ["sub1", "sub2"]}

# AsyncGenerator — critical for ADK (see python-asyncio-deep-dive.md)
async def stream_events() -> AsyncGenerator[str, None]:
    yield "event1"
    yield "event2"

# Callable types
from collections.abc import Callable
InstructionProvider = Callable[[dict], str]
```

**Key ADK types to know:**
- `Optional[X]` = `X | None`
- `dict[str, Any]` — used everywhere for state, args, config
- `AsyncGenerator[Event, None]` — the core ADK streaming type
- `Callable` — for callbacks (`before_agent_callback`, etc.)

#### Practice

1. Add type hints to your Day 1-2 classes
2. Run `mypy` on your code to see what it catches
3. Read `LlmAgent` field types in [04-agents.md](adk/04-agents.md)

---

### Day 4: Data Classes and Pydantic

ADK uses **Pydantic v2** extensively. Every `Session`, `Event`, and `Agent` is a Pydantic `BaseModel`.

```python
# Python dataclass (built-in, lightweight)
from dataclasses import dataclass

@dataclass
class Config:
    name: str
    max_retries: int = 3

# Pydantic BaseModel (validation, serialization, used by ADK)
from pydantic import BaseModel, Field

class AgentConfig(BaseModel):
    name: str
    model: str = "gemini-2.5-flash"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

config = AgentConfig(name="my_agent", temperature=1.5)
print(config.model_dump())  # {'name': 'my_agent', 'model': 'gemini-2.5-flash', 'temperature': 1.5}
```

**When to use which:**

| Feature | `dataclass` | Pydantic `BaseModel` |
|---------|-------------|---------------------|
| Validation | No | Yes (automatic) |
| Serialization | Manual | Built-in (`model_dump`, `model_dump_json`) |
| Immutability | `frozen=True` | `model_config = ConfigDict(frozen=True)` |
| ADK usage | Rare | Everywhere |

> **Deep dive:** [python-pydantic-deep-dive.md](python-pydantic-deep-dive.md)

#### Practice

1. Create a Pydantic model for a "tool result" with validated fields
2. Try passing invalid data and see how Pydantic handles it
3. Read how `Session` is defined in [08-sessions.md](adk/08-sessions.md)

---

### Day 5: Iterators, Generators, and Comprehensions

Generators are fundamental to ADK — every agent produces events via `AsyncGenerator`.

```python
# List comprehension (Java equivalent: streams + collect)
names = [agent.name for agent in agents if agent.active]

# Dict comprehension
tool_map = {t.name: t for t in tools}

# Generator function (lazy evaluation)
def count_up(n: int):
    i = 0
    while i < n:
        yield i  # pauses here, resumes on next()
        i += 1

for num in count_up(5):
    print(num)  # 0, 1, 2, 3, 4

# Generator expression (like comprehension but lazy)
total = sum(t.cost for t in tools)
```

**ADK pattern — AsyncGenerator for event streaming:**

```python
from collections.abc import AsyncGenerator

async def _run_async_impl(ctx) -> AsyncGenerator[Event, None]:
    # This is the pattern every ADK agent uses
    yield Event(author=self.name, content=...)  # emit event
    # Agent pauses here until consumer requests next event
    yield Event(author=self.name, content=...)  # emit another
```

> **Deep dive:** [python-asyncio-deep-dive.md](python-asyncio-deep-dive.md) covers `async for` and `AsyncGenerator` in detail.

#### Practice

1. Write a generator that yields Fibonacci numbers
2. Convert a loop that builds a list into a comprehension
3. Write an async generator and consume it with `async for`

---

### Day 6–7: Decorators and Metaprogramming Basics

Decorators are Python's equivalent of Java annotations — but they execute at runtime, not compile time.

```python
import functools
import time

# Basic decorator (like Java AOP)
def timer(func):
    @functools.wraps(func)  # preserves func metadata
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.2f}s")
        return result
    return wrapper

@timer
def fetch_data(url: str) -> dict:
    ...

# Decorator with arguments
def retry(max_attempts: int = 3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator

@retry(max_attempts=5)
def call_api(): ...
```

**ADK uses these decorators heavily:**
- `@final` — prevents subclass override (on `BaseAgent.run_async`)
- `@override` — marks intentional overrides
- `@abstractmethod` — from `abc.ABC`, like Java `abstract`
- `@field_validator` / `@model_validator` — Pydantic validation
- `@pytest.mark.asyncio` — marks async tests

> **Deep dive:** [python-decorators-metaprogramming-deep-dive.md](python-decorators-metaprogramming-deep-dive.md)

#### Practice

1. Write a `@log_calls` decorator that prints function name and args
2. Write a decorator with arguments (e.g., `@cache(ttl=60)`)
3. Look at how `@final` is used in [04-agents.md](adk/04-agents.md)

---

## Week 2: Async Python and ADK Patterns

### Day 8–9: asyncio Fundamentals

ADK is **async-first**. Every agent, tool, and service uses `async/await`.

```python
import asyncio

# Coroutine (like Java CompletableFuture but single-threaded)
async def fetch_weather(city: str) -> dict:
    await asyncio.sleep(1)  # simulate I/O (NEVER use time.sleep!)
    return {"city": city, "temp": 18}

# Running coroutines
async def main():
    # Sequential
    tokyo = await fetch_weather("Tokyo")
    london = await fetch_weather("London")

    # Concurrent (like Java CompletableFuture.allOf)
    tokyo, london = await asyncio.gather(
        fetch_weather("Tokyo"),
        fetch_weather("London"),
    )

asyncio.run(main())  # entry point
```

**ADK's async pattern:**

```python
# The core ADK loop — async for over an AsyncGenerator
async for event in runner.run_async(
    user_id="user_42",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text="Hello")]),
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

**Critical rules:**
- Never call `time.sleep()` — use `await asyncio.sleep()`
- Never do blocking I/O without `asyncio.to_thread()`
- Every ADK tool can be `async def` or `def` (sync tools are run in thread pool)

> **Deep dive:** [python-asyncio-deep-dive.md](python-asyncio-deep-dive.md)

#### Practice

1. Write two async functions and run them concurrently with `gather`
2. Write an async generator and consume it with `async for`
3. Trace through the request lifecycle in [01-request-lifecycle.md](adk/01-request-lifecycle.md)

---

### Day 10: Error Handling Patterns

```python
# try/except (Java: try/catch)
try:
    result = await tool.run_async(args=args, tool_context=ctx)
except ValueError as e:
    print(f"Invalid input: {e}")
except (ConnectionError, TimeoutError):
    print("Network issue")
except Exception as e:
    print(f"Unexpected: {e}")
    raise  # re-raise (Java: throw)
finally:
    cleanup()

# Context managers (Java: try-with-resources)
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
# session is auto-closed here

# Custom exception
class ToolExecutionError(Exception):
    def __init__(self, tool_name: str, message: str):
        super().__init__(f"Tool '{tool_name}' failed: {message}")
        self.tool_name = tool_name
```

**ADK error patterns:**
- Tools return error dicts (not exceptions) for LLM-visible errors
- `before_tool_callback` can short-circuit with an error response
- `on_tool_error_callback` recovers from tool exceptions
- See [16-error-reference.md](adk/16-error-reference.md) for all error paths

---

### Day 11: Testing with pytest

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Basic test (no @Test annotation needed)
def test_tool_returns_result():
    result = my_tool(query="test")
    assert result["status"] == "ok"
    assert "data" in result

# Fixture (Java: @BeforeEach)
@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.state = {}
    return ctx

def test_tool_writes_state(mock_context):
    save_note("hello", tool_context=mock_context)
    assert mock_context.state["note"] == "hello"

# Async test
@pytest.mark.asyncio
async def test_async_tool():
    result = await async_tool(query="test")
    assert result is not None

# Parametrize (run test with multiple inputs)
@pytest.mark.parametrize("city,expected", [
    ("Tokyo", 18),
    ("London", 12),
])
def test_weather(city, expected):
    result = get_weather(city)
    assert result["temp"] == expected
```

> **Deep dive:** [python-testing-and-mocking-guide.md](python-testing-and-mocking-guide.md)
> **ADK testing:** [22-testing.md](adk/22-testing.md) — `MockModel`, `InMemoryRunner`, `simplify_events`

---

### Day 12: Package Structure and Imports

```
my_agent/
├── __init__.py          # Makes this a package (can be empty)
├── agent.py             # Agent definition
├── tools/
│   ├── __init__.py
│   ├── search.py        # Search tool
│   └── calculator.py    # Calculator tool
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # Shared fixtures
│   └── test_agent.py
└── pyproject.toml       # Project metadata (like pom.xml)
```

```python
# Absolute imports (preferred)
from my_agent.tools.search import search_web
from my_agent.agent import root_agent

# Relative imports (within a package)
from .tools import search_web        # from same package
from ..utils import helper           # from parent package
```

**Virtual environments (like Java's Maven local repo):**

```bash
python -m venv .venv           # create
source .venv/bin/activate      # activate
pip install google-adk         # install
pip install -e .               # install current project in dev mode
```

---

### Day 13–14: Putting It Together — Reading ADK Source Code

Now apply everything to read and understand ADK patterns.

#### Exercise 1: Trace a Request

Read [01-request-lifecycle.md](adk/01-request-lifecycle.md) and trace:
1. `Runner.run_async()` — how does the session get loaded?
2. `BaseAgent.run_async()` — where do callbacks fire?
3. `BaseLlmFlow.run_async()` — how does the tool loop work?

#### Exercise 2: Write a Tool

```python
from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext

async def lookup_user(user_id: str, tool_context: ToolContext) -> dict:
    """Look up a user by ID and cache the result in session state."""
    cached = tool_context.state.get(f"user:{user_id}")
    if cached:
        return cached

    # Simulate API call
    user_data = {"id": user_id, "name": "Alice", "plan": "premium"}
    tool_context.state[f"user:{user_id}"] = user_data
    return user_data

agent = LlmAgent(
    name="support_agent",
    model="gemini-2.5-flash",
    instruction="Help users with their accounts. Use lookup_user to find user info.",
    tools=[lookup_user],
)
```

#### Exercise 3: Write a Test

```python
from tests.unittests.testing_utils import MockModel, InMemoryRunner, simplify_events
from google.genai.types import Part

def test_support_agent_uses_tool():
    mock = MockModel.create(responses=[
        Part.from_function_call(name="lookup_user", args={"user_id": "u123"}),
        "Alice is on the premium plan.",
    ])
    agent = LlmAgent(name="support", model=mock, tools=[lookup_user])
    runner = InMemoryRunner(agent)
    events = runner.run("Tell me about user u123")

    assert simplify_events(events)[-1] == ("support", "Alice is on the premium plan.")
```

---

## What to Read Next

| Goal | Resource |
|------|----------|
| Understand the full architecture | [README.md](README.md) → [01-request-lifecycle.md](adk/01-request-lifecycle.md) |
| Build your first agent | [25-onboarding-guide.md](adk/25-onboarding-guide.md) |
| Decide what to build | [02-when-to-build-what.md](adk/02-when-to-build-what.md) |
| Go deeper on async | [python-asyncio-deep-dive.md](python-asyncio-deep-dive.md) |
| Go deeper on Pydantic | [python-pydantic-deep-dive.md](python-pydantic-deep-dive.md) |
| Go deeper on decorators | [python-decorators-metaprogramming-deep-dive.md](python-decorators-metaprogramming-deep-dive.md) |
| Go deeper on testing | [python-testing-and-mocking-guide.md](python-testing-and-mocking-guide.md) |
| Java → Python quick reference | [java-to-python-cheat-sheet.md](java-to-python-cheat-sheet.md) |
| ADK terminology | [glossary.md](glossary.md) |
