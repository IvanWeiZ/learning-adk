# Java to Python Cheat Sheet

For experienced Java developers learning Python for ADK. This guide maps familiar Java concepts to their Python equivalents, with notes on where things differ.

See also: [python-for-adk-learning-plan.md](../python/python-for-adk-learning-plan.md) for a structured 2-week curriculum.

---

## Syntax Basics

| Java | Python | Notes |
|---|---|---|
| `int x = 5;` | `x = 5` or `x: int = 5` | No semicolons. Type hints are optional but recommended. |
| `{ ... }` blocks | Indentation (4 spaces) | Indentation is syntactically significant. |
| `// comment` | `# comment` | No `/* */` block comments; use `#` per line or `"""docstrings"""`. |
| `null` | `None` | Singleton; test with `is None`, not `== None`. |
| `true` / `false` | `True` / `False` | Capitalized. |
| `System.out.println(x)` | `print(x)` | |
| `final int X = 10;` | `X = 10` | Constants are UPPER_CASE by convention only; not enforced. |
| `var x = "hello"` (Java 10+) | `x = "hello"` | Python has always been dynamically typed. |
| `String.format("Hi %s", name)` | `f"Hi {name}"` | f-strings are the preferred approach. |
| `condition ? a : b` | `a if condition else b` | Ternary reads differently. |
| `for (int i = 0; i < n; i++)` | `for i in range(n):` | Python `for` is always a for-each over an iterable. |
| `switch / case` (Java 14+) | `match / case` (Python 3.10+) | Structural pattern matching; more powerful than Java's switch. |

## OOP

