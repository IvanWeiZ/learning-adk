# Python Metaprogramming — Deep Dive

> **Part 1 is in [python-decorators-deep-dive.md](python-decorators-deep-dive.md)** — closures, basic decorators, decorators with arguments, class-based decorators, decorating classes, and the `inspect` module.

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

This file covers Sections 8–14: descriptors, `__init_subclass__`, metaclasses, `functools` utilities, `__slots__`, dynamic class creation, and the tool registry pattern.

---

### 8. Descriptors

A **descriptor** is an object that implements `__get__`, `__set__`, or `__delete__`. They allow you to customize attribute access.

#### Basic Descriptor

```python
class PositiveInt:
    """Descriptor that only allows positive integers."""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, None)

    def __set__(self, obj, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{self.name} must be a positive integer")
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        del obj.__dict__[self.name]

class Product:
    price = PositiveInt()

    def __init__(self, name, price):
        self.name = name
        self.price = price

p = Product("Laptop", 999)
print(p.price)  # 999
p.price = -50   # Raises ValueError
```

#### How `@property` Works

`@property` is a built-in descriptor:

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def fahrenheit(self):
        """Getter: convert to Fahrenheit."""
        return self._celsius * 9/5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value):
        """Setter: convert from Fahrenheit."""
        self._celsius = (value - 32) * 5/9

t = Temperature(0)
print(t.fahrenheit)     # 32.0
t.fahrenheit = 212      # Sets _celsius to 100
print(t._celsius)       # 100.0
```

Under the hood, `property` is a descriptor that intercepts `.` access.

#### Validation Descriptor

```python
class ValidatedString:
    """A descriptor that validates string attributes."""

    def __init__(self, min_length=0, max_length=None):
        self.min_length = min_length
        self.max_length = max_length

    def __set_name__(self, owner, name):
        self.name = f"_{name}"  # Store internally as _attr

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.name, None)

    def __set__(self, obj, value):
        if not isinstance(value, str):
            raise TypeError(f"Must be a string")
        if len(value) < self.min_length:
            raise ValueError(f"Must be at least {self.min_length} chars")
        if self.max_length and len(value) > self.max_length:
            raise ValueError(f"Must be at most {self.max_length} chars")
        setattr(obj, self.name, value)

class User:
    username = ValidatedString(min_length=3, max_length=20)

    def __init__(self, username):
        self.username = username

u = User("wei")
print(u.username)  # 'wei'
u.username = "a"   # Raises ValueError
```

---

### 9. `__init_subclass__` — Auto-Registration on Subclassing

When a class is subclassed, `__init_subclass__` is called. This is perfect for auto-registration patterns.

#### Basic Registry Pattern

```python
class ToolRegistry:
    """Base class for auto-registering tool types."""
    tools = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register this subclass
        ToolRegistry.tools[cls.__name__] = cls

class SearchTool(ToolRegistry):
    def execute(self, query):
        return f"Searching for {query}"

class CalculatorTool(ToolRegistry):
    def execute(self, expr):
        return eval(expr)

class DatabaseTool(ToolRegistry):
    def execute(self, query):
        return f"Query: {query}"

print(ToolRegistry.tools)
# {'SearchTool': <class SearchTool>, 'CalculatorTool': <class CalculatorTool>, ...}

# Instantiate by name
tool_class = ToolRegistry.tools['SearchTool']
tool = tool_class()
print(tool.execute("Python decorators"))
```

#### Registry with Configuration

```python
class Plugin:
    """Base plugin class with registration."""
    plugins = {}

    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register with a custom name
        plugin_name = name or cls.__name__
        Plugin.plugins[plugin_name] = cls

class EmailPlugin(Plugin, name="email"):
    """Register as 'email' instead of 'EmailPlugin'."""
    pass

class SlackPlugin(Plugin, name="slack"):
    pass

print(Plugin.plugins)  # {'email': <class EmailPlugin>, 'slack': <class SlackPlugin>}
```

#### ADK-Like Agent Registry

```python
class Agent:
    """Base class for auto-registering agent types."""
    agents = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Agent.agents[cls.__name__] = cls
        print(f"Registered agent: {cls.__name__}")

class ReasoningAgent(Agent):
    """An agent that reasons step-by-step."""
    pass

