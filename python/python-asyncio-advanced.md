# Python asyncio — Advanced Patterns

> **Part 1 is in [python-asyncio-deep-dive.md](python-asyncio-deep-dive.md)** — event loop, coroutines, tasks, gather/wait, TaskGroup, async generators, and async context managers.

This file covers Sections 9–18: synchronization primitives (Lock, Semaphore, Event, Queue), advanced task patterns, testing async code, bounded concurrency, and ADK-specific async patterns including the runner loop and callback chain.

---

### 9. Synchronization Primitives

Even though asyncio is single-threaded, you still need synchronization when multiple coroutines share state.

#### Lock — Mutual Exclusion

```python
import asyncio

# Prevent concurrent access to a shared resource
lock = asyncio.Lock()

shared_counter = 0

async def increment():
    global shared_counter
    async with lock:
        # Only one coroutine can be in this block at a time
        current = shared_counter
        await asyncio.sleep(0.01)  # simulate some async work
        shared_counter = current + 1

async def main():
    # Without the lock, concurrent increments would race
    await asyncio.gather(*[increment() for _ in range(100)])
    print(shared_counter)  # 100 (correct with lock, might be <100 without)
```

#### Semaphore — Limit Concurrency

```python
# EXTREMELY useful for rate-limiting API calls
semaphore = asyncio.Semaphore(5)  # max 5 concurrent operations

async def rate_limited_llm_call(prompt: str) -> str:
    async with semaphore:
        # At most 5 coroutines can be in here simultaneously
        return await call_llm_api(prompt)

async def main():
    prompts = [f"prompt_{i}" for i in range(100)]
    # All 100 are "started" but only 5 run at a time
    results = await asyncio.gather(*[
        rate_limited_llm_call(p) for p in prompts
    ])
```

#### BoundedSemaphore — Semaphore That Catches Bugs

```python
# BoundedSemaphore raises ValueError if you release more than you acquire
sem = asyncio.BoundedSemaphore(3)
# Useful for catching programming errors where release is called too many times
```

#### Event — Signal Between Coroutines

```python
event = asyncio.Event()

async def waiter():
    print("Waiting for signal...")
    await event.wait()  # suspends until event is set
    print("Got signal!")

async def setter():
    await asyncio.sleep(2)
    print("Setting signal")
    event.set()  # all waiters wake up

async def main():
    await asyncio.gather(waiter(), waiter(), setter())
    # Both waiters wake up when setter calls event.set()
```

#### Condition — Wait for Complex Conditions

```python
condition = asyncio.Condition()
data_ready = False
data = None

async def producer():
    global data_ready, data
    await asyncio.sleep(1)
    async with condition:
        data = {"result": 42}
        data_ready = True
        condition.notify_all()  # wake up all waiters

async def consumer(name: str):
    async with condition:
        await condition.wait_for(lambda: data_ready)
        print(f"{name} got data: {data}")
```

#### Barrier (Python 3.11+) — Wait for N Coroutines

```python
barrier = asyncio.Barrier(3)  # wait until 3 coroutines arrive

async def worker(name: str):
    print(f"{name} starting phase 1")
    await asyncio.sleep(1)
    await barrier.wait()  # blocks until all 3 arrive here
    print(f"{name} starting phase 2")  # all 3 print this "at once"
```

---

### 10. Queues — Producer/Consumer Patterns

#### Basic Queue

```python
import asyncio

async def producer(queue: asyncio.Queue, items: list):
    for item in items:
        await queue.put(item)
        print(f"Produced: {item}")
    await queue.put(None)  # sentinel to signal "done"

async def consumer(queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is None:
            break
        print(f"Consumed: {item}")
        await asyncio.sleep(0.5)  # simulate processing
        queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=10)  # bounded queue
    await asyncio.gather(
        producer(queue, ["a", "b", "c", "d", "e"]),
        consumer(queue),
    )
```

#### ADK Pattern: Event Queue for Parallel Agents

```python
async def event_bus():
    """Central event queue for multi-agent system."""
    queue: asyncio.Queue[Event] = asyncio.Queue()

    async def publish(event: Event):
        await queue.put(event)

    async def subscribe() -> AsyncGenerator[Event, None]:
        while True:
            event = await queue.get()
            yield event
            queue.task_done()

    return publish, subscribe
```

