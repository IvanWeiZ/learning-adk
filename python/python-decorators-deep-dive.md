# Python Decorators — Deep Dive

## At a Glance

```
+------------------------------------------------------------------+
|          Decorators & Metaprogramming Landscape                    |
|                                                                    |
|  Functions ──► Closures ──► Decorators ──► Class Decorators        |
|      |              |            |               |                 |
|  first-class     capture      @syntax        @dataclass            |
|  objects         scope        = wrapping     = class transform     |
|                                                                    |
|  inspect module ──► Read signatures ──► Generate tool schemas      |
|  __init_subclass__ ──► Auto-register ──► Plugin/agent registries   |
|  Descriptors ──► @property ──► Attribute validation                |
|  functools ──► wraps, partial, lru_cache, singledispatch           |
|                                                                    |
|  ADK uses ALL of these for tool registration, callback hooks,      |
|  schema generation, and plugin systems.                            |
+------------------------------------------------------------------+
```

> **ADK relevance:** Tool registration, callback hooks, schema generation from type hints, plugin systems | **Estimated time:** 3-4 hours

This guide bridges your Java expertise with Python's metaprogramming paradigm. If you have worked with Java annotations, method reflection, and the ServiceLoader pattern, you already understand the *intent* behind Python's decorators and metaprogramming. But Python's implementation is more direct, more functional, and more flexible.

The Google ADK (Agent Development Kit) relies on decorator and metaprogramming *concepts* (though it does not ship decorators like `@tool` or `@register_tool`):
- **Tool wrapping**: ADK's [`FunctionTool`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/function_tool.py) wraps a plain function -- it reads the function's signature and docstring via `inspect` to auto-generate the tool schema
- **Callbacks**: lifecycle hooks (`before_agent_callback`, `before_model_callback`, etc.) are plain callables passed as constructor arguments -- no decorator syntax required
- **Schema generation**: The `inspect` module to read function signatures and `typing.get_type_hints()` to resolve annotations, automatically building tool schemas

Understanding decorators and metaprogramming is foundational to using ADK effectively.

## Core Concepts

### 1. Functions Are Objects

In Java, methods are tightly bound to classes. You have limited functional freedom. In Python, **functions are first-class objects**—they have attributes, you can assign them to variables, pass them around, and store them in collections.

#### Function Attributes

Every function has introspectable attributes:

```python
def greet(name: str, greeting: str = "Hello") -> str:
    """Greet someone with an optional custom greeting."""
    return f"{greeting}, {name}!"

# Inspect function attributes
print(greet.__name__)          # 'greet'
print(greet.__doc__)           # "Greet someone with an optional custom greeting."
print(greet.__annotations__)   # {'name': <class 'str'>, 'greeting': <class 'str'>, 'return': <class 'str'>}
print(greet.__defaults__)      # ('Hello',)  — defaults for positional parameters
print(greet.__code__)          # <code object greet at 0x...>
print(greet.__code__.co_varnames)  # ('name', 'greeting')
print(greet.__code__.co_argcount)  # 2

# Functions are objects—assign to variables
greet_en = greet
greet_es = lambda name, greeting="Hola": f"{greeting}, {name}!"

# Store in collections
greetings = [greet_en, greet_es]
for g in greetings:
    print(g("you"))

# Pass as arguments
def apply_greeting(greeting_func, name):
    return greeting_func(name)

result = apply_greeting(greet, "you")
```

#### Java Comparison

In Java, you'd need:
```java
// Java approach: functional interface + lambda
@FunctionalInterface
interface Greeter {
    String greet(String name);
}

Greeter greetEn = name -> String.format("Hello, %s!", name);

// But you can't introspect a lambda's signature at runtime!
// You need reflection on the functional interface, not the lambda itself.
```

Python's functions are more directly introspectable. You can read a function's signature without wrapping it in an interface.

#### Key Takeaway

Functions are data. This enables:
- Passing behavior (functions) to higher-order functions
- Storing callbacks in dictionaries
- Dynamically building function registries
- Decorators (which are just higher-order functions)

---

### 2. Closures

A **closure** is an inner function that captures variables from its enclosing scope. This is foundational to decorators.

#### Basic Closure

