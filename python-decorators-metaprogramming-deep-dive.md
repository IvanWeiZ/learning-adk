# Python Decorators & Metaprogramming Deep Dive

**Audience:** Experienced Java developers learning Python for ADK development.

---

## What It Is

Decorators are Python's answer to Java annotations + AOP, but with a critical difference: **decorators are runtime code, not metadata**. A Java annotation like `@Override` is a compile-time marker that tooling interprets. A Python decorator executes at definition time, receives the decorated object, and returns a replacement. This makes them far more powerful — they can modify behavior, validate signatures, register objects, or replace the target entirely. ADK uses decorators extensively: `@final` to lock down public APIs, `@override` for implementation methods, Pydantic validators on agent fields, and `@pytest.mark.asyncio` for async tests.

---

## Function Decorators

### Basic Decorator Pattern

A decorator is any callable that takes a function and returns a function. The `@` syntax is sugar for reassignment.

```python
# These two are identical:

@my_decorator
def greet(name: str) -> str:
    return f"Hello, {name}"

# is exactly:
def greet(name: str) -> str:
    return f"Hello, {name}"
greet = my_decorator(greet)
```

The standard pattern uses a nested wrapper function:

```python
def log_calls(func):
    """Decorator that logs every call to the wrapped function."""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@log_calls
def add(a: int, b: int) -> int:
    return a + b
```

**Java parallel:** Like wrapping a method call in an `InvocationHandler` (java.lang.reflect.Proxy), but applied at definition time.

### functools.wraps — Preserving Metadata

Without `@functools.wraps`, the wrapper replaces the original function's `__name__`, `__doc__`, and `__annotations__`. This breaks introspection and ADK's tool system (which reads function metadata to build tool declarations).

```python
import functools

def log_calls(func):
    @functools.wraps(func)  # copies __name__, __doc__, __module__, __annotations__
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

**Rule:** Always use `@functools.wraps(func)` on wrapper functions. ADK's `FunctionTool` inspects `__name__` and `__doc__` to generate the tool's name and description for the LLM.

### Decorators with Arguments

When a decorator needs configuration, add an outer function that returns the actual decorator (three-level nesting):

```python
import functools