class RAGAgent(Agent):
    """An agent that uses retrieval-augmented generation."""
    pass

# Output:
# Registered agent: ReasoningAgent
# Registered agent: RAGAgent

# Later, instantiate by name
agent_class = Agent.agents['ReasoningAgent']
agent = agent_class()
```

#### Java Comparison

```java
// Java: ServiceLoader pattern (similar intent)
public interface Tool {
    void execute();
}

// Create a service provider interface config file:
// META-INF/services/com.example.Tool
// with content:
// com.example.SearchTool
// com.example.CalculatorTool

// Then at runtime:
ServiceLoader<Tool> loader = ServiceLoader.load(Tool.class);
for (Tool tool : loader) {
    tool.execute();
}

// Python's __init_subclass__ is more direct!
```

---

### 10. Metaclasses

> **ADK note:** Metaclasses are rarely written in ADK code. Their main use is *reading* existing code — Pydantic and ABCs use metaclasses internally. For new ADK components, prefer `__init_subclass__` (Section 9) unless you have a specific metaclass requirement.

A **metaclass** is a "class of a class"—it defines how a class behaves. `type` is Python's default metaclass.

#### Understanding `type`

```python
class Dog:
    """A simple class."""
    pass

# The metaclass of Dog is 'type'
print(type(Dog))        # <class 'type'>
print(isinstance(Dog, type))  # True

# type itself is its own metaclass
print(type(type))       # <class 'type'>

# You can use type() to dynamically create classes
Dog = type('Dog', (), {'bark': lambda self: 'Woof!'})
dog = Dog()
print(dog.bark())       # 'Woof!'
```

#### Custom Metaclass

```python
class SingletonMeta(type):
    """Metaclass that ensures only one instance of a class exists."""
    instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in SingletonMeta.instances:
            SingletonMeta.instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta.instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self, url):
        self.url = url

db1 = Database("localhost")
db2 = Database("remote")  # Different URL, but same instance
print(db1 is db2)  # True
print(db1.url)     # "localhost" (original instance)
```

#### Metaclass `__new__` vs `__init__`

```python
class TrackedMeta(type):
    """Metaclass that tracks class creation."""

    def __new__(mcs, name, bases, dct):
        print(f"__new__: Creating class {name}")
        return super().__new__(mcs, name, bases, dct)

    def __init__(cls, name, bases, dct):
        print(f"__init__: Initializing class {name}")
        super().__init__(name, bases, dct)

class MyClass(metaclass=TrackedMeta):
    pass

# Output:
# __new__: Creating class MyClass
# __init__: Initializing class MyClass

# __new__ creates the class object itself
# __init__ is called on the newly created class object
```

#### Combining Metaclass with `__init_subclass__`

Often, `__init_subclass__` is simpler and more modern:

```python
# OLD: Metaclass approach
class RegistryMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)
        if name != 'Base':
            Base.registry[name] = cls
        return cls

class Base(metaclass=RegistryMeta):
    registry = {}

# MODERN: __init_subclass__ approach (preferred)
class Base:
    registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Base.registry[cls.__name__] = cls
```

**Use `__init_subclass__` unless you have a specific metaclass need.**

#### Java Comparison

Java doesn't have metaclasses; the closest analogy is compile-time annotations with annotation processors.

---

### 11. The Registry Pattern — Complete Implementation

A registry is a central repository that maps names to classes/functions. ADK uses this for tools, callbacks, etc.

#### Simple Function Registry

```python
class FunctionRegistry:
    """Registry for dynamically discovered functions."""

    def __init__(self):
        self.functions = {}

    def register(self, name=None):
        """Decorator to register a function."""
        def decorator(func):
            key = name or func.__name__
            self.functions[key] = func
            return func
        return decorator

    def get(self, name):
        """Retrieve a registered function."""
        return self.functions.get(name)

    def list(self):
        """List all registered functions."""
        return list(self.functions.keys())

# Global registry instance
TOOLS = FunctionRegistry()

@TOOLS.register()
def search(query: str) -> list:
    """Search for documents."""
    return [f"Result for {query}"]

@TOOLS.register(name="fetch")
def retrieve(url: str) -> str:
    """Fetch a URL."""
    return f"Content from {url}"