#### Priority Queue

```python
# Events with priority (lower number = higher priority)
pq = asyncio.PriorityQueue()

await pq.put((1, "urgent event"))
await pq.put((3, "low priority"))
await pq.put((2, "normal event"))

_, event = await pq.get()  # "urgent event" (priority 1)
_, event = await pq.get()  # "normal event" (priority 2)
```

---

### 11. Error Handling in Async Code

#### Basic Try/Except in Coroutines

```python
async def risky_operation():
    try:
        result = await call_external_api()
        return result
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        return None
    except asyncio.TimeoutError:
        print("Request timed out")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise  # re-raise unexpected errors
```

#### Errors in Tasks

```python
async def failing_task():
    await asyncio.sleep(1)
    raise ValueError("boom")

async def main():
    task = asyncio.create_task(failing_task())

    # Option 1: await the task — exception propagates
    try:
        result = await task
    except ValueError as e:
        print(f"Task failed: {e}")

    # Option 2: check the task later
    task = asyncio.create_task(failing_task())
    await asyncio.sleep(2)  # let it fail
    if task.done():
        if task.exception():
            print(f"Task failed: {task.exception()}")
        else:
            print(f"Task result: {task.result()}")
```

#### Exception Groups (Python 3.11+)

```python
# When multiple tasks fail simultaneously (e.g., in TaskGroup),
# you get an ExceptionGroup containing all the errors

async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_that_raises_value_error())
            tg.create_task(task_that_raises_type_error())
    except* ValueError as eg:
        # Handle all ValueErrors
        for exc in eg.exceptions:
            print(f"ValueError: {exc}")
    except* TypeError as eg:
        # Handle all TypeErrors
        for exc in eg.exceptions:
            print(f"TypeError: {exc}")
```

#### Error Handling Pattern for ADK Agents

```python
async def resilient_agent_run(
    agent,
    ctx: InvocationContext,
    max_retries: int = 3,
) -> AsyncGenerator[Event, None]:
    """Run an agent with retry logic for transient failures."""

    for attempt in range(max_retries):
        try:
            async for event in agent.run_async(ctx):
                yield event
            return  # success, exit

        except asyncio.CancelledError:
            # Don't retry cancellations — propagate immediately
            raise

        except (ConnectionError, asyncio.TimeoutError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # exponential backoff
                yield Event(
                    author="system",
                    content=f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}",
                )
                await asyncio.sleep(wait_time)
            else:
                yield Event(author="system", content=f"Failed after {max_retries} retries: {e}")
                raise
```

---

### 12. Timeouts and Cancellation

#### `asyncio.wait_for` — Timeout a Single Operation

```python
async def main():
    try:
        # If call_llm takes more than 30 seconds, raise TimeoutError
        result = await asyncio.wait_for(call_llm("hello"), timeout=30.0)
    except asyncio.TimeoutError:
        print("LLM call timed out!")
```

#### `asyncio.timeout` (Python 3.11+) — Timeout a Block

```python
async def main():
    try:
        async with asyncio.timeout(30.0):
            # Everything in this block must complete within 30 seconds
            response = await call_llm("hello")
            processed = await process_response(response)
            await save_result(processed)
    except TimeoutError:
        print("The entire operation timed out!")

# Deadline-based timeout
async def main():
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 30.0  # 30 seconds from now

    try:
        async with asyncio.timeout_at(deadline):
            await multi_step_operation()
    except TimeoutError:
        print("Missed the deadline!")
```

#### Task Cancellation

```python
async def long_running_task():
    try:
        while True:
            await asyncio.sleep(1)
            print("Still running...")
    except asyncio.CancelledError:
        # Clean up resources here
        print("Task was cancelled, cleaning up...")
        await cleanup_resources()
        raise  # IMPORTANT: re-raise CancelledError!
        # Swallowing CancelledError prevents proper cancellation

async def main():
    task = asyncio.create_task(long_running_task())
    await asyncio.sleep(3)

    task.cancel()             # request cancellation
    try:
        await task            # wait for cancellation to complete
    except asyncio.CancelledError:
        print("Task successfully cancelled")

    # Check if cancelled
    print(task.cancelled())   # True
```