def retry(max_attempts: int = 3):
    """Decorator factory — returns a configured decorator."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator

@retry(max_attempts=5)
def fetch_data(url: str) -> dict: ...
```

**Mental model:** `@retry(max_attempts=5)` calls `retry(5)` -> returns `decorator` -> `decorator(fetch_data)` -> returns `wrapper`. **Java parallel:** Like `@Retry(maxAttempts = 5)`, except the behavior is defined here, not in a separate annotation processor.

---

### Stacking Decorators

Decorators apply bottom-up (closest to the function first), but execute top-down at call time:

```python
@decorator_a    # outermost wrapper — runs first at call time
@decorator_b
@decorator_c    # applied first — innermost wrapper
def my_func(): ...
# Equivalent to: my_func = decorator_a(decorator_b(decorator_c(my_func)))
```

Think of it like nested middleware or servlet filters.

### Common Standard Library Decorators

| Decorator | Purpose | Java Equivalent |
|---|---|---|
| `@property` | Getter method accessed as attribute | `getX()` method |
| `@staticmethod` | No `self`/`cls` parameter | `static` method |
| `@classmethod` | Receives class as first arg (`cls`) | Static factory method pattern |
| `@functools.lru_cache` | Memoization with LRU eviction | Guava `CacheBuilder` |
| `@functools.cached_property` | One-time computed attribute | Lazy initialization pattern |
| `@abc.abstractmethod` | Must be implemented by subclasses | `abstract` method |
| `@typing.final` | Prevents override in subclasses | `final` method |
| `@typing.override` | Marks intentional override | `@Override` annotation |

```python
from functools import lru_cache

class ToolRegistry:
    @staticmethod
    def validate_name(name: str) -> bool:       # no self/cls — pure utility
        return name.isidentifier() and name != "user"

    @classmethod
    def from_config(cls, config: dict) -> "ToolRegistry":  # receives class, not instance
        return cls()

    @property
    def tool_count(self) -> int:                 # accessed as registry.tool_count (no parens)
        return len(self._tools)

@lru_cache(maxsize=128)
def expensive_lookup(key: str) -> dict: ...      # memoized — same key returns cached value
```

---

## Class Decorators

A class decorator receives a class and returns a (possibly modified) class. Same `@` syntax, applied to the `class` statement.

### @dataclass

The most common class decorator. Generates `__init__`, `__repr__`, `__eq__` from annotated fields:

```python
from dataclasses import dataclass, field

@dataclass
class ToolCall:
    name: str
    args: dict[str, str]
    call_id: str = field(default_factory=lambda: str(uuid4()))
# Java equivalent: a record or a class with Lombok @Data
```

**Note:** ADK uses Pydantic `BaseModel` instead of `@dataclass` (adds validation, serialization, schema generation), but `@dataclass` is common in Python at large.

### Custom Class Decorators

```python
def register_agent(cls):
    """Register the agent class in a global registry."""
    AGENT_REGISTRY[cls.__name__] = cls
    return cls  # return the class unchanged

@register_agent
class WeatherAgent:
    ...
# WeatherAgent is now in AGENT_REGISTRY and is still the same class.
```

**Java parallel:** Like `@Entity` or `@Component` — but in Python, the decorator *is* the processor, running immediately at class definition time.

## How ADK Uses Decorators

### @final and @override on BaseAgent

ADK marks `run_async` as `@final` (Template Method pattern) and expects subclasses to use `@override` on `_run_async_impl`:

```python
from typing import final, override

class BaseAgent:
    @final
    async def run_async(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Orchestration: callbacks, context creation, delegation
        ...  # subclasses CANNOT override this

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        raise NotImplementedError

class LlmAgent(BaseAgent):
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        ...  # LLM-specific implementation
```

**Java parallel:** `@final` = `final` keyword; `@override` = `@Override`. Key difference: Python's `@final` is advisory (enforced by mypy, not the runtime).

### Pydantic's @field_validator and @model_validator

ADK agents inherit from Pydantic `BaseModel`, so field validation uses Pydantic decorators:

```python
from pydantic import BaseModel, field_validator, model_validator

class LlmAgent(BaseModel):
    name: str
    model: str | BaseLlm | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_identifier(cls, v: str) -> str:
        if not v.isidentifier() or v == "user":
            raise ValueError(f"Invalid agent name: {v!r}")
        return v

    @model_validator(mode="after")
    def check_model_or_sub_agents(self) -> "LlmAgent":
        if self.model is None and not self.sub_agents:
            raise ValueError("Agent must have either a model or sub_agents")
        return self
```

See [python-pydantic-deep-dive.md](python-pydantic-deep-dive.md) for full Pydantic validator coverage.

### @pytest.mark.asyncio for Async Tests

ADK's async-first design means tests run in an event loop via `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_agent_run():
    agent = LlmAgent(name="test_agent", model="gemini-2.0-flash")
    runner = InMemoryRunner(agent=agent, app_name="test")
    session = await runner.session_service.create_session(app_name="test", user_id="u1")
    events = [e async for e in runner.run_async(user_id="u1", session_id=session.id, new_message=...)]
    assert len(events) > 0
```

---

## Metaprogramming Basics

Metaprogramming means writing code that manipulates code. Python supports this through several mechanisms, from simple to advanced.

### \_\_init\_subclass\_\_ — Hook into Subclassing

Called automatically when a class is subclassed. Simpler than metaclasses for registration/validation:

```python
class PluginBase:
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, *, plugin_name: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        PluginBase._registry[plugin_name or cls.__name__] = cls

class AuthPlugin(PluginBase, plugin_name="auth"): ...
class LogPlugin(PluginBase, plugin_name="logging"): ...
# PluginBase._registry == {"auth": AuthPlugin, "logging": LogPlugin}
```

**Java parallel:** Like a static initializer + `ServiceLoader`-style registry, triggered at class definition time.

### ABCs and Abstract Methods (vs Java Interfaces)

Python's `abc` module provides abstract base classes — the closest equivalent to Java interfaces:

```python
from abc import ABC, abstractmethod

class BaseLlm(ABC):
    @abstractmethod
    async def generate_content_async(self, request: LlmRequest, ctx: LlmContext) -> LlmResponse: ...

class GeminiLlm(BaseLlm):
    async def generate_content_async(self, request, ctx) -> LlmResponse: ...
```

| Java | Python |
|---|---|
| `interface Foo` | `class Foo(ABC)` with all `@abstractmethod` |
| `abstract class Foo` | `class Foo(ABC)` with some concrete methods |
| `implements Foo, Bar` | `class Baz(Foo, Bar)` (multiple inheritance) |
| Instantiate abstract -> compile error | Instantiate ABC -> `TypeError` at runtime |

### Descriptors — \_\_get\_\_, \_\_set\_\_, \_\_delete\_\_

Descriptors power `@property`, `@classmethod`, and `@staticmethod` under the hood. A descriptor is any object defining `__get__`, `__set__`, or `__delete__`:

```python
class TypeChecked:
    """Descriptor that enforces a type on assignment."""
    def __init__(self, expected_type: type):
        self.expected_type = expected_type

    def __set_name__(self, owner, name):
        self.attr_name = f"_{name}"
        self.public_name = name

    def __get__(self, obj, objtype=None):
        return self if obj is None else getattr(obj, self.attr_name, None)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f"{self.public_name} must be {self.expected_type.__name__}")
        setattr(obj, self.attr_name, value)
```

You rarely write descriptors directly in ADK code (Pydantic handles it), but understanding them explains how `@property` and validated fields work.

### \_\_class\_getitem\_\_ and Generic Types

`__class_getitem__` enables the `ClassName[Type]` syntax. In practice, inherit from `typing.Generic[T]` to make your class generic. You see this throughout ADK: `AsyncGenerator[Event, None]`, `Optional[BaseLlm]`, `list[BaseTool]`.

---

### Metaclasses — Brief Mention

Metaclasses control class creation itself. A metaclass's `__new__` runs when the `class` statement executes:

```python
class SingletonMeta(type):
    _instances: dict[type, object] = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class LLMRegistry(metaclass=SingletonMeta): ...
# LLMRegistry() always returns the same instance
```

**In ADK:** Metaclasses are rare. Pydantic uses `ModelMetaclass` internally; `ABCMeta` backs `ABC`. Prefer `__init_subclass__` or class decorators instead.

## Practical Examples

### Writing a Logging Decorator (Async-Aware)

```python
import asyncio, functools, logging
logger = logging.getLogger(__name__)

def log_calls(func):
    """Log entry and exit for sync and async functions."""
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"-> {func.__name__}")
            result = await func(*args, **kwargs)
            logger.info(f"<- {func.__name__} returned {result!r}")
            return result
        return wrapper
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"-> {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"<- {func.__name__} returned {result!r}")
            return result
        return wrapper
```

---

### Writing a Retry Decorator (Async)

Useful for wrapping flaky API calls in ADK tools. Combines decorator-with-arguments and async patterns:

```python
import asyncio, functools

def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry an async function with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

@async_retry(max_attempts=3, delay=0.5)
async def call_external_api(endpoint: str) -> dict:
    """ADK tool that calls an external API with automatic retry."""
    ...
```

---

### Decorator That Validates Function Arguments

Illustrates how ADK's `FunctionTool` validates tool inputs using `inspect`:

```python
import functools, inspect
from typing import get_type_hints

def validate_args(func):
    """Enforce type hints at runtime."""
    hints, sig = get_type_hints(func), inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        for name, value in bound.arguments.items():
            if name in hints and not isinstance(value, hints[name]):
                raise TypeError(f"'{name}' expected {hints[name].__name__}, got {type(value).__name__}")
        return func(*args, **kwargs)
    return wrapper

@validate_args
def create_agent(name: str, max_retries: int) -> dict:
    return {"name": name, "max_retries": max_retries}

create_agent("my_agent", 3)       # OK
create_agent("my_agent", "three")  # TypeError: 'max_retries' expected int, got str
```

---

## Java Comparison Table

| Java | Python | Notes |
|---|---|---|
| `@Override` | `@override` (typing) | Compile-time vs type-checker check |
| `@Deprecated` | `warnings.warn(..., DeprecationWarning)` | No built-in decorator; use `warnings` or write one |
| `@SuppressWarnings` | `# type: ignore` / `# noqa` | Per-line pragmas, not decorators |
| `@FunctionalInterface` | `typing.Protocol` with single method | Structural typing, not nominal |
| `abstract` keyword | `@abstractmethod` + `ABC` base class | Runtime check at instantiation |
| `final` keyword | `@final` (typing) | Advisory; enforced by type checkers only |
| `static` keyword | `@staticmethod` | No implicit `this`/`self` |
| `interface` | `ABC` or `Protocol` | ABC = nominal; Protocol = structural |
| Annotation + processor | Decorator | Decorator is the processor |
| AOP (`@Around`) | Decorator wrapping | No framework needed; native AOP |

---

## Key Takeaways for ADK Development

1. **Always use `@functools.wraps`** on wrapper functions — ADK's `FunctionTool` relies on `__name__`, `__doc__`, `__annotations__`.
2. **Use `@override`** on `_run_async_impl` and similar methods — type checkers catch name typos.
3. **Understand `@final`** on `BaseAgent.run_async` — implement `_run_async_impl` instead (Template Method pattern).
4. **Know Pydantic decorators** — `@field_validator` and `@model_validator` validate agent configuration at construction.
5. **Prefer `__init_subclass__` over metaclasses** — simpler and composes better with Pydantic.
6. **Decorators are composable** — stack them like middleware layers.

---

## Cross-References

- [python-for-adk-learning-plan.md](python-for-adk-learning-plan.md) — Python learning curriculum (Week 1 covers decorators)
- [adk/04-agents.md](adk/04-agents.md) — `@final` on `run_async`, `@override` on `_run_async_impl`
- [adk/09-tools.md](adk/09-tools.md) — `FunctionTool` reads function metadata set by `@functools.wraps`
- [python-pydantic-deep-dive.md](python-pydantic-deep-dive.md) — `@field_validator`, `@model_validator`, and Pydantic's internal use of descriptors
