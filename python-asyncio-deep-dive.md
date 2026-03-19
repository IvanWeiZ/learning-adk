# Python asyncio Deep Dive

**Audience:** Experienced Java developers learning ADK.

---

## What It Is

`asyncio` is Python's built-in framework for writing concurrent, non-blocking code using a **single-threaded event loop**. If you come from Java, think of it as `CompletableFuture` combined with virtual threads (Project Loom) -- but instead of OS threads or carrier threads, everything runs on one thread cooperatively yielding control at `await` points. ADK is built entirely on asyncio: every agent, runner, session service, and tool uses `async def` and `AsyncGenerator` to stream events without blocking.

---

## Core Concepts

### The Event Loop

Java's `ExecutorService` manages a pool of threads. Python's `asyncio` event loop is a **single thread** that multiplexes thousands of concurrent I/O operations by switching between coroutines at `await` points.

```
Java Thread Pool                    Python asyncio Event Loop
─────────────────                   ──────────────────────────
Thread-1 → task A                   One thread, one loop:
Thread-2 → task B                     → run coroutine A until it awaits
Thread-3 → task C                     → switch to coroutine B
Thread-4 → task D                     → switch to coroutine C
                                      → A's I/O is ready, resume A
                                      → ...
```

Key difference: there is no preemption. A coroutine runs until it hits `await`, at which point control returns to the event loop. If your code does CPU-intensive work or calls a blocking function (like `time.sleep(5)`), the entire loop stalls.

```python
import asyncio

async def main() -> None:
    print("Starting")
    await asyncio.sleep(1)   # yields to event loop for 1 second
    print("Done")

asyncio.run(main())  # creates event loop, runs main(), closes loop
```

### Coroutines

A coroutine is defined with `async def`. Calling it returns a coroutine object -- it does **not** execute the body. You must `await` it (or schedule it as a task) to run it.

```python
async def fetch_data(url: str) -> dict:
    # This is a coroutine function.
    # Calling fetch_data("...") returns a coroutine object, not a dict.
    ...

# Java equivalent (roughly):
# CompletableFuture<Map<String, Object>> fetchData(String url) { ... }
```

```python
async def main() -> None:
    # WRONG: creates coroutine but never runs it
    fetch_data("https://api.example.com")  # RuntimeWarning: coroutine was never awaited

    # RIGHT: await the coroutine
    result = await fetch_data("https://api.example.com")
```

### Tasks

A `Task` wraps a coroutine and schedules it to run concurrently on the event loop. This is how you run multiple operations in parallel.

```python
async def main() -> None:
    # Create tasks -- both start running immediately
    task_a = asyncio.create_task(fetch_data("url_a"))
    task_b = asyncio.create_task(fetch_data("url_b"))

    # Await both results
    result_a = await task_a
    result_b = await task_b
```

Java equivalent: `CompletableFuture.supplyAsync(...)`.

### Awaitables, Coroutines, and Futures

| Python type | What it is | Java analogy |
|---|---|---|
| Coroutine | Object returned by `async def` call | Not yet submitted `Callable` |
| Task | Scheduled coroutine on the event loop | `CompletableFuture` (already running) |
| Future | Low-level placeholder for a result | `CompletableFuture` (empty) |
| Awaitable | Anything you can `await` (all three above) | Anything with `.get()` or `.join()` |

---

## async/await Patterns

### Basic Async Function

```python
import asyncio
import httpx  # async HTTP client (like Java's HttpClient)

async def get_weather(city: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.json()

async def main() -> None:
    weather = await get_weather("London")
    print(weather)

asyncio.run(main())
```

### Awaiting Multiple Coroutines

#### `asyncio.gather` -- run coroutines concurrently, collect all results

```python
async def main() -> None:
    # All three run concurrently. Returns a list of results in order.
    results = await asyncio.gather(
        get_weather("London"),
        get_weather("Tokyo"),
        get_weather("NYC"),
    )
    # results == [london_data, tokyo_data, nyc_data]
```

Java equivalent: `CompletableFuture.allOf(a, b, c).join()`.

#### `asyncio.TaskGroup` (Python 3.11+) -- structured concurrency

```python
async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        task_a = tg.create_task(get_weather("London"))
        task_b = tg.create_task(get_weather("Tokyo"))
    # Both tasks are guaranteed done when the block exits
    # If either raises, the other is cancelled automatically
    print(task_a.result(), task_b.result())
```

