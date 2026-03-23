# Python Gotchas for Java Developers

> **ADK relevance:** These traps appear in every ADK codebase — agents, tools, callbacks, state management. Knowing them saves hours of debugging. | **Estimated time:** 45 min

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

This is not a syntax guide (see [java-to-python-cheat-sheet.md](../reference/java-to-python-cheat-sheet.md)). This is a list of things that **look right but break at runtime** because Python works differently than Java under the hood.

---

## At a Glance

```
Java Developer Instinct              Python Reality
─────────────────────────            ──────────────
"Variables hold objects"         →   Variables are name tags on objects
"Default args are per-call"      →   Default args are evaluated ONCE
"Blocks create scope"            →   Only functions/classes create scope
"Private means private"          →   _underscore is a suggestion
"Threads run in parallel"        →   GIL: one thread executes at a time
"== checks value"                →   True, but use 'is' for None/True/False
"Empty means null"               →   Empty collections are falsy, not None
"Copy copies"                    →   Shallow copy shares nested objects
"Overloading works"              →   Last definition wins silently
```

---

<!-- Group 1: Semantics (Gotchas 1–6) -->

## 1. The Mutable Default Argument Trap

The single most common Python bug for Java developers.

**Java mental model:** Default parameter values are fresh each call.

**Python reality:** Default values are evaluated **once** at function definition time and **shared** across all calls.

```python
# WRONG — shared list across all calls
def add_tool(name: str, tools: list[str] = []):
    tools.append(name)
    return tools

add_tool("search")   # ['search']
add_tool("fetch")    # ['search', 'fetch']  — surprise!

# RIGHT — use None sentinel
def add_tool(name: str, tools: list[str] | None = None):
    if tools is None:
        tools = []
    tools.append(name)
    return tools
```

**ADK context:** This affects any callback or tool function with dict/list defaults. Pydantic handles this with `Field(default_factory=list)`.

---

## 2. Variables Are Name Tags, Not Boxes

In Java, `a = b` copies the reference. In Python it's the same — but Java developers forget this applies to **everything**, including lists and dicts.

```python
# Assignment does NOT copy
config = {"model": "gemini-2.0-flash"}
backup = config               # same object!
backup["model"] = "gpt-4o"
print(config["model"])        # 'gpt-4o' — both changed

# Shallow copy — nested objects still shared
import copy
a = {"tools": ["search", "fetch"]}
b = a.copy()                  # or dict(a) or {**a}
b["tools"].append("browse")
print(a["tools"])             # ['search', 'fetch', 'browse'] — surprise!

# Deep copy — fully independent
c = copy.deepcopy(a)
c["tools"].append("execute")
print(a["tools"])             # unchanged
```

**Java equivalent:** Java has primitive types (`int[]`, `long`) with value semantics — Python has no such types. In Python, **everything** is an object with reference semantics, including ints and strings (though those are immutable). `clone()` in Java is shallow by default, but Python also lacks any `clone()` at all — you must use `copy.copy()` or `copy.deepcopy()` explicitly.

**ADK context:** Session `state` is a dict. If you store a list in state and pass it around, mutations propagate. Always copy before modifying:

```python
# In a tool function (simplified example — actual ADK uses session.state)
tools_list = list(session_state["available_tools"])  # copy!
tools_list.append("new_tool")
session_state["available_tools"] = tools_list
```

---

## 3. Identity vs Equality

Java has `==` (identity for objects) and `.equals()` (value). Python has `==` (value) and `is` (identity) — the **opposite** default.

```python
# == checks value (like .equals())
[1, 2] == [1, 2]       # True

# 'is' checks identity (like Java ==)
[1, 2] is [1, 2]       # False — different objects

# GOTCHA: small integer caching
a = 256
b = 256
a is b                  # True — Python caches -5 to 256

a = 257
b = 257
a is b                  # False (usually) — not cached!

# RULE: always use 'is' for None, True, False
if result is None:      # correct
    ...
if result == None:      # works but wrong — can be overridden by __eq__
    ...
```

**ADK context:** Always use `if event.actions is None` and `if session.state.get("key") is not None`.

---

## 4. No Block Scope

Java creates a new scope for every `{}` block. Python only creates scope in **functions, classes, and comprehensions** — not `if`, `for`, `while`, `try`, or `with`.