```python
def make_adder(x):
    """Factory function that returns a closure."""
    def add(y):
        return x + y  # Captures 'x' from outer scope
    return add

add_5 = make_adder(5)
add_10 = make_adder(10)

print(add_5(3))    # 8
print(add_10(3))   # 13

# Inspect closure variables
print(add_5.__closure__)  # (<cell at 0x...: int object at 0x...>,)
print(add_5.__closure__[0].cell_contents)  # 5
```

#### The `nonlocal` Keyword

If you want an inner function to *modify* a captured variable, use `nonlocal`:

```python
def make_counter():
    count = 0

    def increment():
        nonlocal count  # Declare we're modifying the outer 'count'
        count += 1
        return count

    return increment

counter = make_counter()
print(counter())  # 1
print(counter())  # 2
print(counter())  # 3

# Without 'nonlocal', Python treats 'count' as local to increment():
# UnboundLocalError: local variable 'count' referenced before assignment
```

#### Closures Enable Decorators

Decorators are functions that return functions. The returned function "remembers" the original function:

```python
def timing_decorator(func):
    """A decorator that times function execution."""
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)  # Captures 'func' from outer scope
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.4f} seconds")
        return result
    return wrapper

@timing_decorator
def slow_function(n):
    import time
    time.sleep(0.1)
    return n ** 2

slow_function(5)  # Prints: slow_function took 0.1001 seconds
```

#### Closure Pitfall: Late Binding

```python
# ⚠️ COMMON MISTAKE
functions = []
for i in range(3):
    def func():
        return i  # Captures 'i' by reference, not value!
    functions.append(func)

print([f() for f in functions])  # [2, 2, 2] — NOT [0, 1, 2]!

# Fix: Use default arguments to capture by value
functions = []
for i in range(3):
    def func(i=i):  # Default argument captures the current value
        return i
    functions.append(func)

print([f() for f in functions])  # [0, 1, 2] ✓
```

#### Java Comparison

Java's anonymous inner classes have a similar concept:

```java
// Java: effectively final requirement
List<Supplier<Integer>> suppliers = new ArrayList<>();
for (int i = 0; i < 3; i++) {
    final int iCopy = i;  // Must be final (or effectively final)
    suppliers.add(() -> iCopy);
}

// Java requires explicit scoping; Python's closure is implicit but more flexible
```

---

### 3. Basic Decorators

The `@decorator` syntax is syntactic sugar:

```python
@decorator
def func():
    pass

# Is equivalent to:
def func():
    pass
func = decorator(func)
```

#### A Simple Decorator

```python
def log_decorator(func):
    """Decorator that logs function calls."""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@log_decorator
def add(a, b):
    return a + b

add(2, 3)
# Output:
# Calling add with args=(2, 3), kwargs={}
# add returned 5
```

#### The Problem: Lost Metadata

When you decorate a function, you *replace* it with `wrapper`. The original metadata is lost:

```python
@log_decorator
def multiply(a, b):
    """Multiply two numbers."""
    return a * b

print(multiply.__name__)       # 'wrapper' — WRONG!
print(multiply.__doc__)        # None — WRONG!
print(multiply.__annotations__)  # {} — WRONG!
```

This breaks introspection—critical for ADK, which reads function metadata!

#### Solution: `functools.wraps`

```python
import functools

def log_decorator(func):
    @functools.wraps(func)  # Copies metadata from func to wrapper
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}...")
        result = func(*args, **kwargs)
        return result
    return wrapper

@log_decorator
def multiply(a, b):
    """Multiply two numbers."""
    return a * b

print(multiply.__name__)        # 'multiply' ✓
print(multiply.__doc__)         # "Multiply two numbers." ✓
print(multiply.__annotations__) # {} (no type hints in this example)
```

**Always use `functools.wraps`!** ADK's tool registration depends on it.

#### Built-In Decorators

Python has common decorators in the standard library:

##### `@staticmethod`

```python
class MathUtils:
    @staticmethod
    def add(a, b):
        """Static method—no access to self or cls."""
        return a + b

# Call without instantiating
result = MathUtils.add(5, 3)  # 8

# Java equivalent:
# public class MathUtils {
#     public static int add(int a, int b) { return a + b; }
# }
```

##### `@classmethod`

```python
class Counter:
    instances = 0

    def __init__(self):
        Counter.instances += 1

    @classmethod
    def get_instance_count(cls):
        """Classmethod receives the class itself as first argument."""
        return cls.instances

c1 = Counter()
c2 = Counter()
print(Counter.get_instance_count())  # 2
```

