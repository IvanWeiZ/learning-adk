# Python asyncio — Deep Dive

> **ADK relevance:** ADK is async-first -- every agent, LLM call, and tool execution uses asyncio | **Estimated time:** 4-6 hours

## At a Glance

```
+------------------------------------------------------------------+
|              Python asyncio Architecture                          |
|                                                                   |
|  +------------------------------------------------------+        |
|  |                    Event Loop                          |        |
|  |  +---------+  +---------+  +---------+                |        |
|  |  |Coroutine|  |Coroutine|  |Coroutine|  ...           |        |
|  |  | (LLM    |  | (DB     |  | (Tool   |                |        |
|  |  |  call)  |  |  query) |  |  exec)  |                |        |
|  |  +----+----+  +----+----+  +----+----+                |        |
|  |       |await        |await       |await               |        |
|  |       v             v            v                    |        |
|  |  +------------------------------------------+         |        |
|  |  |     I/O Multiplexer (select/epoll)       |         |        |
|  |  +------------------------------------------+         |        |
|  +------------------------------------------------------+        |
|                                                                   |
|  Single thread, cooperative multitasking.                         |
|  Coroutines yield at await points, letting others run.            |
|  No threads, no locks, no context-switch overhead.                |
+------------------------------------------------------------------+
```

Python's asyncio provides single-threaded cooperative multitasking for I/O-bound work. Unlike Java's thread-per-request model, asyncio runs everything on one thread -- when a coroutine hits `await`, it yields control to the event loop, which runs other ready coroutines. This guide covers every asyncio concept you need for ADK development, from basic coroutines through advanced patterns like structured concurrency and async generators.

## Core Concepts

### [ ] 1. The Mental Model -- Why asyncio Exists

#### [ ] The Problem

Your ADK agent calls an LLM API (takes 2 seconds), then searches a database (takes 0.5 seconds), then calls another API (takes 1 second). In synchronous code, that's 3.5 seconds of wall time — but your CPU is idle for 99% of it, just waiting for network responses.

#### [ ] Java's Answer: Threads

```java
// Java uses thread pools — each thread blocks independently
ExecutorService pool = Executors.newFixedThreadPool(10);
Future<String> llmFuture = pool.submit(() -> callLlm(prompt));
Future<String> dbFuture = pool.submit(() -> queryDb(query));
String llmResult = llmFuture.get();  // blocks this thread, but others continue
```

Java gives each task its own thread. Simple mental model, but threads are expensive (~1MB stack each), context switching has overhead, and shared mutable state needs locks.

#### [ ] Python's Answer: Cooperative Multitasking (asyncio)

```python
# Python uses a SINGLE thread with cooperative scheduling
async def main():
    llm_task = asyncio.create_task(call_llm(prompt))
    db_task = asyncio.create_task(query_db(query))
    llm_result = await llm_task    # suspends, lets db_task run
    db_result = await db_task
```

asyncio runs everything on **one thread**. When a coroutine hits `await` (an I/O wait), it **yields control** back to the event loop, which runs other coroutines. No threads, no locks, no context switching overhead.

#### [ ] The Key Insight

```
Thread-based (Java):           Async (Python):
┌──────────┐ ┌──────────┐     ┌─────────────────────────────────┐
│ Thread 1 │ │ Thread 2 │     │         Single Thread            │
│          │ │          │     │                                   │
│ call_llm │ │ query_db │     │ call_llm ──await──┐              │
│ (blocked)│ │ (blocked)│     │                   │ query_db     │
│          │ │          │     │                   │ ──await──┐   │
│ (result) │ │ (result) │     │ (llm resumes)←───┘          │   │
│          │ │          │     │                (db resumes)←─┘   │
└──────────┘ └──────────┘     └─────────────────────────────────┘
2 threads, 2 OS resources       1 thread, interleaved execution
```