#### Shielding from Cancellation

```python
async def critical_operation():
    """This must complete even if the parent is cancelled."""
    await save_to_database()

async def main():
    # shield() prevents cancellation from propagating to the inner coroutine
    task = asyncio.create_task(
        asyncio.shield(critical_operation())
    )
    task.cancel()  # the outer task is cancelled, but critical_operation continues
```

---

### 13. Mixing Sync and Async Code

#### Calling Sync Code from Async (Common in ADK)

```python
import asyncio

# Problem: you have a sync function that does CPU-heavy work
def compute_embeddings(text: str) -> list[float]:
    # CPU-intensive, takes 2 seconds
    return heavy_computation(text)

# ❌ WRONG: calling sync code directly blocks the event loop
async def bad_approach(text: str):
    result = compute_embeddings(text)  # blocks ALL other coroutines for 2s!
    return result

# ✅ RIGHT: run sync code in a thread pool
async def good_approach(text: str):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,  # None = default ThreadPoolExecutor
        compute_embeddings,
        text,
    )
    return result

# ✅ ALSO RIGHT: asyncio.to_thread (Python 3.9+) — simpler syntax
async def also_good(text: str):
    result = await asyncio.to_thread(compute_embeddings, text)
    return result
```

#### Calling Async Code from Sync (Entry Points)

```python
# Scenario: your main() is sync but you need to call async ADK code

# Option 1: asyncio.run() — the standard way
def main():
    result = asyncio.run(async_agent_function())

# Option 2: If an event loop is already running (Jupyter, some frameworks)
import nest_asyncio
nest_asyncio.apply()  # patches asyncio to allow nested run()
result = asyncio.run(async_function())

# Option 3: Running in a new thread (workaround for nested loops)
import concurrent.futures

def sync_wrapper():
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, async_function())
        return future.result()
```

#### The Deadly Sin: Blocking the Event Loop

```python
import time

# ❌ NEVER DO THIS — blocks the entire event loop
async def terrible():
    time.sleep(5)              # blocks everything!
    requests.get("https://...")  # blocks everything!
    open("huge_file").read()    # blocks everything!

# ✅ DO THIS INSTEAD
async def correct():
    await asyncio.sleep(5)                          # non-blocking sleep
    await aiohttp_session.get("https://...")         # async HTTP
    content = await asyncio.to_thread(Path("huge_file").read_text)  # offload to thread

# How to detect blocking calls: enable asyncio debug mode
asyncio.run(main(), debug=True)
# This will warn you when a coroutine takes too long without yielding
```

---

### 14. asyncio Streams — TCP/Network I/O

```python
# Low-level network I/O (rarely needed directly in ADK, but good to understand)

# TCP Client
async def tcp_client():
    reader, writer = await asyncio.open_connection("example.com", 80)

    writer.write(b"GET / HTTP/1.0\r\nHost: example.com\r\n\r\n")
    await writer.drain()  # flush the write buffer

    data = await reader.read(4096)
    print(data.decode())

    writer.close()
    await writer.wait_closed()

# TCP Server
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    data = await reader.readline()
    message = data.decode().strip()
    print(f"Received: {message}")

    writer.write(f"Echo: {message}\n".encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def tcp_server():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8888)
    async with server:
        await server.serve_forever()
```

---

### 15. Debugging asyncio

#### Debug Mode

```python
# Method 1: Environment variable
# PYTHONASYNCIODEBUG=1 python my_script.py

# Method 2: asyncio.run with debug=True
asyncio.run(main(), debug=True)

# Debug mode enables:
# - Warnings for coroutines that were never awaited
# - Warnings for callbacks that take too long (>100ms)
# - More detailed tracebacks
```

#### Common Mistakes and How to Spot Them