**Java equivalent:** A static variable and static method:
```java
public class Counter {
    static int instances = 0;
    static int getInstanceCount() { return instances; }
}
```

##### `@property`

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):
        """Property decorator allows attribute-like access to a method."""
        return self._radius

    @radius.setter
    def radius(self, value):
        if value <= 0:
            raise ValueError("Radius must be positive")
        self._radius = value

    @property
    def area(self):
        import math
        return math.pi * self._radius ** 2

circle = Circle(5)
print(circle.radius)      # 5 (calls the getter)
print(circle.area)        # 78.53981...
circle.radius = 10        # Calls the setter
circle.radius = -1        # Raises ValueError

# Java equivalent:
// public class Circle {
//     private double radius;
//     public double getRadius() { return radius; }
//     public void setRadius(double r) { ... validation ... }
//     public double getArea() { return Math.PI * radius * radius; }
// }
```

---

### 4. Decorators with Arguments

Sometimes you want to *configure* a decorator. This requires a third level of nesting:

```
@decorator(arg1, arg2)
def func():
    pass

# Desugars to:
def func():
    pass
func = decorator(arg1, arg2)(func)
```

The pattern is: **decorator factory → decorated function → wrapper**

#### Pattern: Retry Decorator

```python
import functools
import time

def retry(max_attempts=3, delay=1):
    """Decorator factory that returns a decorator that retries on exception."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_attempts=3, delay=0.5)
def flaky_api_call():
    import random
    if random.random() < 0.7:
        raise ConnectionError("API unreachable")
    return "Success!"

result = flaky_api_call()  # May retry, then succeeds
```

#### Pattern: Rate Limiting

> **Sync-only — unsafe in async ADK code.** This implementation uses `time.sleep()`, which blocks the entire asyncio event loop. Do **not** use it in async ADK tools or agents. For async rate limiting, use `asyncio.Semaphore` (see `python-asyncio-advanced.md` Section 16).

```python
import functools
import time
from collections import deque

def rate_limit(calls_per_second=1):
    """Allow max N calls per second. SYNC ONLY — blocks with time.sleep()."""
    def decorator(func):
        last_calls = deque(maxlen=int(calls_per_second))

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if len(last_calls) == last_calls.maxlen:
                elapsed = now - last_calls[0]
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)  # ⚠️ blocks event loop in async context!

            last_calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(calls_per_second=2)
def api_endpoint():
    print(f"Called at {time.time()}")

# Calling this rapidly will be throttled
for _ in range(5):
    api_endpoint()
```

#### Pattern: Timeout Decorator

```python
import functools
import signal
# Unix/macOS only — signal.SIGALRM is not available on Windows

def timeout(seconds=30):
    """Raise TimeoutError if function takes longer than N seconds."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"{func.__name__} exceeded {seconds}s timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)  # Disable alarm
            return result
        return wrapper
    return decorator

@timeout(seconds=5)
def long_operation():
    import time
    time.sleep(10)  # Will timeout after 5 seconds

# long_operation()  # Raises TimeoutError
```

#### Pattern: Caching Decorator

```python
import functools
import time

def cache(ttl=None):
    """Cache function result, optionally with TTL (time-to-live) in seconds."""
    def decorator(func):
        cache_data = {}
        cache_times = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))

            now = time.time()
            if key in cache_data:
                if ttl is None or (now - cache_times[key]) < ttl:
                    print(f"Cache hit for {func.__name__}{args}")
                    return cache_data[key]

            result = func(*args, **kwargs)
            cache_data[key] = result
            cache_times[key] = now
            return result
        return wrapper
    return decorator

@cache(ttl=5)
def expensive_computation(n):
    print(f"Computing {n}...")
    return n ** 2

print(expensive_computation(5))  # Computes
print(expensive_computation(5))  # Cache hit
time.sleep(6)
print(expensive_computation(5))  # TTL expired, recomputes
```

#### Built-In: `functools.lru_cache`

Python provides `functools.lru_cache` for production caching:

```python
import functools

@functools.lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print(fibonacci(100))  # Instant, cached
print(fibonacci.cache_info())  # CacheInfo(hits=98, misses=101, ...)
fibonacci.cache_clear()  # Clear the cache
```

#### Java Comparison

Java doesn't have true decorator arguments; you'd use annotations with parameters:

```java
// Java: Annotations with parameters (limited compared to Python)
@Retry(maxAttempts = 3, delay = 1000)
public String flakeyApiCall() { ... }