**The tradeoff:** asyncio is more efficient for I/O-bound work (network calls, file I/O, database queries), but **every coroutine must cooperate**. If one coroutine does heavy CPU work without yielding, it blocks everything.

---

### [ ] 2. Coroutines — The Building Block

#### [ ] Defining Coroutines

```python
import asyncio

# A regular function
def regular_function():
    return "I run synchronously"

# A coroutine function (defined with `async def`)
async def coroutine_function():
    return "I run asynchronously"

# CRITICAL DIFFERENCE:
result = regular_function()        # Returns "I run synchronously"
result = coroutine_function()      # Returns a coroutine OBJECT, not the string!
                                    # <coroutine object coroutine_function at 0x...>

# You must AWAIT a coroutine to get its result
async def main():
    result = await coroutine_function()  # NOW returns "I run asynchronously"
```

#### [ ] What `await` Actually Does

```python
async def fetch_data(url: str) -> dict:
    print("1. Starting fetch")

    # await does THREE things:
    # 1. Suspends this coroutine
    # 2. Returns control to the event loop
    # 3. Resumes here when the awaited thing completes
    response = await http_client.get(url)  # <-- suspension point

    print("2. Got response")  # runs after response arrives
    return response.json()
```

Think of `await` as a **polite pause**: "I'm waiting for something; event loop, please run other tasks while I wait."

#### [ ] Coroutines Are Not Magic — They're Generators Under the Hood

```python
# Conceptually, this is what Python does with async/await:
# (simplified — don't write code this way, this is for understanding)

# async def fetch():
#     data = await get_data()
#     return process(data)
#
# Is roughly equivalent to:
#
# def fetch():
#     data = yield get_data()   # yield = suspension point
#     return process(data)

# The event loop acts as the "driver" that sends results back in via .send()
```

#### [ ] Awaitable Objects

```python
# Three things can be awaited:

# 1. Coroutines (from async def)
async def coro():
    return 42
await coro()

# 2. Tasks (scheduled coroutines)
task = asyncio.create_task(coro())
await task

# 3. Futures (low-level, rarely used directly)
future = asyncio.get_running_loop().create_future()
# ... something sets future.set_result(42) later
await future

# You can also make custom awaitable objects:
class CustomAwaitable:
    def __await__(self):
        yield  # must yield at least once
        return 42

await CustomAwaitable()  # returns 42
```

---

### [ ] 3. The Event Loop — How It All Runs

#### [ ] The Event Loop Is the Scheduler

```python
# The event loop is a while-True loop that:
# 1. Checks for completed I/O operations
# 2. Runs callbacks for completed operations
# 3. Runs ready coroutines until they hit the next await
# 4. Repeats

# Pseudocode of what asyncio does internally:
# while tasks_exist:
#     ready_callbacks = poll_for_io_completions()
#     for callback in ready_callbacks:
#         callback()
#     for task in ready_tasks:
#         task.step()  # run until next await
```

#### [ ] Starting the Event Loop

```python
# Method 1: asyncio.run() — the standard entry point
async def main():
    result = await do_work()
    print(result)

asyncio.run(main())  # creates loop, runs main(), closes loop

# Method 2: Running in an existing loop (e.g., inside Jupyter/ADK)
# If an event loop is already running, you can't call asyncio.run()
# Instead, create tasks directly:
loop = asyncio.get_running_loop()
task = loop.create_task(do_work())

# Method 3: Low-level (rarely needed)
loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(main())
finally:
    loop.close()
```

#### [ ] Getting the Running Loop

```python
async def some_coroutine():
    # Inside a coroutine, you can get the current loop
    loop = asyncio.get_running_loop()

    # Schedule a callback on the loop (low-level)
    loop.call_soon(callback_func, arg1, arg2)

    # Schedule a callback after a delay
    loop.call_later(5.0, callback_func, arg1)

    # Schedule a callback at a specific time
    loop.call_at(loop.time() + 5.0, callback_func, arg1)
```