print(TOOLS.list())  # ['search', 'fetch']
tool = TOOLS.get('search')
print(tool("Python"))  # ['Result for Python']
```

#### Class Registry with Introspection

```python
import inspect
import typing

class ToolRegistry:
    """Registry that auto-generates schemas from functions."""

    def __init__(self):
        self.tools = {}

    def register(self, **options):
        """Decorator to register a tool function."""
        def decorator(func):
            sig = inspect.signature(func)
            hints = typing.get_type_hints(func)

            # Build schema
            schema = {
                "name": func.__name__,
                "description": func.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }

            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'cls'):
                    continue

                param_type = hints.get(param_name, str)
                json_type = "string"
                if param_type == int:
                    json_type = "integer"
                elif param_type == float:
                    json_type = "number"
                elif param_type == bool:
                    json_type = "boolean"

                schema["parameters"]["properties"][param_name] = {"type": json_type}

                if param.default == inspect.Parameter.empty:
                    schema["parameters"]["required"].append(param_name)

            # Store function and schema
            self.tools[func.__name__] = {
                "function": func,
                "schema": schema,
                "options": options
            }
            return func
        return decorator

    def get_schema(self, name):
        """Get the schema for a tool."""
        return self.tools[name]["schema"]

    def call(self, name, **kwargs):
        """Call a registered tool."""
        tool_entry = self.tools[name]
        return tool_entry["function"](**kwargs)

# Usage
REGISTRY = ToolRegistry()

@REGISTRY.register(category="search")
def web_search(query: str, limit: int = 10) -> list:
    """Search the web for a query."""
    return [f"Result {i}" for i in range(limit)]

@REGISTRY.register(category="compute")
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    # ⚠️ WARNING: eval() is a serious security risk — never use in production ADK tools.
    # An LLM could pass arbitrary Python code as the expression argument.
    # Use a safe arithmetic library (e.g., simpleeval) or a whitelist parser instead.
    return eval(expression)  # noqa: S307 — illustration only, not for production

# Inspect
print(REGISTRY.get_schema("web_search"))
# Call
results = REGISTRY.call("web_search", query="Python", limit=5)
print(results)
```

#### Auto-Discovery Registry

```python
import pkgutil
import importlib
import inspect

class PluginRegistry:
    """Auto-discover and register plugins from a package."""

    def __init__(self):
        self.plugins = {}

    def discover(self, package_name):
        """Discover all plugins in a package."""
        package = importlib.import_module(package_name)
        prefix = package.__name__ + "."

        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
            module = importlib.import_module(modname)

            # Find classes decorated with @plugin
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, '_is_plugin'):
                    self.plugins[name] = obj

    def list_plugins(self):
        return list(self.plugins.keys())

def plugin(cls):
    """Decorator to mark a class as a plugin."""
    cls._is_plugin = True
    return cls

# Usage would look like:
# @plugin
# class DataPlugin:
#     pass
#
# registry = PluginRegistry()
# registry.discover('my_plugins')
```

#### Java Comparison

```java
// Java: Similar pattern with reflection
public class ToolRegistry {
    private Map<String, Class<?>> tools = new HashMap<>();

    public void register(String name, Class<?> toolClass) {
        tools.put(name, toolClass);
    }

    public Object call(String name, Object... args) throws Exception {
        Class<?> toolClass = tools.get(name);
        Method method = toolClass.getMethod("execute", /* param types */);
        return method.invoke(null, args);  // Static call
    }
}

// Python's decorator approach is cleaner!
```

---

### 12. `functools` Toolkit

#### `functools.wraps`

> **See:** [python-decorators-deep-dive.md](python-decorators-deep-dive.md) — Section 3 covers `functools.wraps` in depth, including what attributes it copies (`__name__`, `__doc__`, `__annotations__`, `__wrapped__`) and why it matters for introspection.

Essential: `@functools.wraps(func)` on your wrapper function copies metadata (`__name__`, `__doc__`, `__annotations__`, `__wrapped__`) from the original function. ADK relies on this for tool schema generation from function signatures.

#### `functools.partial`

Create a new function with some arguments pre-filled:

```python
import functools

def power(base, exponent):
    return base ** exponent

