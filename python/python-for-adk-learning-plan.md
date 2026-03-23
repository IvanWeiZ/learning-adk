# Python for ADK — Learning Plan

> **ADK relevance:** Every Python feature here is directly used in ADK agent development | **Estimated time:** ~10 working days, 6-8 hours/day

## At a Glance

**For:** Experienced Java developer with basic Python knowledge
**Goal:** Master Python features needed for production ADK agents

**Week 1 — Foundations**

1. D1 — Type Hints and the `typing` module
2. D2 — Pydantic BaseModel (Part 1 — Basics)
3. D3 — Pydantic BaseModel (Part 2 — Advanced)
4. D4 — Generators and `yield`
5. D5 — asyncio (Part 1 — Coroutines and Tasks)
6. D6 — asyncio (Part 2 — Async Generators)
7. D7 — ABCs, Protocols, and Structural Subtyping

**Week 2 — Advanced Patterns & ADK-Specific**

8. D8 — Decorators and Closures
9. D9 — Context Managers
10. D10 — Dicts, Kwargs, and Data Classes
11. D11 — Module System and Imports
12. D12 — Error Handling Patterns
13. D13 — Testing with Async Code
14. D14 — Capstone Project

A focused 2-week curriculum that bridges your Java expertise with the Python patterns ADK relies on. Each day covers one or two tightly scoped topics with ADK connections, Java comparisons, and hands-on practice.

## Core Concepts

### How This Plan Is Organized

Each day includes:
- **Why it matters for ADK** — concrete connection to the framework
- **Java to Python** — what transfers and what doesn't
- **Key concepts** — what to study
- **Practice** — a small exercise that reinforces the concept in an ADK-like context

---

### Week 1 — Foundations

#### Day 1: Python Type Hints & the `typing` Module

**Why ADK needs this:**
ADK auto-generates tool schemas from your function signatures. If your type hints are wrong, your tools break. Every ADK class uses full type annotations.

**Java to Python:**
Java generics (`List<String>`) map to Python `list[str]`. Java's type system is enforced at compile time; Python's is optional and checked by tools like `mypy`. Think of it as TypeScript vs JavaScript — same language, opt-in safety.

**Key concepts to study:**
- Built-in generic types: `list[str]`, `dict[str, Any]`, `tuple[int, ...]`
- `Optional[X]` (equivalent to `X | None`)
- `Union[X, Y]` and the `X | Y` syntax (Python 3.10+)
- `Literal["a", "b"]` — restricts to exact values
- `Callable[[ArgTypes], ReturnType]` — typing function parameters
- `TypeVar` and `Generic` — creating your own generic classes
- `TypeAlias` for readability
- `TYPE_CHECKING` guard for circular imports
- `typing.get_type_hints()` — how ADK reads your annotations at runtime

**Practice:**
Write a function `def search(query: str, max_results: int = 10, filters: dict[str, Any] | None = None) -> list[dict[str, str]]` and verify `mypy` passes. Then write a generic `Registry[T]` class.

---

#### Day 2: Pydantic BaseModel (Part 1 — Basics)

**Why ADK needs this:**
Every ADK data structure — `Event`, `EventActions`, `Session`, `GenerateContentConfig` — is a Pydantic model. You subclass `BaseModel` constantly.

**Java to Python:**
Think of Pydantic as Lombok `@Data` + Jackson + Bean Validation all in one. You define fields with types, and Pydantic handles validation, serialization, and schema generation automatically.

**Key concepts to study:**
- Defining models: class fields with type annotations and defaults
- `Field()` — descriptions, aliases, constraints (`ge=`, `le=`, `min_length=`)
- Validation: how Pydantic coerces/validates on construction
- `model_dump()` and `model_dump_json()` — serialization
- `model_validate()` and `model_validate_json()` — deserialization
- Nested models — models containing other models
- `model_copy(update={...})` — **ADK uses this pattern heavily** for creating modified copies (like `InvocationContext`)
- `ConfigDict` — model configuration (e.g., `frozen=True` for immutability)