```python
# Mistake 1: Forgetting to await
async def oops():
    coroutine_function()  # ⚠️ RuntimeWarning: coroutine was never awaited
    # Fix: await coroutine_function()

# Mistake 2: Using sync sleep
async def oops2():
    import time
    time.sleep(5)  # blocks the entire loop! No warning by default.
    # Fix: await asyncio.sleep(5)

# Mistake 3: Forgetting that create_task needs a running loop
def not_async():
    task = asyncio.create_task(coro())  # RuntimeError: no running event loop
    # Fix: must be inside an async function

# Mistake 4: Awaiting inside a sync callback
async def main():
    loop = asyncio.get_running_loop()
    loop.call_soon(await coro())  # ❌ SyntaxError / unexpected behavior
    # Fix: loop.create_task(coro())

# Mistake 5: Not handling task exceptions
async def main():
    task = asyncio.create_task(failing_coro())
    await asyncio.sleep(10)
    # Task exception was never retrieved! Python warns about this on GC.
    # Fix: always await tasks or add done callbacks
```

#### Inspecting Running Tasks

```python
async def debug_tasks():
    # See all tasks currently running
    all_tasks = asyncio.all_tasks()
    for task in all_tasks:
        print(f"Task: {task.get_name()}, done={task.done()}")
        if not task.done():
            task.print_stack()  # print the coroutine stack trace

    # Get the currently executing task
    current = asyncio.current_task()
    print(f"Currently running: {current.get_name()}")
```

---

### 16. Performance Patterns and Pitfalls

#### Pattern: Bounded Concurrency for API Calls

> **ADK relevance:** This pattern directly applies to LLM rate limiting — use a `Semaphore` to cap concurrent calls to your LLM provider and avoid 429 errors.

```python
async def process_all_queries(queries: list[str], max_concurrent: int = 10):
    """Process queries with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def process_one(query: str) -> str:
        async with semaphore:
            return await call_llm(query)

    results = await asyncio.gather(*[process_one(q) for q in queries])
    return results
```

#### Pattern: Batch Processing with Async

```python
async def process_in_batches(items: list, batch_size: int = 10):
    """Process items in batches to avoid overwhelming resources."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_results = await asyncio.gather(*[process_item(item) for item in batch])
        results.extend(batch_results)
    return results
```

#### Pattern: Timeout with Fallback

```python
async def llm_with_fallback(prompt: str) -> str:
    """Try primary LLM, fall back to secondary on timeout."""
    try:
        return await asyncio.wait_for(primary_llm(prompt), timeout=10.0)
    except asyncio.TimeoutError:
        return await secondary_llm(prompt)  # cheaper/faster model
```

#### Pattern: Circuit Breaker

> **Note:** This is a simplified example for illustration. In production, protect concurrent access with `asyncio.Lock` and avoid calling `asyncio.get_running_loop()` in `__init__` (it fails outside a coroutine).

```python
class CircuitBreaker:
    def __init__(self, max_failures: int = 5, reset_timeout: float = 60.0):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed = normal, open = failing, half-open = testing
        self._lock = asyncio.Lock()  # protect concurrent access

    async def call(self, coro):
        if self.state == "open":
            if asyncio.get_running_loop().time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
            else:
                raise RuntimeError("Circuit breaker is open")

        try:
            result = await coro
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = asyncio.get_running_loop().time()
            if self.failure_count >= self.max_failures:
                self.state = "open"
            raise

# Usage
breaker = CircuitBreaker(max_failures=3, reset_timeout=30.0)

async def safe_llm_call(prompt: str):
    return await breaker.call(call_llm(prompt))
```

#### Pitfall: Creating Too Many Tasks

```python
# ❌ BAD: 1 million tasks at once
async def bad():
    tasks = [asyncio.create_task(process(i)) for i in range(1_000_000)]
    results = await asyncio.gather(*tasks)  # OOM!

# ✅ GOOD: bounded concurrency
async def good():
    sem = asyncio.Semaphore(100)
    async def bounded(i):
        async with sem:
            return await process(i)
    results = await asyncio.gather(*[bounded(i) for i in range(1_000_000)])
```

---

### 17. ADK-Specific Async Patterns

#### Pattern: The ADK Runner Loop