square = functools.partial(power, exponent=2)
cube = functools.partial(power, exponent=3)

print(square(5))  # 25
print(cube(5))    # 125

# Another example
def multiply(a, b, c):
    return a * b * c

double = functools.partial(multiply, b=2, c=1)
print(double(5))  # 10 (5 * 2 * 1)
```

#### `functools.lru_cache`

Memoize function results with an LRU (Least Recently Used) eviction policy:

```python
import functools

@functools.lru_cache(maxsize=128)
def expensive_function(n):
    print(f"Computing {n}...")
    return n ** 2

expensive_function(5)  # Computing 5...
expensive_function(5)  # (cached, no output)
expensive_function(10)  # Computing 10...

print(expensive_function.cache_info())
# CacheInfo(hits=1, misses=2, maxsize=128, currsize=2)

expensive_function.cache_clear()  # Clear the cache
```

#### `functools.cache` (Python 3.9+)

Simpler version of `lru_cache` with no size limit:

```python
import functools

@functools.cache
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(30))  # Fast with caching
```

#### `functools.singledispatch`

Method overloading based on type:

```python
import functools

@functools.singledispatch
def process(arg):
    print(f"Default handler: {arg}")

@process.register(int)
def _(arg):
    print(f"Handling int: {arg}")

@process.register(str)
def _(arg):
    print(f"Handling str: {arg}")

@process.register(list)
def _(arg):
    print(f"Handling list with {len(arg)} items")

process(42)         # Handling int: 42
process("hello")    # Handling str: hello
process([1, 2, 3])  # Handling list with 3 items
process(3.14)       # Default handler: 3.14
```

#### `functools.singledispatchmethod`

Like `singledispatch` but for class methods:

```python
import functools

class Converter:
    @functools.singledispatchmethod
    def convert(self, arg):
        print(f"Default conversion: {arg}")

    @convert.register(int)
    def _(self, arg):
        print(f"Convert int to string: '{arg}'")

    @convert.register(str)
    def _(self, arg):
        print(f"Convert string to int: {int(arg)}")

c = Converter()
c.convert(42)      # Convert int to string: '42'
c.convert("100")   # Convert string to int: 100
```

#### `functools.reduce`

Apply a function cumulatively to items:

```python
import functools

numbers = [1, 2, 3, 4, 5]
product = functools.reduce(lambda a, b: a * b, numbers)
print(product)  # 120 (1*2*3*4*5)

# With initial value
product = functools.reduce(lambda a, b: a * b, numbers, 10)
print(product)  # 1200 (10*1*2*3*4*5)
```

#### `functools.total_ordering`

Reduce repetition when implementing comparison methods:

```python
import functools

@functools.total_ordering
class Version:
    def __init__(self, major, minor):
        self.major = major
        self.minor = minor

    def __eq__(self, other):
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other):
        return (self.major, self.minor) < (other.major, other.minor)

v1 = Version(1, 2)
v2 = Version(1, 3)
print(v1 < v2)   # True
print(v1 <= v2)  # True (auto-generated)
print(v1 > v2)   # False (auto-generated)
```

---

### 13. ADK-Specific Patterns

#### Building a `@register_tool` Decorator

> **See:** [python-decorators-deep-dive.md](python-decorators-deep-dive.md) — The `function_to_schema` pattern (using `inspect.signature()` + `typing.get_type_hints()` + a `type_map`) is covered in detail there. The example below focuses on the registry wrapping class; the schema extraction logic follows the same pattern.

A decorator that reads a function's signature, generates a schema, and registers it in a central registry. The pattern: (1) use `@functools.wraps(func)` to preserve metadata, (2) call `inspect.signature()` and `typing.get_type_hints()` to extract parameter types, (3) map those types to JSON schema, (4) store both the function and its schema for later lookup. ADK's `FunctionTool` uses the same technique to auto-generate tool declarations sent to the LLM.

#### Building a Callback Registration System

```python
import functools
from typing import Callable, List

class CallbackManager:
    """Manage callbacks for different lifecycle events."""

    def __init__(self):
        self._callbacks = {}

    def on(self, event: str):
        """Register a callback for an event."""
        def decorator(func):
            if event not in self._callbacks:
                self._callbacks[event] = []
            self._callbacks[event].append(func)
            return func
        return decorator

    def trigger(self, event: str, *args, **kwargs):
        """Trigger all callbacks for an event."""
        callbacks = self._callbacks.get(event, [])
        results = []
        for callback in callbacks:
            result = callback(*args, **kwargs)
            results.append(result)
        return results