#### [ ] One Loop Per Thread — The Rule

```python
# asyncio.run() creates ONE event loop on the current thread
# You CANNOT nest asyncio.run() calls:

async def inner():
    return 42

async def outer():
    # ❌ WRONG: RuntimeError: This event loop is already running
    result = asyncio.run(inner())

# ✅ RIGHT: just await
async def outer():
    result = await inner()
```

---

### [ ] 4. Tasks — Concurrent Execution

#### [ ] Sequential vs Concurrent — Timeline

```
Sequential (plain await):
    ┌──────────────────────────────────────────────────────┐
    │ t=0        t=2        t=3       t=4.5                │
    │  │──── A ────│── B ──│── C ───│                      │
    │  2s           1s       1.5s    total = 4.5s           │
    └──────────────────────────────────────────────────────┘

Concurrent (create_task + await):
    ┌──────────────────────────────────────────────────────┐
    │ t=0                   t=2                            │
    │  │──────── A ────────│                               │
    │  │──── B ────│        (done at t=1)                  │
    │  │────── C ──────│    (done at t=1.5)                │
    │                       total = 2.0s (slowest task)    │
    └──────────────────────────────────────────────────────┘
```

#### [ ] The Difference Between `await` and `create_task`

```python
import asyncio
import time

async def slow_operation(name: str, delay: float) -> str:
    print(f"  {name}: starting")
    await asyncio.sleep(delay)  # simulate I/O
    print(f"  {name}: done")
    return f"{name} result"


# SEQUENTIAL — one after another
async def sequential():
    start = time.time()
    a = await slow_operation("A", 2.0)   # wait 2s
    b = await slow_operation("B", 1.0)   # then wait 1s
    c = await slow_operation("C", 1.5)   # then wait 1.5s
    print(f"Total: {time.time() - start:.1f}s")  # ~4.5s
    return a, b, c


# CONCURRENT — all at once
async def concurrent():
    start = time.time()
    task_a = asyncio.create_task(slow_operation("A", 2.0))
    task_b = asyncio.create_task(slow_operation("B", 1.0))
    task_c = asyncio.create_task(slow_operation("C", 1.5))
    a = await task_a
    b = await task_b
    c = await task_c
    print(f"Total: {time.time() - start:.1f}s")  # ~2.0s (limited by slowest)
    return a, b, c
```

**Java equivalent:**
```java
// Sequential: a.get(); b.get(); c.get();
// Concurrent: CompletableFuture.allOf(a, b, c).join();
```

#### [ ] Task Naming (For Debugging)

```python
task = asyncio.create_task(
    slow_operation("fetch_llm", 2.0),
    name="llm-call-1"  # shows up in debugging/logging
)
print(task.get_name())  # "llm-call-1"
```

#### [ ] Task Callbacks

```python
async def main():
    task = asyncio.create_task(slow_operation("A", 1.0))

    # Add a callback that fires when the task completes
    def on_done(t: asyncio.Task):
        if t.exception():
            print(f"Task failed: {t.exception()}")
        else:
            print(f"Task result: {t.result()}")

    task.add_done_callback(on_done)
    await task
```

#### [ ] Fire and Forget (Background Tasks)

```python
# Sometimes you want to start a task and not await it
async def log_event(event: dict):
    await db.insert(event)

async def handle_request(query: str):
    # Fire and forget — don't wait for logging
    asyncio.create_task(log_event({"query": query}))

    # But WARNING: if the task raises an exception, it's silently lost!
    # Python 3.12 warns about this. Best practice:

    background_tasks = set()

    task = asyncio.create_task(log_event({"query": query}))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)  # prevent GC
```

---

### [ ] 5. Gathering and Waiting

#### [ ] `asyncio.gather` — Run Multiple Coroutines Concurrently