// Java requires boilerplate reflection code to read annotation parameters
// Python's decorator arguments are just regular function arguments!
```

---

### 5. Class-Based Decorators

Instead of nested functions, you can use a class with `__call__`:

```python
import functools

class LogDecorator:
    """Decorator implemented as a class."""

    def __init__(self, func):
        self.func = func
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        print(f"Calling {self.func.__name__}")
        result = self.func(*args, **kwargs)
        print(f"Returned {result}")
        return result

@LogDecorator
def greet(name):
    return f"Hello, {name}!"

print(greet("you"))
```

#### Stateful Class Decorators

Class decorators shine when you need to maintain state:

```python
import functools

class CallCounter:
    """Track how many times a function is called."""

    def __init__(self, func):
        self.func = func
        self.count = 0
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"Call #{self.count}")
        return self.func(*args, **kwargs)

    def reset(self):
        self.count = 0

@CallCounter
def process(data):
    return len(data)

process([1, 2, 3])  # Call #1
process([4, 5])     # Call #2
print(process.count)  # 2
process.reset()
process([])         # Call #1
```

#### Class Decorators with Arguments

Combine `__init__` (setup) and `__call__` (invocation):

```python
import functools
import time

class RateLimit:
    """Rate limiter with configurable threshold."""

    def __init__(self, calls_per_sec=1):
        self.calls_per_sec = calls_per_sec
        self.last_call = 0

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - self.last_call
            min_interval = 1.0 / self.calls_per_sec
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

            self.last_call = time.time()
            return func(*args, **kwargs)
        return wrapper

@RateLimit(calls_per_sec=2)
def api_call():
    print(f"API called at {time.time()}")

for _ in range(3):
    api_call()