**Practice:**
Model an ADK-like `Event` class:
```python
from pydantic import BaseModel, Field

class Event(BaseModel):
    id: str
    author: str
    content: str | None = None
    timestamp: datetime
    actions: EventActions = Field(default_factory=EventActions)  # mutable default via Field
    branch: str | None = None
```
Then practice `model_copy(update={"author": "new_agent"})`.

---

#### Day 3: Pydantic BaseModel (Part 2 — Advanced)

**Why ADK needs this:**
ADK uses validators for configuration, custom serialization for events, and discriminated unions for different tool types.

**Key concepts to study:**
- `@field_validator` and `@model_validator` — custom validation logic
- `@computed_field` — derived properties that appear in serialization
- Discriminated unions: `Annotated[ToolA | ToolB, Field(discriminator="type")]`
- Custom serializers: `@field_serializer`
- JSON Schema generation: `Model.model_json_schema()` — this is how ADK creates tool definitions from your types
- `model_config = ConfigDict(arbitrary_types_allowed=True)` — when you need non-standard types

**Practice:**
Create a `ToolDefinition` model that uses a discriminated union for different tool types (`function`, `search`, `code_execution`), each with different required fields. Generate the JSON schema and inspect it.

---

#### Day 4: Generators & `yield` (Sync)

**Why ADK needs this:**
ADK streams everything through generators. Understanding sync generators is prerequisite to async generators (which ADK actually uses). The `yield` keyword has no Java equivalent — this is genuinely new.

**Java to Python:**
Java's `Stream<T>` is the closest analogy, but generators are lazily evaluated coroutines that maintain internal state between calls. More like a Java `Iterator` that's trivially easy to write.

**Key concepts to study:**
- `yield` — turns a function into a generator
- Generator protocol: `__iter__` and `__next__`
- `yield from` — delegating to sub-generators (like `flatMap`)
- Generator expressions: `(x for x in items if x > 0)`
- `send()` — sending values into a generator (less common but important)
- Memory efficiency — generators don't materialize the full collection
- Use as pipelines: chaining generators

**Practice:**
Write a generator that yields events from a simulated agent run:
```python
def simulate_agent_run(query: str) -> Generator[dict, None, None]:
    yield {"type": "thinking", "content": "Processing..."}
    yield {"type": "tool_call", "content": "search(query)"}
    yield {"type": "response", "content": f"Answer to {query}"}
```
Then chain it with a filter generator that only passes through certain event types.

---

#### Day 5: `asyncio` Fundamentals

**Why ADK needs this:**
ADK is **async-first**. Every agent method, every LLM call, every tool execution is async. If you don't understand asyncio, you can't use ADK.

**Java to Python:**
Java uses `CompletableFuture` and thread pools. Python's asyncio is single-threaded cooperative multitasking — closer to JavaScript's event loop than Java's threading model. This is a fundamental mindset shift.

**Key concepts to study:**
- Event loop: what it is, how it works (single thread!)
- `async def` — defines a coroutine
- `await` — suspends until result is ready
- `asyncio.run()` — entry point from sync code
- `asyncio.sleep()` vs `time.sleep()` (never use `time.sleep` in async code!)
- `asyncio.create_task()` — run coroutines concurrently
- `asyncio.gather()` — await multiple coroutines (used by `ParallelAgent`)
- `asyncio.TaskGroup` (Python 3.11+) — structured concurrency
- Error handling in async code
- Why blocking I/O in async code is catastrophic

**Practice:**
Write an async function that simulates calling 3 different LLM providers concurrently (each with a random `asyncio.sleep` delay) and returns the first result. Then write one that waits for all 3 and merges results.

---

#### Day 6: `AsyncGenerator` & `async for`

**Why ADK needs this:**
ADK's core method signature is:
```python
async def run_async(ctx: InvocationContext) -> AsyncGenerator[Event, None]
```
Every agent yields events asynchronously. This combines Day 4 (generators) and Day 5 (asyncio).

**Key concepts to study:**
- `async def` + `yield` = `AsyncGenerator`
- `async for event in agent.run_async(ctx):` — consuming async generators
- `AsyncIterator` protocol: `__aiter__` and `__anext__`
- Combining async generators: collecting, filtering, merging
- `async yield from` doesn't exist — you must use `async for x in sub(): yield x`
- Error handling and cleanup in async generators
- Typing: `AsyncGenerator[YieldType, SendType]`