```python
async def runner_loop(agent, session_service, query: str) -> AsyncGenerator[Event, None]:
    """Simplified version of how ADK's Runner works."""
    session = await session_service.get_or_create_session("user-1", "app-1")
    ctx = InvocationContext(agent=agent, session=session, services=services)

    all_events = []
    async for event in agent.run_async(ctx):
        # Process each event as it streams
        all_events.append(event)

        # Apply state changes
        if event.actions and event.actions.state_delta:
            for key, value in event.actions.state_delta.items():
                if value is None:
                    session.state.pop(key, None)
                else:
                    session.state[key] = value

        # Handle agent transfer
        if event.actions and event.actions.transfer_to_agent:
            target = find_agent(event.actions.transfer_to_agent)
            ctx = ctx.model_copy(update={"agent": target})
            async for sub_event in target.run_async(ctx):
                all_events.append(sub_event)
                yield sub_event
            continue  # skip yielding the transfer event itself

        yield event

    # Persist session
    await session_service.save_session(session)
```

#### Pattern: Callback Chain (Before/After Hooks)

```python
async def execute_with_callbacks(agent, ctx: InvocationContext):
    """ADK-style callback chain for agent execution."""

    # Before callback — can short-circuit
    if agent.before_agent_callback:
        override = await agent.before_agent_callback(ctx)
        if override is not None:
            yield override  # skip agent, yield the override event
            return

    # Main agent execution
    async for event in agent.run_async(ctx):
        # Before model callback (per-turn)
        if agent.before_model_callback:
            modified = await agent.before_model_callback(event, ctx)
            if modified:
                event = modified

        yield event

    # After callback
    if agent.after_agent_callback:
        final_event = await agent.after_agent_callback(ctx)
        if final_event:
            yield final_event
```

#### Pattern: Concurrent Tool Execution

```python
async def execute_tools_concurrently(
    tool_calls: list[dict],
    tools: dict[str, BaseTool],
    ctx: ToolContext,
) -> list[Event]:
    """Execute multiple tool calls concurrently (like ADK does)."""

    async def run_single_tool(tool_call: dict) -> Event:
        tool = tools[tool_call["name"]]
        try:
            result = await asyncio.wait_for(
                tool.run_async(args=tool_call["args"], tool_context=ctx),
                timeout=30.0,
            )
            return Event(
                author=f"tool:{tool_call['name']}",
                content=str(result),
                event_type="tool_result",
            )
        except asyncio.TimeoutError:
            return Event(
                author=f"tool:{tool_call['name']}",
                content="Tool execution timed out",
                event_type="tool_error",
            )
        except Exception as e:
            return Event(
                author=f"tool:{tool_call['name']}",
                content=f"Tool error: {e}",
                event_type="tool_error",
            )

    # Run all tools concurrently
    results = await asyncio.gather(*[
        run_single_tool(tc) for tc in tool_calls
    ])
    return results
```

#### Pattern: Session Locking

```python
class SessionService:
    """Session service with per-session locking to prevent concurrent writes."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    async def update_session(self, session_id: str, state_delta: dict):
        async with self._get_lock(session_id):
            session = self._sessions[session_id]
            for key, value in state_delta.items():
                if value is None:
                    session.state.pop(key, None)
                else:
                    session.state[key] = value
            await self._persist(session)
```

---

### 18. Complete Reference: Java → Python Async Mapping

| Java | Python asyncio | Notes |
|------|---------------|-------|
| `ExecutorService` | Event loop | Single-threaded in Python |
| `CompletableFuture<T>` | `Coroutine[Any, Any, T]` / `Task[T]` | `await` instead of `.get()` |
| `future.get()` | `await task` | |
| `future.get(5, SECONDS)` | `await asyncio.wait_for(task, 5.0)` | |
| `CompletableFuture.allOf(a,b,c)` | `asyncio.gather(a,b,c)` | |
| `CompletableFuture.anyOf(a,b,c)` | `asyncio.wait(tasks, return_when=FIRST_COMPLETED)` | |
| `future.thenApply(fn)` | `result = await task; fn(result)` | Just await and call |
| `future.thenCompose(fn)` | `result = await task; result2 = await fn(result)` | |
| `future.exceptionally(fn)` | `try: await task except: fn()` | |
| `future.cancel()` | `task.cancel()` | |
| `future.isDone()` | `task.done()` | |
| `Thread.sleep(ms)` | `await asyncio.sleep(seconds)` | NEVER use `time.sleep` in async |
| `Semaphore` | `asyncio.Semaphore` | Same concept, async API |
| `ReentrantLock` | `asyncio.Lock` | Not reentrant in Python! |
| `CountDownLatch` | `asyncio.Barrier` (3.11+) | |
| `BlockingQueue` | `asyncio.Queue` | |
| `synchronized` | `async with lock:` | |
| `StructuredTaskScope` (Java 21) | `asyncio.TaskGroup` (Python 3.11+) | Same concept |
| `Stream<T>` | `AsyncGenerator[T, None]` | Lazy, streaming |
| `@Async` (Spring) | `async def` | |
| `Mono<T>` / `Flux<T>` (Reactor) | Coroutine / AsyncGenerator | Reactive vs coroutine — note asyncio is **pull-based** (consumer drives iteration); Reactor is push-based (publisher pushes to subscriber). |