`TaskGroup` is Python's answer to Java 21's `StructuredTaskScope`. It guarantees cleanup: if one task fails, sibling tasks are cancelled and the group re-raises as an `ExceptionGroup`.

### AsyncGenerator -- Critical for ADK

An `AsyncGenerator` is an async function that `yield`s values instead of returning them. This is how ADK streams events.

```python
from collections.abc import AsyncGenerator

async def count_slowly() -> AsyncGenerator[int, None]:
    for i in range(5):
        await asyncio.sleep(0.5)
        yield i  # produces a value, then suspends

async def main() -> None:
    async for number in count_slowly():
        print(number)  # prints 0, 1, 2, 3, 4 with half-second gaps
```

Java has no direct equivalent. The closest would be a `Flow.Publisher<T>` (Reactive Streams) or `Iterator` backed by a `BlockingQueue`. Python's `AsyncGenerator` is simpler: it is just a function with `yield` that the caller consumes with `async for`.

**How ADK uses this pattern:**

```python
# ADK's BaseAgent._run_async_impl signature:
async def _run_async_impl(
    self, ctx: InvocationContext
) -> AsyncGenerator[Event, None]:
    # ... do work ...
    yield Event(...)   # stream event to caller
    # ... do more work ...
    yield Event(...)   # stream another event
```

Every agent, flow, and runner uses this pattern. Events are not collected into a list and returned -- they are streamed one at a time via `yield`.

### `async for` and `async with`

```python
# async for -- iterate over an async iterable (AsyncGenerator, async DB cursor, etc.)
async for event in runner.run_async(user_id="u1", session_id="s1", new_message=msg):
    print(event)

# async with -- async context manager (setup/teardown with awaitable __aenter__/__aexit__)
async with httpx.AsyncClient() as client:
    response = await client.get("https://example.com")
# client is closed here, even if an exception was raised
```

Java equivalents:
- `async for` is similar to consuming a reactive `Flux` or iterating a `Flow.Publisher`
- `async with` is similar to try-with-resources (`AutoCloseable`) but supports async cleanup

### `asyncio.run()` as Entry Point

`asyncio.run()` creates a new event loop, runs the given coroutine to completion, and shuts down the loop. It is the standard way to bridge sync code into async code.

```python
# This is your main() in a script -- the bridge between sync and async worlds.
if __name__ == "__main__":
    asyncio.run(main())
```

Rule: there is exactly **one** `asyncio.run()` per program. Everything inside it uses `await`.

---

## ADK-Specific Patterns

### Why ADK Is Async-First

ADK processes involve multiple I/O-bound operations that benefit from concurrency:

1. **LLM API calls** -- waiting for model responses (100ms to seconds)
2. **Tool execution** -- external API calls, database queries
3. **Session persistence** -- reading/writing session state
4. **Streaming** -- events must flow to the caller as they are produced, not after everything finishes

By using `AsyncGenerator`, ADK streams events as they happen. The caller sees each event immediately, enabling real-time UIs and progressive responses.

### The Runner Pattern

The fundamental ADK consumption pattern is `async for` over the runner:

```python
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

agent = LlmAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    tools=[get_weather],
)

runner = Runner(
    agent=agent,
    app_name="weather_app",
    session_service=InMemorySessionService(),
)

async def chat(user_message: str) -> None:
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )
    async for event in runner.run_async(
        user_id="user1",
        session_id="session1",
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)

asyncio.run(chat("What is the weather in London?"))
```

This is a direct application of `AsyncGenerator` + `async for`. The runner yields events as the agent processes: first the tool call event, then the tool response event, then the final text response event.

### Writing Async Tools

ADK tools can be sync or async. Prefer async when the tool performs I/O:

```python
# Sync tool -- ADK wraps it automatically, but it blocks the event loop during execution
def get_user_count() -> int:
    return 42

# Async tool -- preferred for I/O operations
async def search_database(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/search",
            json={"q": query},
        )
        return response.json()["results"]

agent = LlmAgent(
    name="search_agent",
    model="gemini-2.5-flash",
    tools=[search_database],  # ADK detects it's async and awaits it
)
```

When ADK encounters a sync tool, it runs the function directly in the event loop thread. If that function blocks (e.g., `requests.get()`), the entire event loop stalls. For blocking I/O, either:
1. Write the tool as `async def` using an async HTTP client, or
2. Use `asyncio.to_thread()` inside the tool to offload blocking work