```python
# In Java, 'x' wouldn't exist outside the if block
# In Python, it does
if True:
    x = 42
print(x)  # 42 — totally valid

# Loop variables leak
for i in range(5):
    pass
print(i)  # 4 — still exists

# This catches Java devs in closures
callbacks = []
for i in range(3):
    callbacks.append(lambda: i)  # all capture same 'i'

[cb() for cb in callbacks]  # [2, 2, 2] — not [0, 1, 2]!

# FIX: capture with default argument
callbacks = []
for i in range(3):
    callbacks.append(lambda i=i: i)  # binds current value

[cb() for cb in callbacks]  # [0, 1, 2]
```

**ADK context:** When building tool lists or callbacks in loops, use the default argument trick or `functools.partial`. In production code, `functools.partial` is the preferred alternative since it's explicit and doesn't require a keyword-argument trick:

```python
from functools import partial

def make_callback(value):
    return lambda: value

callbacks = [partial(make_callback, i) for i in range(3)]
```

---

## 5. Truthiness — Everything Has a Boolean Value

Java requires explicit boolean expressions. Python treats many values as `False`:

```python
# All of these are falsy:
bool(None)       # False
bool(0)          # False
bool(0.0)        # False
bool("")         # False
bool([])         # False
bool({})         # False
bool(set())      # False

# All of these are truthy:
bool(1)          # True
bool("hello")    # True
bool([0])        # True  — list with one element (even if it's 0)
bool({"": ""})   # True  — dict with one entry

# GOTCHA: checking for None vs empty
def process(items=None):
    if not items:           # catches None AND empty list!
        return "nothing"
    return f"got {len(items)}"

process(None)    # "nothing" — correct
process([])      # "nothing" — probably wrong! empty list is valid input

# FIX: be explicit
def process(items=None):
    if items is None:       # only catches None
        return "nothing"
    return f"got {len(items)}"

process([])      # "got 0" — correct
```

**ADK context:** Agent callbacks returning `None` vs empty `Content()` have different semantics. A callback returning `None` means "continue normally"; returning empty content means "I handled it, here's nothing."

---

## 6. No Method Overloading

Java lets you define `process(String s)` and `process(int n)` as separate methods. Python silently **replaces** the first definition with the second.

```python
# WRONG — second definition silently replaces first
class ToolHandler:
    def handle(self, text: str):
        print(f"text: {text}")

    def handle(self, count: int):    # replaces the above!
        print(f"count: {count}")

h = ToolHandler()
h.handle("hello")  # "count: hello" — calls the second one with wrong type

# RIGHT — use optional params, Union types, or @singledispatchmethod
from functools import singledispatchmethod

class ToolHandler:
    @singledispatchmethod
    def handle(self, arg):
        raise TypeError(f"Unsupported: {type(arg)}")

    @handle.register
    def _(self, arg: str):
        print(f"text: {arg}")

    @handle.register
    def _(self, arg: int):
        print(f"count: {arg}")
```

**More commonly in Python — just use optional parameters:**

```python
def handle(self, text: str | None = None, count: int | None = None):
    if text is not None:
        ...
    elif count is not None:
        ...
```

---

<!-- Group 2: Runtime (Gotchas 7–9) -->

## 7. String Gotchas

```python
# No char type — single characters are strings
type("a")           # <class 'str'>
"hello"[0]          # "h" (a string, not a char)

# Strings are immutable (like Java)
s = "hello"
# s[0] = "H"       # TypeError!
s = "H" + s[1:]    # creates new string

# f-strings evaluate at runtime (not compile-time constants)
name = "agent"
greeting = f"Hello, {name}"  # "Hello, agent"

# GOTCHA: multiline strings preserve indentation
def get_prompt():
    return """
        You are a helpful agent.
        Be concise.
    """
# Result has leading spaces and newlines!

# FIX: use textwrap.dedent or backslash
import textwrap
def get_prompt():
    return textwrap.dedent("""\
        You are a helpful agent.
        Be concise.""")
```

**ADK context:** Agent `instruction` fields are strings. Watch indentation in multiline prompts — extra whitespace gets sent to the LLM and wastes tokens.

---

## 8. Exception Handling Differences