#### Key Mindset Shifts

**1. No threads by default.** Java developers instinctively think "concurrent = threads." In asyncio, everything is one thread. Concurrency comes from cooperative yielding at `await` points.

**2. `await` is not `.get()`.** Java's `future.get()` blocks the calling thread. Python's `await` *suspends* the coroutine and lets other coroutines run. It's non-blocking.

**3. No need for `synchronized`.** Since asyncio is single-threaded, there are no data races from parallel execution. You only need `asyncio.Lock` when multiple coroutines interleave their `await` points while modifying shared state.

**4. CPU-bound work needs threads.** asyncio doesn't parallelize CPU work. Use `asyncio.to_thread()` or `ProcessPoolExecutor` for CPU-intensive tasks.

**5. Everything is explicit.** Java's Spring `@Async` magically makes things async. In Python, you see every `async def` and `await` — no hidden magic.

---

## ADK in Practice

asyncio patterns map directly to ADK components:

| asyncio Concept | ADK Usage |
|---|---|
| `async def` + `await` | Every agent method, tool function, and callback |
| `AsyncGenerator` | `run_async() -> AsyncGenerator[Event, None]` -- the core streaming API |
| `asyncio.gather()` | `ParallelAgent` runs sub-agents concurrently |
| `asyncio.TaskGroup` | Structured concurrency for tool execution |
| `asyncio.Semaphore` | Rate-limiting LLM API calls |
| `asyncio.Queue` | Event bus for parallel agent communication |
| `asyncio.Lock` | Session locking to prevent concurrent writes |
| `asyncio.wait_for()` | Tool execution timeouts |
| `async with` | MCP toolset connections, session management |
| `asyncio.to_thread()` | Running CPU-bound work without blocking the event loop |

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `time.sleep()` in async code | Entire event loop freezes | Use `await asyncio.sleep()` |
| Forgetting to `await` a coroutine | RuntimeWarning, coroutine never runs | Add `await` or `create_task()` |
| `asyncio.run()` inside async code | RuntimeError: loop already running | Just `await` directly |
| Not handling task exceptions | Silent failures, "exception never retrieved" | Always `await` tasks or add callbacks |
| Creating too many tasks at once | Memory exhaustion | Use `asyncio.Semaphore` for bounded concurrency |
| Blocking I/O (requests, open()) in async | Event loop stalls for all coroutines | Use `aiohttp`, `asyncio.to_thread()` |

## Quick Reference Card

```
asyncio.run(main())              Entry point from sync code
await coro()                     Suspend until result ready
asyncio.create_task(coro())      Schedule concurrent execution
asyncio.gather(a, b, c)         Run multiple, return all results
asyncio.wait(tasks)              More control over completion
asyncio.as_completed(coros)      Process results as they arrive
asyncio.TaskGroup()              Structured concurrency (3.11+)
asyncio.wait_for(coro, timeout)  Timeout a single operation
asyncio.timeout(seconds)         Timeout a block (3.11+)
asyncio.Semaphore(n)             Limit concurrent operations
asyncio.Lock()                   Mutual exclusion
asyncio.Queue()                  Producer/consumer
asyncio.to_thread(fn)            Run sync code in thread pool
task.cancel()                    Request cancellation
asyncio.shield(coro)             Protect from cancellation
```