### Async Session Services

ADK's session services are async. When implementing a custom service, every method must be `async def`:

```python
from google.adk.sessions import BaseSessionService, Session

class MySessionService(BaseSessionService):
    async def create_session(
        self, *, app_name: str, user_id: str, **kwargs
    ) -> Session:
        # Use async DB driver (asyncpg, aiosqlite, motor, etc.)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("INSERT INTO sessions ...")
            return Session(...)

    async def get_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> Session | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT ... WHERE id = $1", session_id)
            return Session(...) if row else None
```

### Example: Async Tool Calling an External API

A complete async tool with error handling and timeout:

```python
import httpx

async def get_stock_price(symbol: str) -> dict:
    """Returns the current stock price for the given ticker symbol."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.stocks.example.com/v1/price/{symbol}"
            )
            response.raise_for_status()
            data = response.json()
            return {
                "symbol": symbol,
                "price": data["price"],
                "currency": data["currency"],
            }
    except httpx.TimeoutException:
        return {"error": f"Timeout fetching price for {symbol}"}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code} for {symbol}"}
```

---

## Common Pitfalls

### 1. Blocking the Event Loop

The most common mistake. One blocking call freezes everything.

```python
import time

# BAD: blocks the event loop for 5 seconds. No other coroutine can run.
async def bad_sleep() -> None:
    time.sleep(5)

# GOOD: yields to event loop. Other coroutines run during the wait.
async def good_sleep() -> None:
    await asyncio.sleep(5)

# BAD: requests is synchronous -- blocks the event loop
import requests
async def bad_fetch() -> dict:
    return requests.get("https://api.example.com").json()

# GOOD: httpx.AsyncClient is non-blocking
import httpx
async def good_fetch() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com")
        return response.json()
```

Java equivalent: calling `Thread.sleep()` inside a virtual thread's carrier thread, blocking all other virtual threads on that carrier.

### 2. Forgetting to Await

```python
async def main() -> None:
    # BUG: result is a coroutine object, not the actual data
    result = fetch_data("url")        # missing await!
    print(type(result))               # <class 'coroutine'>

    # FIX:
    result = await fetch_data("url")
    print(type(result))               # <class 'dict'>
```

Python 3.12+ shows a `RuntimeWarning` for unawaited coroutines, but the bug is still easy to miss in production.

### 3. Mixing Sync and Async Code

When you must call blocking (sync) code from an async context, use `asyncio.to_thread()`:

```python
import asyncio

def cpu_heavy_work(data: bytes) -> bytes:
    """A CPU-bound function that cannot be made async."""
    # ... expensive computation ...
    return processed_data

async def process_async(data: bytes) -> bytes:
    # Runs cpu_heavy_work in a separate thread, yielding the event loop
    result = await asyncio.to_thread(cpu_heavy_work, data)
    return result
```

`asyncio.to_thread()` is Python 3.9+. It is equivalent to `loop.run_in_executor(None, func, *args)` using the default thread pool.

For the reverse (calling async code from sync code), use `asyncio.run()`:

```python
# In a sync context (e.g., a Django view, a CLI script):
def sync_entry_point() -> None:
    result = asyncio.run(some_async_function())
```

Warning: `asyncio.run()` cannot be called when an event loop is already running. If you are inside a Jupyter notebook or a framework that already runs a loop, use `nest_asyncio` or restructure your code.

### 4. Task Cancellation and Cleanup

When a task is cancelled, Python raises `asyncio.CancelledError` inside the coroutine at its next `await`. You can catch it for cleanup:

```python
async def long_running_task() -> None:
    try:
        while True:
            await asyncio.sleep(1)
            print("working...")
    except asyncio.CancelledError:
        print("Cleaning up resources...")
        # Close connections, flush buffers, etc.
        raise  # re-raise to confirm cancellation

async def main() -> None:
    task = asyncio.create_task(long_running_task())
    await asyncio.sleep(3)
    task.cancel()           # request cancellation
    try:
        await task          # wait for it to finish cancelling
    except asyncio.CancelledError:
        print("Task was cancelled")
```

ADK relevance: when a runner is stopped or a request times out, in-flight tool tasks may be cancelled. Ensure your async tools handle `CancelledError` gracefully if they hold resources.

### 5. Accidentally Creating Coroutines in Loops