```python
async def call_llm(prompt: str) -> str:
    await asyncio.sleep(2)
    return f"LLM: {prompt}"

async def search_db(query: str) -> list:
    await asyncio.sleep(1)
    return [f"result for {query}"]

async def call_api(endpoint: str) -> dict:
    await asyncio.sleep(0.5)
    return {"endpoint": endpoint, "status": "ok"}


# gather runs all three concurrently and returns results in ORDER
async def main():
    results = await asyncio.gather(
        call_llm("hello"),
        search_db("python"),
        call_api("/status"),
    )
    # results is a list in the SAME ORDER as the arguments:
    # ["LLM: hello", ["result for python"], {"endpoint": "/status", "status": "ok"}]
    llm_result, db_result, api_result = results
```

#### [ ] `gather` with Error Handling

```python
async def failing_task():
    raise ValueError("something broke")

# DEFAULT: if any task fails, gather raises immediately
async def main():
    try:
        results = await asyncio.gather(
            call_llm("hello"),
            failing_task(),        # raises!
            search_db("python"),
        )
    except ValueError as e:
        print(f"One task failed: {e}")
        # But what about the other tasks? They might still be running!

# BETTER: return_exceptions=True collects exceptions as results
async def main_safe():
    results = await asyncio.gather(
        call_llm("hello"),
        failing_task(),
        search_db("python"),
        return_exceptions=True,  # don't raise, return exceptions in the list
    )
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i} failed: {result}")
        else:
            print(f"Task {i} succeeded: {result}")
    # Output:
    # Task 0 succeeded: LLM: hello
    # Task 1 failed: something broke
    # Task 2 succeeded: ['result for python']
```

#### [ ] `asyncio.wait` — More Control Over Completion

```python
async def main():
    tasks = [
        asyncio.create_task(call_llm("q1"), name="llm"),
        asyncio.create_task(search_db("q2"), name="db"),
        asyncio.create_task(call_api("/health"), name="api"),
    ]

    # Wait for ALL to complete (like gather, but returns sets)
    done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
    for task in done:
        print(f"{task.get_name()}: {task.result()}")

    # Wait for the FIRST one to complete
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    first_result = done.pop().result()
    # Cancel the rest if you don't need them
    for task in pending:
        task.cancel()

    # Wait for the FIRST EXCEPTION
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
```

#### [ ] `asyncio.as_completed` — Process Results As They Arrive

```python
async def main():
    coros = [
        call_llm("prompt1"),     # takes 2s
        search_db("query1"),     # takes 1s
        call_api("/endpoint"),   # takes 0.5s
    ]

    # Results arrive in completion order, not input order
    for coro in asyncio.as_completed(coros):
        result = await coro
        print(f"Got result: {result}")
        # Prints:
        # Got result: {"endpoint": ...}     (0.5s — fastest)
        # Got result: ["result for ..."]    (1.0s)
        # Got result: "LLM: ..."           (2.0s — slowest)
```

**Java equivalent:** `CompletableFuture.anyOf()` for FIRST_COMPLETED, `allOf()` for ALL_COMPLETED.

---

### [ ] 6. TaskGroup — Structured Concurrency (Python 3.11+)

TaskGroup is the modern replacement for `gather`. It guarantees that all tasks are cleaned up, even on failure.

#### [ ] Basic Usage

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(call_llm("hello"))
        task2 = tg.create_task(search_db("python"))
        task3 = tg.create_task(call_api("/status"))

    # When the `async with` block exits, ALL tasks are guaranteed complete
    print(task1.result())
    print(task2.result())
    print(task3.result())
```

#### [ ] Error Handling with TaskGroup

```python
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            task1 = tg.create_task(call_llm("hello"))
            task2 = tg.create_task(failing_task())       # will fail
            task3 = tg.create_task(search_db("python"))

    except* ValueError as eg:
        # Python 3.11 ExceptionGroup — can catch MULTIPLE exceptions
        for exc in eg.exceptions:
            print(f"Caught ValueError: {exc}")
        # When one task fails, TaskGroup CANCELS all other tasks
        # This is the key difference from gather
    except* TypeError as eg:
        # except* can catch different exception types in separate clauses
        # NOTE: each except* clause must match a DIFFERENT exception type
        for exc in eg.exceptions:
            print(f"Caught TypeError: {exc}")