```python
# No checked exceptions — nothing forces you to handle errors
# This compiles fine even though open() can raise FileNotFoundError
data = open("config.json").read()

# GOTCHA: bare except catches EVERYTHING including KeyboardInterrupt
try:
    result = agent.run()
except:              # catches SystemExit, KeyboardInterrupt too!
    pass             # you can't even Ctrl+C out

# RIGHT — catch specific exceptions
try:
    result = agent.run()
except (ValueError, RuntimeError) as e:
    logger.error(f"Agent failed: {e}")

# GOTCHA: exception chaining
try:
    int("abc")
except ValueError:
    raise RuntimeError("bad input")  # loses original traceback

# RIGHT — use 'from' to chain
try:
    int("abc")
except ValueError as e:
    raise RuntimeError("bad input") from e  # preserves chain

# Context managers replace try-with-resources
# Java: try (var conn = getConnection()) { ... }
# Python:
with open("data.json") as f:
    data = f.read()
# f is automatically closed, even on exception
```

**ADK context:** Tool functions should catch and handle their own exceptions. Unhandled exceptions in tools surface as error events to the LLM.

---

## 9. The GIL — Threads Don't Run in Parallel

Java's threads run truly concurrently on multiple cores. Python's Global Interpreter Lock (GIL) means **only one thread executes Python bytecode at a time**.

```python
# WRONG — threading for CPU-bound work (no speedup)
import threading
def compute(n):
    return sum(range(n))

t1 = threading.Thread(target=compute, args=(10**8,))
t2 = threading.Thread(target=compute, args=(10**8,))
t1.start(); t2.start()
t1.join(); t2.join()
# This is NOT faster than running sequentially!

# RIGHT for CPU-bound — use multiprocessing
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor() as pool:
    results = list(pool.map(compute, [10**8, 10**8]))

# RIGHT for I/O-bound — use asyncio (what ADK uses)
import asyncio
async def fetch_all():
    results = await asyncio.gather(
        fetch_url("http://api1.com"),
        fetch_url("http://api2.com"),
    )
```

**ADK context:** ADK is async-first. All concurrency is `asyncio`, not threads. `ParallelAgent` runs sub-agents concurrently via `asyncio.gather`, not threads. Never use `time.sleep()` — use `await asyncio.sleep()`.

If you must call blocking code (a legacy library, a CPU-bound function) from inside an async ADK tool, use `asyncio.to_thread()` to avoid blocking the event loop:

```python
import asyncio

async def my_tool(query: str) -> str:
    # blocking_db_call() would freeze the event loop — offload it:
    result = await asyncio.to_thread(blocking_db_call, query)
    return result
```

---

<!-- Group 3: Object & Module System (Gotchas 10–13) -->

## 10. Class System Surprises

```python
# No access modifiers — underscore is convention only
class Agent:
    def __init__(self):
        self.name = "public"       # public (convention)
        self._config = {}          # "protected" (convention, not enforced)
        self.__secret = "hidden"   # name-mangled to _Agent__secret

a = Agent()
a._config["key"] = "val"         # works fine — not actually protected
a._Agent__secret                  # even "private" is accessible

# No interfaces — use ABC or Protocol
from abc import ABC, abstractmethod

class BaseTool(ABC):
    @abstractmethod
    async def run_async(self, *, args, tool_context):
        ...

# Explicit self — not implicit this
class Counter:
    def __init__(self):        # Java: public Counter()
        self.count = 0         # Java: this.count = 0

    def increment(self):       # 'self' is explicit
        self.count += 1        # must use self.count, not just count

# GOTCHA: forgetting self
class Bad:
    def greet(self):
        name = "world"         # local variable, not instance variable!
        return f"hello {name}"

    def get_name(self):
        return self.name       # AttributeError — 'name' was local in greet()

# Multiple inheritance — MRO (Method Resolution Order)
class A:
    def method(self): return "A"
class B(A):
    def method(self): return "B"
class C(A):
    def method(self): return "C"
class D(B, C):
    pass

D().method()     # "B" — follows MRO: D → B → C → A
D.__mro__        # shows the full resolution order
```

---

## 11. Dictionary and Collection Gotchas

```python
# Dict iteration order is guaranteed (insertion order, Python 3.7+)
# Java HashMap has no order guarantee

# GOTCHA: modifying dict during iteration
d = {"a": 1, "b": 2, "c": 3}
for key in d:
    if d[key] < 2:
        del d[key]   # RuntimeError: dictionary changed size during iteration

# FIX: iterate over a copy of keys
for key in list(d.keys()):
    if d[key] < 2:
        del d[key]   # safe

# GOTCHA: dict.get() vs direct access
d = {"key": None}
d["key"]             # None
d.get("key")         # None
d.get("missing")     # None  — same as above! Can't tell if key exists

# RIGHT — use 'in' check or default sentinel
"key" in d                     # True
d.get("missing", "SENTINEL")  # "SENTINEL"

# GOTCHA: list multiplication creates shared references
grid = [[0] * 3] * 3     # looks like 3x3 grid
grid[0][0] = 1
print(grid)               # [[1, 0, 0], [1, 0, 0], [1, 0, 0]] — all rows changed!

# FIX: use comprehension
grid = [[0] * 3 for _ in range(3)]  # independent rows
```

