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

### 1. The Mental Model -- Why asyncio Exists

#### The Problem

Your ADK agent calls an LLM API (takes 2 seconds), then searches a database (takes 0.5 seconds), then calls another API (takes 1 second). In synchronous code, that's 3.5 seconds of wall time — but your CPU is idle for 99% of it, just waiting for network responses.

#### Java's Answer: Threads

```java
// Java uses thread pools — each thread blocks independently
ExecutorService pool = Executors.newFixedThreadPool(10);
Future<String> llmFuture = pool.submit(() -> callLlm(prompt));
Future<String> dbFuture = pool.submit(() -> queryDb(query));
String llmResult = llmFuture.get();  // blocks this thread, but others continue
```

Java gives each task its own thread. Simple mental model, but threads are expensive (~1MB stack each), context switching has overhead, and shared mutable state needs locks.

#### Python's Answer: Cooperative Multitasking (asyncio)

```python
# Python uses a SINGLE thread with cooperative scheduling
async def main():
    llm_task = asyncio.create_task(call_llm(prompt))
    db_task = asyncio.create_task(query_db(query))
    llm_result = await llm_task    # suspends, lets db_task run
    db_result = await db_task
```

asyncio runs everything on **one thread**. When a coroutine hits `await` (an I/O wait), it **yields control** back to the event loop, which runs other coroutines. No threads, no locks, and no OS-level context switching. asyncio does switch between coroutines at `await` points, but that is a Python-level cooperative switch — no kernel involvement and orders of magnitude cheaper than preemptive OS thread scheduling.

#### The Key Insight

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

### 2. Coroutines — The Building Block

#### Defining Coroutines

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

#### What `await` Actually Does

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

#### Coroutines Are Not Magic — They're Generators Under the Hood

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

#### Awaitable Objects

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

### 3. The Event Loop — How It All Runs

#### The Event Loop Is the Scheduler

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

#### Starting the Event Loop

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

#### Getting the Running Loop

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

#### One Loop Per Thread — The Rule

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

### 4. Tasks — Concurrent Execution

#### Sequential vs Concurrent — Timeline

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

#### The Difference Between `await` and `create_task`

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

#### Task Naming (For Debugging)

```python
task = asyncio.create_task(
    slow_operation("fetch_llm", 2.0),
    name="llm-call-1"  # shows up in debugging/logging
)
print(task.get_name())  # "llm-call-1"
```

#### Task Callbacks

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

#### Fire and Forget (Background Tasks)

```python
# Sometimes you want to start a task and not await it
async def log_event(event: dict):
    await db.insert(event)

# ✅ CORRECT: keep a reference to prevent GC and silent exception loss
background_tasks = set()

async def handle_request(query: str):
    task = asyncio.create_task(log_event({"query": query}))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)  # drop ref when done

# ❌ WRONG: task is created but the reference is immediately dropped
async def handle_request_bad(query: str):
    asyncio.create_task(log_event({"query": query}))
    # If the task raises, the exception is silently lost.
    # Python 3.12+ warns about this at runtime.
```

---

### 5. Gathering and Waiting

#### `asyncio.gather` — Run Multiple Coroutines Concurrently

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

#### `gather` with Error Handling

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

#### `asyncio.wait` — More Control Over Completion

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

#### `asyncio.as_completed` — Process Results As They Arrive

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

### 6. TaskGroup — Structured Concurrency (Python 3.11+)

TaskGroup is the modern replacement for `gather`. It guarantees that all tasks are cleaned up, even on failure.

#### Basic Usage

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

#### Error Handling with TaskGroup

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

#### Why TaskGroup > gather

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

### 7. AsyncGenerator and `async for`

This is the **most important section for ADK**. ADK streams events through async generators.

#### Sync Generator Recap

```python
# Sync generator: function that yields values lazily
def count_up(n: int):
    for i in range(n):
        yield i         # pauses here, resumes on next()

for num in count_up(5):
    print(num)  # 0, 1, 2, 3, 4
```

#### Async Generator — yield + await

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

#### The ADK Pattern — Streaming Events

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

#### Composing Async Generators (Sequential Agents)

```python
# Python does NOT support `async yield from` — you must loop manually.
# The reason is deeper than syntax: an async generator can only yield
# from its own body. There is no way to "delegate" to a sub-generator
# and interleave its yields with the outer generator's execution.
# `yield from` (sync) works because the sub-generator steps are cheap
# and synchronous. Async generators need to await between steps, so
# the language requires you to make each await explicit.

# ❌ WRONG — SyntaxError: `async yield from` is not valid Python
async def sequential_agents(agents, query):
    for agent in agents:
        async yield from agent.run(query)  # SyntaxError!

# ✅ RIGHT — explicit async for loop: consume each sub-generator fully
# before moving to the next one (true sequential execution)
async def sequential_agents(agents, query) -> AsyncGenerator[Event, None]:
    for agent in agents:
        async for event in agent.run(query):
            yield event
```

#### Composing Async Generators (Parallel Agents)

```python
import asyncio
from typing import AsyncGenerator

async def parallel_agents(agents, query) -> AsyncGenerator[Event, None]:
    """Run agents in parallel, collect events, then yield.

    LIMITATION — streaming is lost:
    Because `yield` cannot appear inside `async with TaskGroup()` (SyntaxError),
    all events are buffered in a queue and only released after ALL agents finish.
    The consumer sees nothing until the slowest agent completes.

    If true streaming is required (events flow out as they arrive), use a
    different coordination approach — e.g., have consumers await on the queue
    directly while the tasks run, or use asyncio.Queue with an explicit
    "all done" counter instead of TaskGroup.
    """
    queue: asyncio.Queue[Event | None] = asyncio.Queue()

    async def run_and_enqueue(agent):
        async for event in agent.run(query):
            await queue.put(event)
        await queue.put(None)  # sentinel: this agent is done

    # Start all agents concurrently.
    # NOTE: yield cannot appear inside `async with TaskGroup()` — SyntaxError.
    # Events accumulate in the queue; consumer sees them only after all agents finish.
    async with asyncio.TaskGroup() as tg:
        for agent in agents:
            tg.create_task(run_and_enqueue(agent))

    # Yield buffered events after TaskGroup exits (all tasks done)
    while not queue.empty():
        event = queue.get_nowait()
        if event is not None:
            yield event
```

#### Async Generator Cleanup

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

#### Async Comprehensions

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

### 8. Async Context Managers (`async with`)

#### The Protocol

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

#### Using `contextlib.asynccontextmanager`

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

#### Nested Async Context Managers

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

#### ADK Example: MCP Toolset Connection

```python
# PSEUDOCODE — import path not verified against ADK source.
# ADK's McpToolset is a BaseToolset passed directly to an agent.
# (MCPToolset is deprecated; use McpToolset instead)
# Verify the exact import path in google/adk-python before using.
from google.adk.tools import McpToolset  # verify this import

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


> **Continued in [python-asyncio-advanced.md](python-asyncio-advanced.md)** — synchronization primitives, queues, error handling, timeouts, cancellation, mixing sync/async, streams, debugging, performance patterns, and ADK-specific async patterns.