# Usage
callbacks = CallbackManager()

@callbacks.on("agent_created")
def log_creation(agent_name: str):
    print(f"Agent {agent_name} created")

@callbacks.on("agent_created")
def notify_creation(agent_name: str):
    print(f"Notifying listeners about {agent_name}")

@callbacks.on("agent_destroyed")
def cleanup(agent_name: str):
    print(f"Cleaning up {agent_name}")

# Trigger events
callbacks.trigger("agent_created", agent_name="ReasoningAgent")
callbacks.trigger("agent_destroyed", agent_name="ReasoningAgent")
```

#### Building a Plugin System

```python
import functools
import inspect
from typing import Dict, Any

class PluginSystem:
    """Extensible plugin architecture."""

    def __init__(self):
        self._hooks = {}  # hook_name -> [plugin_funcs]

    def register_hook(self, hook_name: str):
        """Decorator to register a plugin function to a hook."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            if hook_name not in self._hooks:
                self._hooks[hook_name] = []

            self._hooks[hook_name].append(wrapper)
            return wrapper
        return decorator

    def run_hook(self, hook_name: str, *args, **kwargs):
        """Execute all plugins registered to a hook."""
        if hook_name not in self._hooks:
            return []

        results = []
        for plugin_func in self._hooks[hook_name]:
            try:
                result = plugin_func(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Plugin {plugin_func.__name__} failed: {e}")

        return results

# Usage
plugins = PluginSystem()

@plugins.register_hook("before_inference")
def validate_input(data: Dict[str, Any]) -> bool:
    """Validate input before inference."""
    print(f"Validating {len(data)} fields")
    return True

@plugins.register_hook("before_inference")
def log_inference(data: Dict[str, Any]) -> None:
    """Log inference request."""
    print(f"Starting inference with {data}")

@plugins.register_hook("after_inference")
def cache_result(result: Any) -> None:
    """Cache inference result."""
    print(f"Caching result: {result}")

# Run hooks
plugins.run_hook("before_inference", data={"query": "Hello"})
plugins.run_hook("after_inference", result="Response")
```

---

### 14. Stacking Decorators

When multiple decorators are applied, they execute in a specific order.

#### Decorator Stacking — Onion Diagram

```
@decorator_a          Execution order (call):
@decorator_b          ┌─────────────────────────────────┐
def greet(name):      │ decorator_a (outer)              │
                      │   ┌─────────────────────────┐    │
Definition order:     │   │ decorator_b (inner)      │    │
greet =               │   │   ┌─────────────────┐    │    │
  decorator_a(        │   │   │ greet(name)      │    │    │
    decorator_b(      │   │   │  "Hello, you!"   │    │    │
      greet           │   │   └─────────────────┘    │    │
    )                 │   │  B: after                 │    │
  )                   │   └─────────────────────────┘    │
                      │  A: after                        │
                      └─────────────────────────────────┘

Bottom decorator (B) wraps first, so it is closest to the
original function.  Outermost decorator (A) runs first on
call, like peeling an onion from the outside in.
```

```python
def decorator_a(func):
    def wrapper(*args, **kwargs):
        print("A: before")
        result = func(*args, **kwargs)
        print("A: after")
        return result
    return wrapper

def decorator_b(func):
    def wrapper(*args, **kwargs):
        print("B: before")
        result = func(*args, **kwargs)
        print("B: after")
        return result
    return wrapper

@decorator_a
@decorator_b
def greet(name):
    print(f"Hello, {name}!")

greet("you")

# Output:
# A: before
# B: before
# Hello, you!
# B: after
# A: after

# Why? Decorator stacking works from bottom-up for definition,
# but the execution wraps from top-down:
# greet = decorator_a(decorator_b(greet))
```

#### Order Matters

```python
import functools
import time

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

def time_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"Took {elapsed:.4f}s")
        return result
    return wrapper

# Order 1: Log first, then time
@time_calls
@log_calls
def process_1(data):
    time.sleep(0.1)
    return len(data)

# Order 2: Time first, then log
@log_calls
@time_calls
def process_2(data):
    time.sleep(0.1)
    return len(data)

print("Order 1:")
process_1([1, 2, 3])
# Calling process_1
# Took 0.1001s

print("\nOrder 2:")
process_2([1, 2, 3])
# Took 0.1001s
# Calling process_2

# Different orders yield different log messages!
# Choose the order that matches your intent.
```

#### Real-World ADK Stacking

```python
import functools

def log(func):
    """Log function calls."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