**Practice:**
Build a mini agent framework:
```python
async def agent_a(query: str) -> AsyncGenerator[Event, None]:
    yield Event(type="start", agent="a")
    await asyncio.sleep(0.5)  # simulate LLM call
    yield Event(type="response", agent="a", content="result")

async def run_sequential(agents) -> AsyncGenerator[Event, None]:
    for agent in agents:
        async for event in agent("test"):
            yield event
```

---

#### Day 7: Abstract Base Classes, Protocols & Inheritance

**Why ADK needs this:**
ADK's extension model is built on ABCs: `BaseAgent`, `BaseLlm`, `BaseTool`, `BaseSessionService`. To create custom agents or tools, you subclass these and implement abstract methods.

**Java to Python:**
Java `abstract class` maps to Python `ABC`. Java `interface` maps to Python `Protocol` (structural) or `ABC` (nominal). Multiple inheritance is supported and commonly used (no `implements` keyword needed).

**Key concepts to study:**
- `abc.ABC` and `@abstractmethod`
- `typing.Protocol` — structural subtyping (duck typing with type safety)
- `@runtime_checkable` — allowing `isinstance()` checks on Protocols
- Python's MRO (Method Resolution Order) — how multiple inheritance resolves conflicts
- `super()` — calling parent methods (works differently from Java's `super`)
- `__init_subclass__` — hook called when a class is subclassed (used in registries)
- `__subclasses__()` — discovering all subclasses at runtime

**Practice:**
Create an ADK-like tool system:
```python
class BaseTool(ABC):
    @abstractmethod
    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any: ...
    # NOTE: args and tool_context are keyword-only (after *)

class FunctionTool(BaseTool):
    def __init__(self, func: Callable):
        self._func = func

    async def run_async(self, *, args, tool_context):
        return await self._func(**args)
```

---

### Week 2 — Advanced Patterns & ADK-Specific

#### Day 8: Decorators & First-Class Functions

**Why ADK needs this:**
ADK's callback system and tool registration rely on passing functions as arguments and using decorators. Tool registration patterns, callback registration, and plugin hooks all use these patterns. Note: ADK has no `@tool` decorator — tools are registered via the `FunctionTool()` constructor or by passing plain functions directly to `LlmAgent(tools=[...])`.

**Java to Python:**
Java's `@FunctionalInterface` and lambdas are limited compared to Python. In Python, functions are truly first-class objects — you can assign them to variables, pass them as arguments, return them from functions, and modify them with decorators.

**Key concepts to study:**
- Functions as objects: `func.__name__`, `func.__doc__`, `func.__annotations__`
- Higher-order functions: functions that take/return functions
- Closures: inner functions capturing outer scope variables
- Decorators: `@decorator` syntax is just `func = decorator(func)`
- Decorators with arguments: `@decorator(arg)` needs a decorator factory
- `functools.wraps` — preserving function metadata
- `functools.partial` — partial application
- `inspect` module — runtime introspection of function signatures (ADK uses this for tool schema generation)

**Practice:**
Write a `@register_tool` decorator that:
1. Reads the function's type hints and docstring
2. Generates a JSON schema for the tool
3. Registers it in a global tool registry
```python
@register_tool
async def search_web(query: str, max_results: int = 5) -> list[str]:
    """Search the web for information."""
    ...
```

---

#### Day 9: Context Managers & Resource Management

**Why ADK needs this:**
ADK uses async context managers for session management, MCP toolset connections, database connections, and cleanup. The `async with` pattern appears everywhere.

**Java to Python:**
Java's try-with-resources (`try (var x = ...)`) maps to Python's `with`/`async with`. The `__enter__`/`__exit__` protocol is like Java's `AutoCloseable` but more powerful.

**Key concepts to study:**
- `with` statement and the context manager protocol
- `__enter__` / `__exit__` (sync)
- `__aenter__` / `__aexit__` (async)
- `contextlib.contextmanager` — create context managers from generators
- `contextlib.asynccontextmanager` — async version
- `contextlib.ExitStack` / `AsyncExitStack` — managing multiple resources
- Cleanup guarantees and exception handling in `__exit__`
- Using context managers for state management (not just resources)

**Practice:**
Build an async session manager:
```python
class SessionManager:
    async def __aenter__(self):
        self.session = await create_session()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.save()
        await self.session.close()
        return False  # don't suppress exceptions
```

---

#### Day 10: Dict/Kwargs Patterns & Python Data Manipulation

**Why ADK needs this:**
ADK configuration, state management (`session.state`), event actions (`state_delta`), and tool arguments all use dict patterns heavily. Python dicts are far more central than Java Maps.

**Java to Python:**
Java `Map<String, Object>` maps to Python `dict[str, Any]`. But Python dicts are used where Java would use POJOs, builder patterns, or configuration objects.

**Key concepts to study:**
- `*args` and `**kwargs` — variadic arguments
- Dict unpacking: `{**base, **overrides}` (like spread operator)
- `dict.get(key, default)` vs `dict[key]`
- `dict.setdefault()`, `dict.update()`
- `collections.defaultdict` and `collections.Counter`
- Destructuring: `a, b, *rest = some_list`
- Walrus operator `:=` — assignment expressions
- Pattern matching (`match/case` — Python 3.10+) — like Java's enhanced switch

**Practice:**
Implement ADK-like state management:
```python
class SessionState:
    def __init__(self):
        self._state: dict[str, Any] = {}

    def apply_delta(self, delta: dict[str, Any]):
        """Merge delta into state, handling 'user:' and 'app:' prefixed keys."""
        for key, value in delta.items():
            if value is None:
                self._state.pop(key, None)  # delete
            else:
                self._state[key] = value
```

---

#### Day 11: Python Module System & Project Structure

**Why ADK needs this:**
ADK uses namespace packages (`google.adk.agents`), and your agent projects need proper structure for imports, testing, and deployment.

**Java to Python:**
Java packages map to directories with predictable rules. Python's module system is more flexible but also more confusing: `__init__.py`, relative imports, `sys.path` manipulation, namespace packages.

**Key concepts to study:**
- Modules vs packages vs namespace packages
- `__init__.py` — what it does, when to use it
- Import mechanics: `import`, `from x import y`, relative imports
- `__all__` — controlling `from module import *`
- Circular import resolution strategies
- `pyproject.toml` — modern Python project config (replaces `setup.py`)
- Virtual environments: `venv`, `uv`, or `poetry`
- Dependency management: `pip`, `uv`, `poetry`
- Entry points and `__main__.py`

**Practice:**
Structure a multi-agent ADK project:
```
my_agents/
├── pyproject.toml
├── src/
│   └── my_agents/
│       ├── __init__.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── search_agent.py
│       │   └── summary_agent.py
│       ├── tools/
│       │   ├── __init__.py
│       │   └── web_search.py
│       └── config.py
└── tests/
    └── test_agents.py
```

---

#### Day 12: Error Handling & Logging

**Why ADK needs this:**
ADK's `LlmAgent` has error callbacks (`on_model_error_callback`, `on_tool_error_callback`), and production agents need robust error handling and observability.

**Java to Python:**
Python has no checked exceptions (everything is unchecked). `logging` module is similar to SLF4J but configured differently. No `log4j.xml` — configuration is programmatic or via `dictConfig`.

**Key concepts to study:**
- Exception hierarchy: `BaseException` → `Exception` → specific types
- Custom exceptions: when and how to define them
- `try/except/else/finally` — the `else` clause is Python-specific
- Exception chaining: `raise X from Y`
- `logging` module: loggers, handlers, formatters, levels
- `logging.config.dictConfig()` — programmatic configuration
- `structlog` — structured logging (common in production Python)
- Async error handling: exceptions in tasks, `TaskGroup` exception groups
- `traceback` module — programmatic access to stack traces

**Practice:**
Build an error-handling wrapper for ADK tool execution:
```python
async def safe_tool_call(tool: BaseTool, args: dict, context: ToolContext) -> Event:
    try:
        result = await asyncio.wait_for(
            tool.run_async(args=args, tool_context=context), timeout=30.0
        )
        return Event(type="tool_result", content=result)
    except asyncio.TimeoutError:
        logger.warning("Tool %s timed out", tool.name)
        return Event(type="tool_error", content="Tool execution timed out")
    except Exception as e:
        logger.exception("Tool %s failed", tool.name)
        return Event(type="tool_error", content=str(e))
```

---

#### Day 13: Testing Async Python Code

**Why ADK needs this:**
You need to test your agents, tools, and flows. Testing async code has specific patterns.

**Java to Python:**
JUnit maps to `pytest`. Mockito maps to `unittest.mock`. But async testing needs `pytest-asyncio` and has its own patterns.

**Key concepts to study:**
- `pytest` basics: test discovery, assertions, fixtures
- `pytest-asyncio` — `@pytest.mark.asyncio` for async tests
- `unittest.mock`: `Mock`, `MagicMock`, `AsyncMock`
- `mock.patch` and `mock.patch.object` — monkey-patching for tests
- Fixtures: `@pytest.fixture` — dependency injection for tests
- `conftest.py` — shared fixtures
- Parametrized tests: `@pytest.mark.parametrize`
- Testing generators and async generators
- `hypothesis` — property-based testing (optional but powerful)

**Practice:**
Write tests for the tool system you built on Day 8:
```python
@pytest.mark.asyncio
async def test_search_tool_returns_results():
    with mock.patch("my_agents.tools.web_search.fetch") as mock_fetch:
        mock_fetch.return_value = ["result1", "result2"]
        tool = FunctionTool(search_web)
        result = await tool.run_async(args={"query": "test"}, tool_context=mock_context)
        assert len(result) == 2
```

---

#### Day 14: Putting It All Together — Build a Mini ADK Agent

**Why this matters:**
Integrate everything into one working project that mirrors ADK's architecture.

**Capstone project — build a simplified agent framework with:**

1. **Event system** (Pydantic models, typed events)
2. **Base agent** (ABC with `async run_async() -> AsyncGenerator[Event, None]`)
3. **LLM agent** (subclass that calls a mock LLM)
4. **Tool system** (decorator-based registration, schema generation from type hints)
5. **Sequential & Parallel agents** (composition using async generators)
6. **Session with state** (dict-based state with delta merging)
7. **Runner** (orchestrator that drives agents and collects events)
8. **Error handling & logging** throughout
9. **Tests** for every component

This is a **multi-session project** (not a single day). Expect ~300-500 lines of Python across multiple focused sessions, each exercising concepts from previous days.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using `time.sleep()` in async code | Always use `await asyncio.sleep()` |
| Missing `@functools.wraps` on decorators | ADK reads `__name__` and `__doc__` for tool schemas |
| Mutable default arguments (`def f(x=[])`) | Use `None` default and create inside function |
| Forgetting to `await` a coroutine | Python warns but won't raise — the coroutine never runs |
| Using `asyncio.run()` inside async code | Just `await` directly — nested `run()` raises RuntimeError |

## Quick Reference

For a full Java → Python side-by-side mapping, see [java-to-python-cheat-sheet.md](../reference/java-to-python-cheat-sheet.md).

---

**Recommended Resources**

**Official docs (primary source of truth):**
- [Python `typing` module](https://docs.python.org/3/library/typing.html)
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/)
- [Python `asyncio` docs](https://docs.python.org/3/library/asyncio.html)
- [Google ADK documentation](https://google.github.io/adk-python/)
- [pytest docs](https://docs.pytest.org/)

**Books & courses:**
- *Fluent Python* (2nd ed.) by Luciano Ramalho — chapters on generators, async, decorators, and protocols are gold
- *Python Concurrency with asyncio* by Matthew Fowler — deep dive on async patterns
- *Robust Python* by Patrick Viafore — type hints, Pydantic, and writing maintainable Python

**Practice platforms:**
- Build small projects after each day's topic
- Read ADK source code on GitHub (`google/adk-python`) — best way to see patterns in action
- Contribute to ADK or build a sample multi-agent project