```python
# BAD: sequential execution -- each await waits for the previous to finish
async def slow() -> list[dict]:
    results = []
    for city in ["London", "Tokyo", "NYC"]:
        result = await get_weather(city)  # waits each time
        results.append(result)
    return results  # total time: sum of all three calls

# GOOD: concurrent execution
async def fast() -> list[dict]:
    return await asyncio.gather(
        get_weather("London"),
        get_weather("Tokyo"),
        get_weather("NYC"),
    )  # total time: max of the three calls
```

---

## Java Comparison Table

| Concept | Java | Python asyncio |
|---|---|---|
| Thread pool | `ExecutorService` / `ForkJoinPool` | Event loop (single-threaded) |
| Async function | `CompletableFuture<T>` return type | `async def` function |
| Await result | `future.join()` / `future.get()` | `await coroutine` |
| Fire and forget | `CompletableFuture.runAsync(...)` | `asyncio.create_task(...)` |
| Wait for all | `CompletableFuture.allOf(a, b, c)` | `asyncio.gather(a, b, c)` |
| Structured concurrency | `StructuredTaskScope` (Java 21+) | `asyncio.TaskGroup` (Python 3.11+) |
| Reactive stream | `Flow.Publisher<T>` | `AsyncGenerator[T, None]` |
| Consume stream | `Flow.Subscriber<T>` | `async for item in generator` |
| Context manager | try-with-resources (`AutoCloseable`) | `async with` (`__aenter__`/`__aexit__`) |
| Run blocking in async | `executor.submit(callable)` | `asyncio.to_thread(func)` |
| Run async from sync | `future.join()` | `asyncio.run(coro)` |
| Cancel a task | `future.cancel(true)` | `task.cancel()` raises `CancelledError` |
| Timeout | `future.get(5, SECONDS)` | `asyncio.wait_for(coro, timeout=5)` |
| Sleep without blocking | `Thread.sleep()` in virtual thread | `await asyncio.sleep(n)` |
| Non-blocking HTTP | `HttpClient.sendAsync(...)` | `httpx.AsyncClient` / `aiohttp` |
| Async iteration | `Spliterator` / `Stream` (not truly async) | `async for` + `AsyncIterator` |
| Entry point | `public static void main(String[])` | `asyncio.run(main())` |

### Key Mental Model Shift

In Java, concurrency comes from **multiple threads**. In Python asyncio, concurrency comes from **cooperative multitasking on one thread**. The event loop is like a single-threaded scheduler that jumps between coroutines whenever they say "I am waiting for I/O" (i.e., `await`).

This means:
- No locks needed for shared state (only one coroutine runs at a time)
- No race conditions from concurrent memory access
- But: one blocking call stalls everything (no preemption)
- CPU-bound work must be offloaded to threads or processes

---

## Quick Reference: asyncio API

| Function | Purpose |
|---|---|
| `asyncio.run(coro)` | Entry point: create loop, run coroutine, clean up |
| `asyncio.create_task(coro)` | Schedule coroutine to run concurrently |
| `asyncio.gather(*coros)` | Run multiple coroutines concurrently, return all results |
| `asyncio.TaskGroup()` | Structured concurrency (Python 3.11+) |
| `asyncio.sleep(seconds)` | Non-blocking sleep |
| `asyncio.wait_for(coro, timeout)` | Run with a timeout, raise `TimeoutError` |
| `asyncio.to_thread(func, *args)` | Run sync function in a thread |
| `asyncio.Queue()` | Async-safe queue for producer/consumer patterns |
| `asyncio.Semaphore(n)` | Limit concurrency to `n` coroutines |
| `asyncio.Lock()` | Async mutex (rarely needed since single-threaded) |

---

## Cross-References

- [01-request-lifecycle.md](adk/01-request-lifecycle.md) -- Traces a full request through ADK's async pipeline
- [03-runners.md](adk/03-runners.md) -- `Runner.run_async()` returns an `AsyncGenerator[Event, None]`
- [05-flows.md](adk/05-flows.md) -- The reason-act loop uses `async for` to stream LLM responses
- [09-tools.md](adk/09-tools.md) -- Tools can be `async def` for non-blocking I/O
- [17-concurrency.md](adk/17-concurrency.md) -- Thread safety, parallel tool dispatch via `asyncio.gather`
- [python-for-adk-learning-plan.md](python-for-adk-learning-plan.md) -- Two-week Python curriculum including async fundamentals