def rate_limit(calls_per_sec=1):
    """Rate limit function calls."""
    def decorator(func):
        import time
        last_call = [0]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < 1.0 / calls_per_sec:
                time.sleep(1.0 / calls_per_sec - elapsed)
            last_call[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def cache(func):
    """Cache results."""
    cache_data = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(kwargs.items()))
        if key in cache_data:
            print(f"[CACHE] Hit for {func.__name__}")
            return cache_data[key]
        result = func(*args, **kwargs)
        cache_data[key] = result
        return result
    return wrapper

@log
@rate_limit(calls_per_sec=1)
@cache
def fetch_user(user_id: int):
    """Fetch a user (rate limited and cached)."""
    print(f"[FETCH] Getting user {user_id}")
    return {"id": user_id, "name": f"User{user_id}"}

# First call: fetch + rate limit + log
result = fetch_user(1)
# [LOG] Calling fetch_user
# [FETCH] Getting user 1

# Second call (same args): uses cache
result = fetch_user(1)
# [LOG] Calling fetch_user
# [CACHE] Hit for fetch_user

# Third call (different args): fetch + rate limit + log
result = fetch_user(2)
# [LOG] Calling fetch_user
# [FETCH] Getting user 2
```

---

### 15. Common Pitfalls

#### Pitfall 1: Forgetting `@functools.wraps`

```python
# ❌ WRONG
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

print(greet.__name__)  # 'wrapper' — WRONG!
print(greet.__doc__)   # None — WRONG!

# ✓ CORRECT
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("Before")
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

print(greet.__name__)  # 'greet' ✓
print(greet.__doc__)   # 'Greet someone.' ✓
```

#### Pitfall 2: Decorator Argument Confusion

```python
# ❌ WRONG — You'll get "1 positional argument" error
def retry(func, max_attempts=3):  # 'func' is required!
    def wrapper(*args, **kwargs):
        for _ in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except:
                pass
    return wrapper

# @retry(max_attempts=5)  # ERROR: missing 'func' argument!