**ADK context:** `session.state` is a dict. Use `.get()` with explicit defaults, and never modify dicts you're iterating over.

---

## 12. Import System Traps

```python
# GOTCHA: circular imports
# file_a.py
from file_b import helper    # tries to import file_b
def main(): return helper()

# file_b.py
from file_a import main      # tries to import file_a — circular!
def helper(): return main()

# FIX 1: import the module, not the name
import file_b
def main(): return file_b.helper()

# FIX 2: move import inside the function
def main():
    from file_b import helper  # deferred import
    return helper()

# GOTCHA: relative imports
# In a package:
# mypackage/
#   __init__.py
#   tools.py
#   agents.py

# Inside agents.py:
from .tools import MyTool     # relative import — needs package context
from tools import MyTool      # WRONG if running as script — ModuleNotFoundError

# GOTCHA: import side effects
# Python executes module-level code on import
# config.py
print("Config loaded!")       # prints every time config is imported
API_KEY = os.getenv("KEY")    # evaluated at import time, not call time
```

> **ADK-specific:** Importing `google.adk.*` modules at the top of a file raises `ModuleNotFoundError` in test environments where ADK is not installed. Prefer lazy imports inside functions or use conditional guards (`try: import google.adk ... except ImportError: ...`) to keep test discovery fast.

---

## 13. Unpacking and Assignment Gotchas

```python
# Tuple unpacking — very Pythonic, no Java equivalent
a, b = 1, 2           # a=1, b=2
a, b = b, a            # swap without temp variable
first, *rest = [1, 2, 3, 4]   # first=1, rest=[2, 3, 4]

# GOTCHA: single-element tuple needs comma
t = (42)     # int, not tuple!
t = (42,)    # tuple with one element
t = 42,      # also a tuple — comma makes the tuple, not parens

# GOTCHA: augmented assignment with immutable types
a = 1
b = a
a += 1       # creates NEW int — b still 1 (ints are immutable)

# vs mutable types
a = [1]
b = a
a += [2]     # mutates IN PLACE — b is now [1, 2] too!
# a = a + [2] would create new list, but += calls __iadd__ which mutates

# Walrus operator (Python 3.8+) — no Java equivalent
# Assign and test in one expression
if (n := len(items)) > 10:
    print(f"Too many: {n}")
```

---

## Quick Reference Card

| Java Instinct | Python Trap | Fix |
|---|---|---|
| `def f(x=[])` is fine | Mutable default shared across calls | Use `None` sentinel |
| `backup = original` copies | Both point to same object | Use `.copy()` or `copy.deepcopy()` |
| `if (x == null)` | Works but wrong for singletons | Use `is None` |
| Variables in `for` are local | Loop vars leak into enclosing scope | Be aware; use `_` for throwaway |
| `if (!list.isEmpty())` | `if not items` catches `None` AND `[]` | Use `if items is not None` |
| Method overloading | Last definition silently wins | Use optional params or `singledispatch` |
| `private` is enforced | `_` prefix is a suggestion only | Accept it — Python trusts developers |
| Threads run in parallel | GIL: one thread at a time | Use `asyncio` for I/O, `multiprocessing` for CPU |
| `try { } catch { }` | Bare `except:` catches `SystemExit` | Always specify exception type |
| `HashMap` has no order | `dict` preserves insertion order | Rely on it (Python 3.7+) |
| `clone()` deep-copies | `.copy()` is shallow | Use `copy.deepcopy()` for nested structures |
| `this` is implicit | `self` must be explicit everywhere | Always write `self.field`, never just `field` |

---

## Related

- [java-to-python-cheat-sheet.md](../reference/java-to-python-cheat-sheet.md) — syntax mapping (Java code → Python equivalent)
- [python-for-adk-learning-plan.md](python-for-adk-learning-plan.md) — 2-week curriculum with exercises
- [python-asyncio-deep-dive.md](python-asyncio-deep-dive.md) — async gotchas in depth
- [python-pydantic-deep-dive.md](python-pydantic-deep-dive.md) — Pydantic gotchas (mutable defaults, validation)
- [python-decorators-deep-dive.md](python-decorators-deep-dive.md) — decorator/closure gotchas