```

#### When to Use Class Decorators

- **Stateful**: Need to maintain state between calls
- **Clearer**: Complex logic reads better as methods
- **Inspection**: Can expose debugging info (e.g., `counter.count`)

---

### 6. Decorating Classes

Decorators aren't just for functions—you can decorate classes too!

#### Basic Class Decorator

```python
def add_repr(cls):
    """Add a __repr__ method to a class."""
    original_init = cls.__init__

    def new_repr(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{cls.__name__}({attrs})"

    cls.__repr__ = new_repr
    return cls

@add_repr
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("you", 30)
print(repr(p))  # Person(name='you', age=30)
```

#### `@dataclass` — The Canonical Example

```python
from dataclasses import dataclass

@dataclass
class Tool:
    """Decorator that auto-generates __init__, __repr__, __eq__, etc."""
    name: str
    description: str
    required: bool = False

tool = Tool(name="search", description="Search the web")
print(tool)  # Tool(name='search', description='Search the web', required=False)
print(tool.name)  # 'search'

# Equivalent to writing:
# class Tool:
#     def __init__(self, name: str, description: str, required: bool = False):
#         self.name = name
#         self.description = description
#         self.required = required
#
#     def __repr__(self):
#         return f"Tool(name={self.name!r}, description={self.description!r}, required={self.required!r})"
#
#     def __eq__(self, other):
#         ...
```

#### Custom Class Decorator: Registration

```python
# Global registry
MODELS = {}

def register_model(cls):
    """Register a model class by its name."""
    MODELS[cls.__name__] = cls
    return cls

@register_model
class GPTModel:
    def __init__(self):
        self.name = "gpt-4"

@register_model
class ClaudeModel:
    def __init__(self):
        self.name = "claude-3"

print(MODELS)  # {'GPTModel': <class GPTModel>, 'ClaudeModel': <class ClaudeModel>}
model = MODELS["GPTModel"]()  # Instantiate by name
```

---

### 7. The `inspect` Module — Reading Function Metadata

The `inspect` module is **critical** for ADK. It lets you read a function's signature, type hints, and parameter details—exactly what ADK needs to auto-generate tool schemas.

#### Getting a Function Signature

```python
import inspect

def create_user(name: str, email: str, age: int = 18) -> dict:
    """Create a new user."""
    return {"name": name, "email": email, "age": age}

sig = inspect.signature(create_user)
print(sig)  # (name: str, email: str, age: int = 18) -> dict

# Access parameters
for param_name, param in sig.parameters.items():
    print(f"  {param_name}: {param.annotation}, default={param.default}")

# Output:
#   name: <class 'str'>, default=inspect.Parameter.empty
#   email: <class 'str'>, default=inspect.Parameter.empty
#   age: <class 'int'>, default=18
```

#### Parameter Objects

```python
import inspect

sig = inspect.signature(create_user)
param = sig.parameters['age']

print(param.name)           # 'age'
print(param.annotation)     # <class 'int'>
print(param.default)        # 18
print(param.kind)           # ParameterKind.POSITIONAL_OR_KEYWORD
```

#### Parameter Kinds

```python
import inspect

def example(a, /, b, *args, c, **kwargs):
    #        ^  ^  ^      ^  ^
    #        |  |  |      |  |____ VAR_KEYWORD (kwargs)
    #        |  |  |      |_______ KEYWORD_ONLY (c)
    #        |  |  |_____________ VAR_POSITIONAL (*args)
    #        |  |________________ POSITIONAL_OR_KEYWORD (b)
    #        |___________________ POSITIONAL_ONLY (a, / syntax)
    pass

sig = inspect.signature(example)
for name, param in sig.parameters.items():
    print(f"{name}: {param.kind.name}")

# Output:
# a: POSITIONAL_ONLY
# b: POSITIONAL_OR_KEYWORD
# args: VAR_POSITIONAL
# c: KEYWORD_ONLY
# kwargs: VAR_KEYWORD
```

#### Type Hints with `get_type_hints`

```python
import inspect
import typing
from typing import Optional

def send_message(user_id: int, message: str, urgency: Optional[str] = None) -> bool:
    """Send a message to a user."""
    return True

hints = typing.get_type_hints(send_message)
print(hints)
# {'user_id': <class 'int'>, 'message': <class 'str'>, 'urgency': typing.Optional[str], 'return': <class 'bool'>}

# Note: get_type_hints resolves forward references and Union types
# inspect.signature().parameters don't—they show the raw string
```

#### Complete Example: Generating a JSON Schema from a Function

This illustrates the concept ADK uses; ADK delegates to Pydantic's `model_json_schema()` for full type support rather than the manual type mapping shown here:

```python
import inspect
import json
from typing import get_type_hints, get_origin, get_args

def function_to_schema(func) -> dict:
    """Convert a function signature into a JSON schema for a tool."""
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls'):
            continue

        param_type = hints.get(param_name, str)

        # Convert Python type to JSON schema type
        json_type = "string"
        if param_type == int:
            json_type = "integer"
        elif param_type == float:
            json_type = "number"
        elif param_type == bool:
            json_type = "boolean"
        elif get_origin(param_type) == list:
            json_type = "array"

        prop = {
            "type": json_type,
            "description": ""
        }

        # Check if parameter is required
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
        else:
            prop["default"] = param.default

        properties[param_name] = prop

    return {
        "name": func.__name__,
        "description": func.__doc__ or "",
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }

# Example usage
def search(query: str, limit: int = 10) -> list:
    """Search for documents matching the query."""
    pass

schema = function_to_schema(search)
print(json.dumps(schema, indent=2))

# Output:
# {
#   "name": "search",
#   "description": "Search for documents matching the query.",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "query": {
#         "type": "string",
#         "description": ""
#       },
#       "limit": {
#         "type": "integer",
#         "description": "",
#         "default": 10
#       }
#     },
#     "required": ["query"]
#   }
# }
```

#### Java Comparison

```java
// Java requires reflection at runtime:
Method method = myClass.getMethod("search", String.class, int.class);
Parameter[] params = method.getParameters();
// Then you manually extract type info—Python's inspect is simpler
```

---

## ADK in Practice

| Decorator Pattern | ADK Usage |
|---|---|
| `@functools.wraps` | Preserve `__name__` and `__doc__` so ADK can read tool metadata |
| `inspect.signature()` | ADK reads function signatures to extract parameter names and types |
| `typing.get_type_hints()` | ADK resolves type annotations for schema generation |
| Pydantic `model_json_schema()` | ADK's actual schema generation — delegates to Pydantic, not manual type mapping |
| Decorator with arguments | Tool registration patterns, callback configuration |

---

> **Continued in [python-metaprogramming-deep-dive.md](python-metaprogramming-deep-dive.md)** — descriptors, metaclasses, `__init_subclass__`, the registry pattern, `functools` toolkit, ADK-specific patterns, decorator stacking, and common pitfalls.