# ✓ CORRECT — Use a nested function (decorator factory)
def retry(max_attempts=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except:
                    pass
        return wrapper
    return decorator

@retry(max_attempts=5)  # Correct!
def flaky_function():
    pass
```

#### Pitfall 3: Late Binding in Closures

```python
# ❌ WRONG
decorators = []
for i in range(3):
    def my_decorator(func):
        def wrapper(*args, **kwargs):
            print(f"Decorator {i}")  # Captures 'i' by reference!
            return func(*args, **kwargs)
        return wrapper
    decorators.append(my_decorator)

def func():
    pass

for dec in decorators:
    func = dec(func)

func()  # Prints "Decorator 2" three times (i=2 at the end)

# ✓ CORRECT — Use default arguments
decorators = []
for i in range(3):
    def my_decorator(func, i=i):  # Capture current i
        def wrapper(*args, **kwargs):
            print(f"Decorator {i}")
            return func(*args, **kwargs)
        return wrapper
    decorators.append(my_decorator)
```

#### Pitfall 4: Decorating Async Functions

```python
# ❌ WRONG — Loses async nature
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        return func(*args, **kwargs)  # Doesn't await!
    return wrapper

@my_decorator
async def async_function():
    import asyncio
    await asyncio.sleep(1)
    return "Done"

# This will return a coroutine, not run the async function

# ✓ CORRECT — Handle async
import asyncio
import functools

def async_decorator(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        print("Before")
        return await func(*args, **kwargs)
    return wrapper

@async_decorator
async def async_function():
    await asyncio.sleep(1)
    return "Done"

# Now it works correctly
# asyncio.run(async_function())  # "Before", then "Done"
```

#### Pitfall 5: Mutable Default Arguments

```python
# ❌ WRONG — Default argument is shared across calls
def register(name, tags=[]):  # Mutable default!
    tags.append(name)
    return tags

print(register("tool1"))  # ['tool1']
print(register("tool2"))  # ['tool1', 'tool2'] — unexpected!

# ✓ CORRECT — Use None and initialize inside
def register(name, tags=None):
    if tags is None:
        tags = []
    tags.append(name)
    return tags

print(register("tool1"))  # ['tool1']
print(register("tool2"))  # ['tool2'] ✓
```

---

## Java to Python Metaprogramming Reference

| Java Concept | Python Equivalent | Notes |
|---|---|---|
| **Annotations** | Decorators | `@decorator` vs `@Annotation`; Python decorators are functions, not metadata |
| **Reflection** | `inspect` module | `inspect.signature()`, `typing.get_type_hints()` read function/class metadata |
| **Functional Interface** | First-class functions | Functions are objects; no interface wrapper needed |
| **Method Overloading** | `functools.singledispatch` | Single function with multiple implementations based on type |
| **Abstract Classes** | Abstract base classes (`abc`) | `@abstractmethod` decorator |
| **ServiceLoader** | `__init_subclass__` or metaclasses | Auto-registration when subclasses are defined |
| **Getters/Setters** | `@property` decorator | Attribute-like syntax without get/set boilerplate |
| **Static Methods** | `@staticmethod` decorator | Similar to Java's `static` keyword |
| **Class Methods** | `@classmethod` decorator | Receives class as first argument, like static with class context |
| **Generics** | Type Hints (`typing` module) | Not enforced at runtime (but inspectable) |
| **Compile-Time Safety** | Type Checkers (`mypy`, `pyright`) | Runtime is dynamic; use static type checkers for safety |
| **Inner Classes** | Nested classes or closures | Python's closures are simpler and more powerful |
| **Custom Metaclasses** | Metaclasses | Rarely needed; `__init_subclass__` is usually better |
| **Reflection API** | `__dict__`, `vars()`, `dir()` | Direct attribute access; simpler than Java's reflection |
| **Method.invoke()** | `getattr()` and `()` | Direct function calls; simpler than Java's `Method.invoke()` |
| **Class.forName()** | `importlib.import_module()` | Dynamic imports; similar dynamic class loading |

---

## ADK in Practice

ADK uses every metaprogramming concept in this guide:

| Concept | ADK Usage |
|---|---|
| `inspect.signature()` | Auto-generates tool schemas from function type hints |
| `functools.wraps` | Preserves function metadata through decorator chains |
| `__init_subclass__` | LLM registry auto-registers model adapters |
| Closures | Callback factories that capture configuration |
| Class decorators | `@dataclass` for lightweight data objects |
| `functools.partial` | Pre-configuring tool functions with fixed arguments |
| `functools.singledispatch` | Type-based dispatch for different event handling |
| Descriptor protocol | `@property` for computed agent attributes |

## Common Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Forgetting `@functools.wraps` | ADK can't read `__name__`/`__doc__` for tool schemas | Always use `@functools.wraps(func)` |
| Decorator argument confusion | `TypeError: missing positional argument` | Use three-level nesting (factory -> decorator -> wrapper) |
| Late binding in closures | All closures capture final loop value | Use default argument `def f(i=i):` |
| Decorating async with sync wrapper | Returns coroutine object instead of result | Use `async def wrapper` for async functions |
| Mutable default arguments | Shared state across calls | Use `None` default, create inside function |

## Quick Reference Card

```
Key Takeaways:

1. Functions are objects — pass them, store them, inspect them
2. @decorator = func = decorator(func) — syntactic sugar
3. Always use @functools.wraps — ADK reads function metadata
4. Decorator with args: @dec(arg) = func = dec(arg)(func)
5. inspect.signature() + get_type_hints() = tool schema generation
6. __init_subclass__ = auto-registration (simpler than metaclasses)
7. Descriptors = custom attribute access (@property is the canonical example)
8. functools toolkit: wraps, partial, lru_cache, singledispatch
9. @dataclass = powerful class decorator for data objects
10. Decorator stacking order matters — bottom decorator wraps first
```

---