```

#### [ ] Why TaskGroup > gather

```python
# Problem with gather: if task2 fails, task1 and task3 keep running
# as "orphaned" tasks. You have to manually cancel them.

# gather — manual cleanup needed
async def fragile():
    tasks = [
        asyncio.create_task(slow_task(10)),
        asyncio.create_task(failing_task()),
        asyncio.create_task(slow_task(10)),
    ]
    try:
        results = await asyncio.gather(*tasks)
    except Exception:
        for t in tasks:
            t.cancel()  # you have to remember this!
        raise

# TaskGroup — automatic cleanup
async def robust():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(slow_task(10))
        tg.create_task(failing_task())
        tg.create_task(slow_task(10))
    # If failing_task() raises, the other two are automatically cancelled
    # and the TaskGroup waits for them to finish cancellation
```

**Java equivalent:** Java 21's `StructuredTaskScope` (Project Loom) is directly inspired by the same "structured concurrency" concept.

---

### [ ] 7. AsyncGenerator and `async for`

This is the **most important section for ADK**. ADK streams events through async generators.

#### [ ] Sync Generator Recap

```python
# Sync generator: function that yields values lazily
def count_up(n: int):
    for i in range(n):
        yield i         # pauses here, resumes on next()

for num in count_up(5):
    print(num)  # 0, 1, 2, 3, 4
```

#### [ ] Async Generator — yield + await

```python
from typing import AsyncGenerator

# Async generator: yields values lazily AND can await between yields
async def fetch_pages(urls: list[str]) -> AsyncGenerator[dict, None]:
    for url in urls:
        response = await http_client.get(url)  # async I/O
        yield response.json()                   # yield result

# Consumed with `async for`
async def main():
    urls = ["https://api.com/page/1", "https://api.com/page/2"]
    async for page_data in fetch_pages(urls):
        print(page_data)
```

#### [ ] The ADK Pattern — Streaming Events

```python
from typing import AsyncGenerator
from dataclasses import dataclass

@dataclass
class Event:
    author: str
    content: str
    event_type: str = "text"

# This is exactly how ADK agents work:
async def run_agent(query: str) -> AsyncGenerator[Event, None]:
    # Step 1: Emit a "thinking" event
    yield Event(author="agent", content="Processing your query...", event_type="thinking")

    # Step 2: Call the LLM (async I/O)
    llm_response = await call_llm(query)

    # Step 3: If the LLM wants to use a tool, emit tool events
    if llm_response.tool_call:
        yield Event(
            author="agent",
            content=f"Calling tool: {llm_response.tool_call.name}",
            event_type="tool_call",
        )
        tool_result = await execute_tool(llm_response.tool_call)
        yield Event(
            author="tool",
            content=tool_result,
            event_type="tool_result",
        )

    # Step 4: Emit the final response
    yield Event(author="agent", content=llm_response.text, event_type="response")


# Consumer — the Runner collects events
async def run(query: str):
    async for event in run_agent(query):
        print(f"[{event.event_type}] {event.author}: {event.content}")
```

#### [ ] Composing Async Generators (Sequential Agents)

```python
# Python does NOT support `async yield from` — you must loop manually

# ❌ WRONG — syntax error
async def sequential_agents(agents, query):
    for agent in agents:
        async yield from agent.run(query)  # SyntaxError!

# ✅ RIGHT — explicit async for loop
async def sequential_agents(agents, query) -> AsyncGenerator[Event, None]:
    for agent in agents:
        async for event in agent.run(query):
            yield event
```

#### [ ] Composing Async Generators (Parallel Agents)

```python
import asyncio
from typing import AsyncGenerator