| Java | Python | Notes |
|---|---|---|
| `class Foo { }` | `class Foo:` | No braces; body is indented. |
| `interface IFoo { }` | `class IFoo(ABC):` | Use `abc.ABC` + `@abstractmethod`. → [decorators deep dive](../python/python-decorators-deep-dive.md) |
| `class Bar extends Foo` | `class Bar(Foo):` | Single inheritance syntax is the same concept. |
| `class Bar implements IFoo` | `class Bar(IFoo):` | No `implements`; just inherit from the ABC. |
| `this.field` | `self.field` | `self` is explicit in all instance methods. |
| `public Foo(int x) { }` | `def __init__(self, x: int):` | Constructor is always `__init__`. |
| `@Override` | `@override` (3.12+) | Optional; from `typing`. ADK uses duck typing heavily. |
| `final class Foo` | `@final` decorator | From `typing`; advisory, not enforced at runtime. |
| `static void bar()` | `@staticmethod` | Or `@classmethod` if you need access to the class. |
| `Foo.class` | `Foo` or `type(instance)` | Classes are first-class objects in Python. |
| `instanceof` | `isinstance(obj, Foo)` | Also supports tuples: `isinstance(obj, (Foo, Bar))`. |
| `public` / `private` / `protected` | Convention: `_private`, `__mangled` | No enforced access modifiers. `_` prefix = internal. |
| Multiple constructors (overloading) | Default args or `@classmethod` factories | Python has no method overloading. |
| `Foo<T>` (generics) | `Foo[T]` with `TypeVar` or `Generic` | See [Type System](#type-system) below. |

## Type System

| Java | Python | Notes |
|---|---|---|
| `int`, `long`, `double` | `int`, `float` | Python `int` has arbitrary precision. No primitives vs. wrappers. |
| `String` | `str` | Immutable in both languages. |
| `boolean` | `bool` | |
| `List<String>` | `list[str]` | Lowercase built-in generics since Python 3.9. |
| `Map<String, Integer>` | `dict[str, int]` | |
| `Set<String>` | `set[str]` | |
| `Optional<String>` | `str \| None` | Python 3.10+ union syntax. Older: `Optional[str]`. |
| `Object` | `object` | Base of all classes. `Any` for untyped. |
| `void` | `-> None` | In return type annotation. |
| `enum Color { RED, GREEN }` | `class Color(Enum):` | `from enum import Enum`. |
| `record Point(int x, int y)` | `@dataclass` or `BaseModel` | ADK uses Pydantic `BaseModel` extensively. → [pydantic deep dive](../python/python-pydantic-deep-dive.md) |
| `sealed interface` | `@final` on subclasses | No direct sealed equivalent. |
| Annotations (`@NotNull`) | Type hints + runtime validation | Pydantic validates at runtime; type hints alone do not. |

## Collections

| Java | Python | Notes |
|---|---|---|
| `new ArrayList<>()` | `[]` or `list()` | Lists are the default mutable sequence. |
| `new HashMap<>()` | `{}` or `dict()` | Dict literals use `{k: v}`. |
| `new HashSet<>()` | `set()` or `{a, b}` | `{}` alone creates a dict, not a set. |
| `List.of(1, 2, 3)` | `(1, 2, 3)` (tuple) | Tuples are immutable. For immutable list: `tuple(my_list)`. |
| `list.add(x)` | `list.append(x)` | |
| `list.get(i)` | `list[i]` | Supports negative indexing: `list[-1]` is last element. |
| `map.get(key)` | `d[key]` or `d.get(key)` | `.get()` returns `None` instead of raising `KeyError`. |
| `map.put(k, v)` | `d[k] = v` | |
| `map.containsKey(k)` | `k in d` | Works for sets and lists too. |
| `stream().filter().map()` | List comprehension | `[f(x) for x in items if pred(x)]` — more idiomatic. |
| `stream().collect()` | Comprehension or `list(gen)` | Generators for lazy evaluation. |
| `Collections.unmodifiableList()` | `tuple(list)` | Or use `frozenset` for immutable sets. |
| `Arrays.sort(arr)` | `sorted(arr)` or `arr.sort()` | `sorted()` returns new list; `.sort()` mutates in place. |
| `Map.entry()` / iteration | `d.items()` | `for k, v in d.items():` — unpacking is idiomatic. |

## Error Handling

| Java | Python | Notes |
|---|---|---|
| `try { } catch (E e) { }` | `try: ... except E as e:` | |
| `catch (A \| B e)` | `except (A, B) as e:` | Tuple of exception types. |
| `finally { }` | `finally:` | Same semantics. |
| `throw new E()` | `raise E()` | |
| `throws IOException` | No equivalent | Python has no checked exceptions. Document in docstrings. |
| `try (var r = ...)` (try-with-resources) | `with open(...) as f:` | Context managers via `__enter__`/`__exit__` or `contextlib`. |
| `catch (Exception e)` | `except Exception as e:` | Avoid bare `except:` — it catches `SystemExit` too. |
| Custom exception class | `class MyError(Exception):` | Inherit from `Exception`, not `BaseException`. |
| `e.getMessage()` | `str(e)` | |
| Stack trace | `traceback` module | Or `import traceback; traceback.print_exc()`. |

## Concurrency

| Java                        | Python                        | Notes                                                                            |
| --------------------------- | ----------------------------- | -------------------------------------------------------------------------------- |
| `CompletableFuture<T>`      | `asyncio.Task` / `await`      | ADK is async-first. → [asyncio deep dive](../python/python-asyncio-deep-dive.md) |
| `ExecutorService`           | `asyncio.get_event_loop()`    | Single-threaded event loop; no thread pool needed for I/O.                       |
| `Future.get()`              | `await coroutine`             | Never block on a coroutine; always `await`.                                      |
| `CompletableFuture.allOf()` | `asyncio.gather()`            | Run multiple coroutines concurrently.                                            |
| `synchronized`              | `asyncio.Lock()`              | For async code. `threading.Lock` for threaded code (rare in ADK).                |
| `Thread`                    | `asyncio.create_task()`       | Tasks are lightweight; no OS threads.                                            |
| `@Async` (Spring)           | `async def`                   | Native language keyword.                                                         |
| `Callable<T>`               | `Callable[..., Awaitable[T]]` | Or just `async def` function.                                                    |
| `volatile`                  | No equivalent                 | GIL provides basic visibility; use `asyncio` primitives.                         |
| Thread pool for CPU work    | `asyncio.to_thread()`         | Offload CPU-bound work from the event loop.                                      |

See [17-concurrency.md](../adk/17-concurrency.md) for ADK-specific concurrency patterns.

## Testing

| Java | Python | Notes |
|---|---|---|
| JUnit 5 | `pytest` | No class required; plain functions work. → [testing guide](../python/python-testing-and-mocking-guide.md) |
| `@Test` | `def test_something():` | Prefix with `test_`. |
| `@BeforeEach` / `@AfterEach` | `@pytest.fixture` | Fixtures are injected by name. More flexible than JUnit lifecycle. |
| `@BeforeAll` / `@AfterAll` | `@pytest.fixture(scope="module")` | Or `scope="session"` for across all tests. |
| `assertEquals(a, b)` | `assert a == b` | Plain assert; pytest rewrites for rich diffs. |
| `assertThrows(E, () -> ...)` | `with pytest.raises(E):` | Context manager style. |
| `@ParameterizedTest` | `@pytest.mark.parametrize(...)` | |
| Mockito `mock()` | `unittest.mock.Mock()` | Or `MagicMock`, `AsyncMock` for async. |
| `when(m.foo()).thenReturn(x)` | `m.foo.return_value = x` | Or `m.foo.side_effect = ...` for dynamic behavior. |
| `verify(m).foo()` | `m.foo.assert_called_once()` | |
| `@MockBean` (Spring) | `monkeypatch` or `@patch` | pytest's `monkeypatch` fixture or `unittest.mock.patch`. |
| `@SpringBootTest` | `@pytest.mark.asyncio` | For testing async ADK agents. |

See [22-testing.md](../adk/22-testing.md) for ADK-specific testing with `MockModel`.

## Package / Module System

| Java | Python | Notes |
|---|---|---|
| `package com.foo.bar` | Directory + `__init__.py` | Each directory with `__init__.py` is a package. |
| `import com.foo.Bar` | `from foo import Bar` | Or `import foo.bar`. |
| `import static` | `from module import func` | Same syntax as regular import. |
| `*` wildcard import | `from module import *` | Discouraged; use explicit imports. |
| Maven / Gradle | `pip` / `uv` / `poetry` | `uv` is the modern fast alternative. |
| `pom.xml` / `build.gradle` | `pyproject.toml` | Single config file for dependencies, build, and tool settings. |
| JAR | wheel (`.whl`) / sdist | `pip install .` builds and installs. |
| `public` class per file | No restriction | Multiple classes per file is normal and encouraged. |
| `module-info.java` (JPMS) | `__init__.py` exports | Control public API via `__all__` list. |
| `mvn test` | `pytest` | Or `python -m pytest` for module invocation. |
| `src/main/java` / `src/test/java` | `src/` + `tests/` | Flat structure is more common in Python. |

## ADK-Specific Mappings

| Java Concept | ADK Python Equivalent | Notes |
|---|---|---|
| Spring Boot Application | `Runner` + `App` | `Runner` is the stateless orchestrator; `App` is the DI container. → [03-runners.md](../adk/03-runners.md), [10-apps.md](../adk/10-apps.md) |
| `@RestController` | `LlmAgent` | An agent handles requests and produces responses. → [04-agents.md](../adk/04-agents.md) |
| `@Service` | `FunctionTool` / `BaseTool` | Business logic wrapped as tools for agents. → [09-tools.md](../adk/09-tools.md) |
| DTO / Request Body | Pydantic `BaseModel` | Runtime validation, serialization, schema generation. → [pydantic deep dive](../python/python-pydantic-deep-dive.md) |
| `@Autowired` / DI | Constructor args on `LlmAgent` | Tools, sub-agents, and config are passed directly. No DI framework. |
| `ApplicationEvent` | `Event` + `EventActions` | Side effects are data, not method calls. → [07-events.md](../adk/07-events.md) |
| `HttpSession` | `Session` + `SessionService` | Session state is a plain dict with scoped keys. → [08-sessions.md](../adk/08-sessions.md) |
| Interceptor / Filter | Callbacks (`before_*` / `after_*`) | Six hook points on `LlmAgent`. → [04-agents.md](../adk/04-agents.md) |
| Spring Profiles | State scoping (`session:` / `user:` / `app:`) | Different state scopes replace environment-based config. → [08-sessions.md](../adk/08-sessions.md) |
| `@Async` + `CompletableFuture` | `async def` + `await` | Everything in ADK is async. → [asyncio deep dive](../python/python-asyncio-deep-dive.md) |
| `@Scheduled` | `LoopAgent` | Iterative execution until a stopping condition. → [04-agents.md](../adk/04-agents.md) |
| `@Transactional` | `EventActions.state_delta` | State changes are committed atomically with the event. → [07-events.md](../adk/07-events.md) |
| Strategy pattern (interface + impls) | `BaseLlm`, `BaseSessionService`, etc. | ABC base + multiple concrete implementations throughout ADK. |
| JUnit + Mockito | `pytest` + `MockModel` + `AsyncMock` | `MockModel` replaces the LLM for deterministic tests. → [22-testing.md](../adk/22-testing.md) |
| `ObjectMapper` (Jackson) | Pydantic `model_dump()` / `model_validate()` | Serialization and deserialization built into models. |
| Lombok `@Data` | `@dataclass` or `BaseModel` | Auto-generated `__init__`, `__repr__`, `__eq__`. |
| `Optional.orElse()` | `value if value is not None else default` | Or just `value or default` for falsy-safe cases. |
| `Stream.of().map().filter()` | Generator expressions / comprehensions | `(f(x) for x in items if pred(x))` — lazy by default. |

---

## Key Mindset Shifts

1. **No boilerplate** — Python rewards conciseness. If your code looks like Java with Python syntax, refactor.
2. **Duck typing** — Check behavior, not type. `hasattr(obj, "run")` rather than `instanceof Runnable`.
3. **Everything is an object** — Functions, classes, and modules are all objects you can pass around.
4. **Explicit self** — Always the first parameter in instance methods. Not a keyword; just a convention.
5. **EAFP over LBYL** — "Easier to Ask Forgiveness than Permission." Use `try/except` rather than checking preconditions.
6. **No checked exceptions** — Document exceptions in docstrings; callers choose what to catch.
7. **async/await is foundational** — ADK is built on asyncio. Master it early. → [asyncio deep dive](../python/python-asyncio-deep-dive.md)

---

See also: [glossary.md](glossary.md) | [25-onboarding-guide.md](../adk/00-onboarding-guide.md) | [20-best-practices.md](../adk/20-best-practices.md)