async def parallel_agents(agents, query) -> AsyncGenerator[Event, None]:
    """Run agents in parallel, yield events as they arrive."""
    queue: asyncio.Queue[Event | None] = asyncio.Queue()

    async def run_and_enqueue(agent):
        async for event in agent.run(query):
            await queue.put(event)
        await queue.put(None)  # sentinel: this agent is done

    # Start all agents concurrently
    # NOTE: yield cannot be used inside `async with TaskGroup()` —
    # it would be a SyntaxError. Instead, enqueue events and yield after.
    async with asyncio.TaskGroup() as tg:
        for agent in agents:
            tg.create_task(run_and_enqueue(agent))

    # Yield events after TaskGroup exits (all tasks done)
    while not queue.empty():
        event = queue.get_nowait()
        if event is not None:
            yield event
```

#### [ ] Async Generator Cleanup

```python
async def streaming_llm(prompt: str) -> AsyncGenerator[str, None]:
    connection = await open_llm_connection(prompt)
    try:
        async for chunk in connection.stream():
            yield chunk
    finally:
        # This runs when the generator is closed (GC'd or .aclose() called)
        # CRITICAL: cleanup resources here
        await connection.close()

# If the consumer stops early, finally still runs:
async def main():
    async for chunk in streaming_llm("hello"):
        print(chunk)
        if "stop" in chunk:
            break  # triggers the generator's finally block
```

#### [ ] Async Comprehensions

```python
# List comprehension with async for
events = [event async for event in agent.run_async(ctx)]

# With filtering
errors = [e async for e in agent.run_async(ctx) if e.event_type == "error"]

# Async generator expression
event_stream = (e async for e in agent.run_async(ctx))
# This is lazy — doesn't execute until iterated
```

---

### [ ] 8. Async Context Managers (`async with`)

#### [ ] The Protocol

```python
class AsyncDatabaseConnection:
    async def __aenter__(self):
        # Setup: called when entering `async with`
        self.conn = await create_connection()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Teardown: ALWAYS called when exiting `async with`, even on exception
        await self.conn.close()
        return False  # False = don't suppress exceptions

# Usage
async def main():
    async with AsyncDatabaseConnection() as conn:
        await conn.execute("SELECT * FROM users")
    # conn.close() is guaranteed to be called
```

**Java equivalent:** try-with-resources, but async.

#### [ ] Using `contextlib.asynccontextmanager`

```python
from contextlib import asynccontextmanager

# Much more concise — use a generator instead of a class
@asynccontextmanager
async def managed_session(session_id: str):
    session = await load_session(session_id)
    try:
        yield session        # <-- everything before yield is __aenter__
    finally:
        await session.save() # <-- everything after yield is __aexit__
        await session.close()

async def main():
    async with managed_session("abc-123") as session:
        session.state["count"] += 1
```

#### [ ] Nested Async Context Managers

```python
# Nesting
async def main():
    async with managed_session("abc") as session:
        async with managed_llm_client() as llm:
            result = await llm.generate("hello")
            session.state["result"] = result

# Or use AsyncExitStack for dynamic nesting
from contextlib import AsyncExitStack

async def main(tool_configs: list):
    async with AsyncExitStack() as stack:
        tools = []
        for config in tool_configs:
            tool = await stack.enter_async_context(managed_tool(config))
            tools.append(tool)

        # All tools are now initialized
        # When the block exits, they're all cleaned up in reverse order
```

#### [ ] ADK Example: MCP Toolset Connection

```python
# ADK's McpToolset is a BaseToolset passed directly to an agent
# (MCPToolset is deprecated; use McpToolset instead)
from google.adk.tools import McpToolset

toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"],
    ),
)

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    tools=[toolset],  # toolset is passed directly; cleanup is automatic
)
```

---

### [ ] 9. Synchronization Primitives

Even though asyncio is single-threaded, you still need synchronization when multiple coroutines share state.

#### [ ] Lock — Mutual Exclusion

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

#### [ ] Semaphore — Limit Concurrency

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

#### [ ] BoundedSemaphore — Semaphore That Catches Bugs

```python
# BoundedSemaphore raises ValueError if you release more than you acquire
sem = asyncio.BoundedSemaphore(3)
# Useful for catching programming errors where release is called too many times
```

#### [ ] Event — Signal Between Coroutines

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

#### [ ] Condition — Wait for Complex Conditions

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

#### [ ] Barrier (Python 3.11+) — Wait for N Coroutines

```python
barrier = asyncio.Barrier(3)  # wait until 3 coroutines arrive

async def worker(name: str):
    print(f"{name} starting phase 1")
    await asyncio.sleep(1)
    await barrier.wait()  # blocks until all 3 arrive here
    print(f"{name} starting phase 2")  # all 3 print this "at once"
```

---

### [ ] 10. Queues — Producer/Consumer Patterns

#### [ ] Basic Queue

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

#### [ ] ADK Pattern: Event Queue for Parallel Agents

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

#### [ ] Priority Queue

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

### [ ] 11. Error Handling in Async Code

#### [ ] Basic Try/Except in Coroutines

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

#### [ ] Errors in Tasks

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

#### [ ] Exception Groups (Python 3.11+)

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

#### [ ] Error Handling Pattern for ADK Agents

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

### [ ] 12. Timeouts and Cancellation

#### [ ] `asyncio.wait_for` — Timeout a Single Operation

```python
async def main():
    try:
        # If call_llm takes more than 30 seconds, raise TimeoutError
        result = await asyncio.wait_for(call_llm("hello"), timeout=30.0)
    except asyncio.TimeoutError:
        print("LLM call timed out!")
```

#### [ ] `asyncio.timeout` (Python 3.11+) — Timeout a Block

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

#### [ ] Task Cancellation

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

#### [ ] Shielding from Cancellation

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

### [ ] 13. Mixing Sync and Async Code

#### [ ] Calling Sync Code from Async (Common in ADK)

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

#### [ ] Calling Async Code from Sync (Entry Points)

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

#### [ ] The Deadly Sin: Blocking the Event Loop

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

### [ ] 14. asyncio Streams — TCP/Network I/O

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

### [ ] 15. Debugging asyncio

#### [ ] Debug Mode

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

#### [ ] Common Mistakes and How to Spot Them

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

#### [ ] Inspecting Running Tasks

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

### [ ] 16. Performance Patterns and Pitfalls

#### [ ] Pattern: Bounded Concurrency for API Calls

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

#### [ ] Pattern: Batch Processing with Async

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

#### [ ] Pattern: Timeout with Fallback

```python
async def llm_with_fallback(prompt: str) -> str:
    """Try primary LLM, fall back to secondary on timeout."""
    try:
        return await asyncio.wait_for(primary_llm(prompt), timeout=10.0)
    except asyncio.TimeoutError:
        return await secondary_llm(prompt)  # cheaper/faster model
```

#### [ ] Pattern: Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, max_failures: int = 5, reset_timeout: float = 60.0):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed = normal, open = failing, half-open = testing

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

#### [ ] Pitfall: Creating Too Many Tasks

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

### [ ] 17. ADK-Specific Async Patterns

#### [ ] Pattern: The ADK Runner Loop

```python
async def runner_loop(agent, session_service, query: str):
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

        yield event

    # Persist session
    await session_service.save_session(session)
```

#### [ ] Pattern: Callback Chain (Before/After Hooks)

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

#### [ ] Pattern: Concurrent Tool Execution

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

#### [ ] Pattern: Session Locking

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

### [ ] 18. Complete Reference: Java → Python Async Mapping

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
| `Mono<T>` / `Flux<T>` (Reactor) | Coroutine / AsyncGenerator | Reactive vs coroutine |

#### [ ] Key Mindset Shifts

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
