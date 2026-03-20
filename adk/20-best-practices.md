# 20 — Best Practices: Anti-Patterns & Rules

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** ADK source code (agents, tools, sessions, runners modules) | **Prereqs:** [00-onboarding-guide.md](00-onboarding-guide.md)

## At a Glance

Full debugging checklist: see [Debugging Checklist](#debugging-checklist) below.

This document collects the most common ADK mistakes, anti-patterns, and rules. Each section covers one category of error with wrong/correct examples and the reasoning behind the rule. Use the debugging checklist above as a first-pass diagnostic when things go wrong.

---

## How It Works

### 1. Agent Naming — The #1 Source of Startup Crashes

**The Rules**

```
Agent name must be:
├── A valid Python identifier (letters, digits, underscores)
├── NOT "user" (reserved by ADK for end-user input)
└── Unique among siblings (duplicate names log warnings but cause bugs)
```

**Common Mistakes**

```python
# WRONG: Hyphens are not valid Python identifiers
agent = Agent(name="my-agent", ...)
# → ValueError: Agent name must be a valid identifier

# WRONG: "user" is reserved
agent = Agent(name="user", ...)
# → ValueError: Agent name cannot be `user`

# WRONG: Spaces
agent = Agent(name="my agent", ...)
# → ValueError

# CORRECT: Use underscores
agent = Agent(name="my_agent", ...)

# CORRECT: CamelCase also works (it's a valid identifier)
agent = Agent(name="MyAgent", ...)
```

**Duplicate Sub-Agent Names (Silent Bug)**

```python
# WRONG: Both children named "helper" — transfer_to_agent will be ambiguous
root = Agent(
    name="root",
    sub_agents=[
        Agent(name="helper", instruction="Help with math"),
        Agent(name="helper", instruction="Help with code"), # Duplicate!
    ],
)
# ADK only logs a warning, but agent transfer becomes unpredictable.

# CORRECT: Unique names
root = Agent(
    name="root",
    sub_agents=[
        Agent(name="math_helper", instruction="Help with math"),
        Agent(name="code_helper", instruction="Help with code"),
    ],
)
```

### 2. Tool Design — Return Errors, Never Raise Exceptions

**The Pattern**

```
Tool return value:
├── Success → return any JSON-serializable value
├── Error → return {"error": "human-readable message"}
└── Never → raise Exception ← LLM sees a stack trace, gets confused
```

```python
# WRONG: Raising exceptions
def search_database(query: str) -> str:
    """Search the database."""
    results = db.search(query)
    if not results:
        raise ValueError("No results found") # LLM sees raw stack trace!
    return str(results)

# CORRECT: Return error dict
def search_database(query: str) -> str:
    """Search the database."""
    try:
        results = db.search(query)
        if not results:
            return "No results found for your query. Try different search terms."
        return str(results)
    except ConnectionError:
        return "Database is temporarily unavailable. Please try again."
    except Exception as e:
        return f"Search failed: {e}"
```

**Why This Matters**

```
When a tool raises an exception:
┌──────────────────────────────────────────────────┐
│ LLM sees:                                        │
│ "Error: Traceback (most recent call last):       │
│   File '/app/tools.py', line 42, in search_db    │
│     raise ValueError('No results found')         │
│ ValueError: No results found"                    │
│                                                  │
│ LLM reaction: confused, may retry forever,       │
│ or generate apology with stack trace details     │
└──────────────────────────────────────────────────┘

When a tool returns an error string:
┌──────────────────────────────────────────────────┐
│ LLM sees:                                        │
│ "No results found for your query.                │
│  Try different search terms."                    │
│                                                  │
│ LLM reaction: rephrases query or tells user      │
│ there are no results in a natural way            │
└──────────────────────────────────────────────────┘
```

### 3. Tool Docstrings — The LLM's Only Documentation

The LLM chooses tools by function name and docstring. Poor docstrings = wrong tool calls.

```python
# WRONG: No docstring — LLM has no idea what this does
def process(data: str) -> str:
    return api.call(data)

# WRONG: Too vague
def search(query: str) -> str:
    """Search for stuff."""
    return api.search(query)

# WRONG: Implementation details the LLM doesn't need
def search_products(query: str) -> str:
    """Uses Elasticsearch with BM25 scoring to query the products index.
    Connects to cluster at es.internal:9200 with retry logic."""
    return es.search(query)

# CORRECT: Clear, action-oriented, describes inputs and outputs
def search_products(query: str, category: str = "all") -> str:
    """Search for products by name or description.

    Args:
        query: What to search for (e.g., "wireless headphones")
        category: Product category to filter by. Options: "electronics",
            "clothing", "books", "all"

    Returns:
        A list of matching products with name, price, and rating.
    """
    return catalog.search(query, category)
```

**Naming Matters Too**

```python
# Ambiguous names — LLM confuses these
tools=[get_data, fetch_info, retrieve_results]

# Clear, specific names — LLM picks the right one
tools=[search_products, get_order_status, check_inventory]
```

### 4. The `output_schema` Trap — It Disables All Tools

```python
from pydantic import BaseModel

class Analysis(BaseModel):
    sentiment: str
    confidence: float
    topics: list[str]

# WRONG: output_schema + tools — tools are silently ignored!
agent = Agent(
    name="analyzer",
    model="gemini-2.5-flash",
    instruction="Analyze user messages using the search tool.",
    output_schema=Analysis, # ← Forces structured output
    tools=[search_knowledge], # ← These are IGNORED!
)

# CORRECT: Use output_schema WITHOUT tools (for pure analysis)
analyzer = Agent(
    name="analyzer",
    output_schema=Analysis,
    instruction="Analyze the sentiment, confidence, and topics of the message.",
    # No tools — this agent only produces structured output
)

# CORRECT: Or use tools WITHOUT output_schema
researcher = Agent(
    name="researcher",
    tools=[search_knowledge],
    instruction="Search knowledge base and provide analysis.",
    # No output_schema — agent uses tools freely and responds in text
)
```

**When to use `output_schema`:**

```
Do you need the agent to call tools?
├── Yes → Do NOT use output_schema
│         Use output_key to save text output to state instead
│
└── No → output_schema is perfect
         Use when agent does pure reasoning/classification
```

**Why they are incompatible:**

```
output_schema set on agent
├── ADK sets response_mime_type = "application/json"
├── ADK sets response_schema = <your Pydantic model>
├── ADK removes all tool/function declarations from the LLM request
│   └── Reason: Gemini cannot produce both structured JSON output
│       and function calls in the same response
└── Result: tools=[...] is silently ignored — no error, no warning

Workaround for structured output WITH tools:
├── Step 1: Use agent with tools (no output_schema) to gather data
├── Step 2: Use a second agent with output_schema (no tools) to format
└── Wire them with SequentialAgent or output_key
```

### 5. Agent Reuse — One Parent Only

Each agent instance belongs to one parent (enforced at runtime):

```python
# WRONG: Same instance in two parents
shared_helper = Agent(name="helper", instruction="Help with tasks")

parent_a = Agent(
    name="parent_a",
    sub_agents=[shared_helper], # Sets shared_helper.parent_agent = parent_a
)

parent_b = Agent(
    name="parent_b",
    sub_agents=[shared_helper], # CRASHES: "Agent 'helper' already has a parent"
)

# CORRECT: Create separate instances
parent_a = Agent(
    name="parent_a",
    sub_agents=[Agent(name="helper_a", instruction="Help with tasks")],
)

parent_b = Agent(
    name="parent_b",
    sub_agents=[Agent(name="helper_b", instruction="Help with tasks")],
)

# ALSO CORRECT: Use clone()
template = Agent(name="helper", instruction="Help with tasks")

parent_a = Agent(
    name="parent_a",
    sub_agents=[template.clone(update={"name": "helper_a"})],
)

parent_b = Agent(
    name="parent_b",
    sub_agents=[template.clone(update={"name": "helper_b"})],
)
```

### 6. Callback Parameter Naming — Must Be Exact

ADK injects by parameter name. Wrong names = broken callbacks.

```python
# WRONG: Parameter named "ctx" instead of "callback_context"
async def my_before_agent(ctx):
    print("Before agent")
    return None

# WRONG: Parameter named "request" instead of "llm_request"
async def my_before_model(callback_context, request):
    print("Before model")
    return None

# CORRECT: Exact parameter names
async def my_before_agent(callback_context):
    print(f"Agent: {callback_context.agent_name}")
    return None

async def my_before_model(callback_context, llm_request):
    print(f"Sending {len(llm_request.contents)} messages")
    return None

async def my_before_tool(tool, args, tool_context):
    print(f"Calling tool: {tool.name} with {args}")
    return None

async def my_after_tool(tool, args, tool_context, tool_response):
    print(f"Tool {tool.name} returned: {tool_response}")
    return None
```

**Parameter name cheat sheet:**

```
Callback parameter names (must be exact):
│
├── before_agent_callback
│      callback_context
│
├── after_agent_callback
│      callback_context
│
├── before_model_callback
│      callback_context, llm_request
│
├── after_model_callback
│      callback_context, llm_response
│
├── before_tool_callback
│      tool, args, tool_context
│
└── after_tool_callback
       tool, args, tool_context, tool_response
```

### 7. generate_content_config — Don't Duplicate Agent Fields

ADK rejects duplicated config:

```python
from google.genai import types

# WRONG: tools in both places
agent = Agent(
    name="my_agent",
    tools=[search],
    generate_content_config=types.GenerateContentConfig(
        tools=[search], # CRASHES: "All tools must be set via LlmAgent.tools"
    ),
)

# WRONG: system_instruction in both places
agent = Agent(
    name="my_agent",
    instruction="Be helpful",
    generate_content_config=types.GenerateContentConfig(
        system_instruction="Be helpful", # CRASHES: "must be set via LlmAgent.instruction"
    ),
)

# WRONG: response_schema in both places
agent = Agent(
    name="my_agent",
    output_schema=MyModel,
    generate_content_config=types.GenerateContentConfig(
        response_schema=MyModel, # CRASHES: "must be set via LlmAgent.output_schema"
    ),
)

# CORRECT: Only use generate_content_config for LLM-specific settings
agent = Agent(
    name="my_agent",
    instruction="Be helpful",
    tools=[search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7, # ← These are fine here
        max_output_tokens=2048, # ← These are fine here
        top_p=0.9, # ← These are fine here
    ),
)
```

### 8. State Management — Avoid These Traps

**Trap 1: Forgetting State Prefix Behavior**

```python
# CONFUSING: Reading "user:name" without the prefix
name = tool_context.state.get("name") # Gets session-scoped "name", NOT "user:name"!

# CORRECT: Always include the full key with prefix
name = tool_context.state.get("user:name") # Gets user-scoped name
```

**Trap 2: Storing Non-Serializable Objects**

```python
# WRONG: Storing Python objects — will crash on session persistence
tool_context.state["db_connection"] = get_db_connection() # Not JSON-serializable!
tool_context.state["timestamp"] = datetime.now() # datetime isn't JSON-safe

# CORRECT: Store only JSON-serializable values
tool_context.state["db_host"] = "db.example.com"
tool_context.state["timestamp"] = datetime.now().isoformat()
tool_context.state["results"] = [{"id": 1, "name": "Alice"}]
```

**Trap 3: temp: State Disappearing**

```python
# temp: state is ONLY in memory — never persisted between requests

# Request 1:
tool_context.state["temp:auth_token"] = "abc123" # Set in memory

# Request 2 (new invocation):
token = tool_context.state.get("temp:auth_token") # → None! It's gone.

# Use temp: for cache/scratch data only. For persistent data, use session or user scope.
```

**Trap 4: State in Parallel Agents**

```python
# RISKY: Two parallel agents writing the same state key
agent_a = Agent(name="a", output_key="result") # Writes state["result"]
agent_b = Agent(name="b", output_key="result") # Also writes state["result"]!

parallel = ParallelAgent(
    name="parallel",
    sub_agents=[agent_a, agent_b], # Race condition: who wins?
)

# CORRECT: Different keys for each parallel agent
agent_a = Agent(name="a", output_key="result_a")
agent_b = Agent(name="b", output_key="result_b")
```

### 9. Model Inheritance — Don't Over-Specify

```
Model resolution order:
┌─────────────────────────────────────────────┐
│ 1. Agent's own model field (if set)         │
│ 2. Nearest ancestor LlmAgent's model       │
│ 3. LlmAgent class default                  │
│    (gemini-2.5-flash by default)            │
└─────────────────────────────────────────────┘
```

```python
# WASTEFUL: Setting the same model on every agent
root = Agent(name="root", model="gemini-2.5-flash", sub_agents=[
    Agent(name="child_a", model="gemini-2.5-flash", ...), # Redundant
    Agent(name="child_b", model="gemini-2.5-flash", ...), # Redundant
])

# CORRECT: Set once on root, children inherit
root = Agent(name="root", model="gemini-2.5-flash", sub_agents=[
    Agent(name="child_a", ...), # Inherits gemini-2.5-flash
    Agent(name="child_b", ...), # Inherits gemini-2.5-flash
])

# CORRECT: Override only when different
root = Agent(name="root", model="gemini-2.5-flash", sub_agents=[
    Agent(name="fast_child", ...), # Inherits flash
    Agent(name="smart_child", model="gemini-2.5-pro", ...), # Override to pro
])
```

### 10. Instruction Design — Dynamic vs Static

**Dynamic Instructions with Placeholders**

```python
# ADK supports {state_key} placeholders in instructions
agent = Agent(
    name="support",
    instruction="""You are a support agent for {user:company_name}.
    The customer's plan is: {user:plan_type}.
    Previous issue count: {user:issue_count}.""",
)
# At runtime, ADK replaces {user:company_name} with state["user:company_name"]
```

**Dynamic Instructions with Functions**

```python
# For complex logic, use a callable
async def build_instruction(ctx) -> str:
    """Build instruction based on runtime context."""
    if ctx.state.get("user:is_premium"):
        return "You are a premium support agent. Prioritize this customer."
    return "You are a standard support agent."

agent = Agent(
    name="support",
    instruction=build_instruction, # Called at each invocation
)
```

**Common Instruction Mistakes**

```python
# WRONG: Telling the agent about tools it doesn't have
agent = Agent(
    name="helper",
    instruction="Use the search_web tool to find information.",
    tools=[], # No tools! LLM will hallucinate tool calls.
)

# WRONG: Contradicting transfer configuration
agent = Agent(
    name="helper",
    instruction="Transfer complex issues to the escalation_agent.",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    sub_agents=[], # No sub-agents + both transfers blocked = can't transfer anywhere!
)

# CORRECT: Instruction matches actual capabilities
agent = Agent(
    name="helper",
    instruction="You help with simple questions. For complex issues, transfer to escalation_agent.",
    sub_agents=[escalation_agent],
)
```

### 11. Session Backend Selection

```
┌───────────────────────────────────────────────────────────────────────┐
│ Which Session Backend to Use?                                        │
│                                                                       │
│ Environment?                                                          │
│ │                                                                     │
│ ├── Local dev / tests                                                 │
│ │   └── InMemorySessionService                                       │
│ │       Pros: Zero setup, fast                                        │
│ │       Cons: Lost on restart, single process only                    │
│ │                                                                     │
│ ├── Single-server deployment                                          │
│ │   └── SqliteSessionService                                          │
│ │       Pros: Persistent, no external DB needed                       │
│ │       Cons: Single-writer, not for horizontal scaling               │
│ │                                                                     │
│ ├── Production / multi-server                                         │
│ │   └── DatabaseSessionService (PostgreSQL / MySQL)                   │
│ │       Pros: Scalable, row-level locking, multi-process safe         │
│ │       Cons: Requires DB infrastructure                              │
│ │                                                                     │
│ └── Google Cloud                                                      │
│     └── VertexAiSessionService                                        │
│         Pros: Managed, integrates with Vertex AI Agent Engine         │
│         Cons: GCP-only                                                │
└───────────────────────────────────────────────────────────────────────┘
```

### 12. Testing Agents — Use Real Components, Mock External APIs

```python
import pytest
from google.adk import Agent
from google.adk.runners import InMemoryRunner

# CORRECT: Test with real ADK components, mock only external services
@pytest.mark.asyncio
async def test_weather_agent():
    def mock_weather(city: str) -> str:
        """Get weather for a city."""
        return f"Sunny, 25 degrees C in {city}"

    agent = Agent(
        model="gemini-2.5-flash",
        name="weather_bot",
        instruction="Help users check weather.",
        tools=[mock_weather], # Real FunctionTool with mock implementation
    )

    runner = InMemoryRunner(agent=agent)
    events = []
    # Note: run_async_with_new_session_agen is a method on TestInMemoryRunner
    # (from tests/unittests/testing_utils.py), not the public InMemoryRunner.
    async for event in runner.run_async_with_new_session_agen(
        types.Content(role="user", parts=[types.Part(text="Weather in Tokyo?")])
    ):
        events.append(event)

    # Verify agent called the tool and responded
    assert any(
        event.content and "Tokyo" in str(event.content)
        for event in events
    )

# WRONG: Mocking ADK internals — brittle and misses real bugs
@pytest.mark.asyncio
async def test_weather_agent_bad():
    with mock.patch("google.adk.flows.BaseLlmFlow.run_async"):
        pass # Don't do this — you're testing your mocks, not your agent
```

### 13. Async Best Practices

**Never Block the Event Loop**

```python
# WRONG: Blocking I/O in a tool
import requests

def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    response = requests.get(url) # BLOCKS the entire event loop!
    return response.text

# CORRECT: Use async HTTP
import aiohttp

async def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# ALSO OK: Wrap blocking code with asyncio.to_thread
import asyncio
import requests

async def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    response = await asyncio.to_thread(requests.get, url)
    return response.text
```

**Sync Tools Are Fine — ADK Handles Them**

```python
# ADK auto-detects sync vs async and handles both correctly
def sync_tool(query: str) -> str:
    """A sync tool — ADK wraps this correctly."""
    return compute(query)

async def async_tool(query: str) -> str:
    """An async tool — ADK awaits this."""
    return await async_compute(query)

agent = Agent(
    tools=[sync_tool, async_tool], # Both work fine
)
```

### 14. Description Field — Critical for Agent Transfer

The LLM uses `description` to pick transfer targets. Bad descriptions = wrong routing:

```python
# WRONG: Vague descriptions
sub_agents=[
    Agent(name="agent_a", description="Handles stuff"),
    Agent(name="agent_b", description="Does things"),
]

# WRONG: No descriptions at all
sub_agents=[
    Agent(name="billing_agent"), # LLM only sees the name
    Agent(name="support_agent"), # Will guess based on name alone
]

# CORRECT: Specific, action-oriented descriptions
sub_agents=[
    Agent(
        name="billing_agent",
        description="Handles billing inquiries: invoices, payment methods, "
            "subscription changes, refunds, and pricing questions",
    ),
    Agent(
        name="technical_support",
        description="Handles technical issues: bugs, errors, configuration "
            "problems, API questions, and integration help",
    ),
]
```

### 15. Common Architecture Anti-Patterns

**Anti-Pattern 1: God Agent**

```
One agent with 20 tools and a 2000-word instruction

┌──────────────────────────────────────────┐
│              god_agent                   │
│  tools: [tool1, tool2, ... tool20]       │
│  instruction: (2000 words)               │
│                                          │
│  Problems:                               │
│  - LLM picks wrong tools                │
│  - Instruction too long, gets ignored    │
│  - Hard to test and maintain             │
└──────────────────────────────────────────┘

Split into focused agents with clear responsibilities

coordinator (routes)
├── Agent A
│      3-5 tools, focused instruction
│
├── Agent B
│      3-5 tools, focused instruction
│
└── Agent C
       3-5 tools, focused instruction
```

**Concrete before/after:**

```
BEFORE — God Agent:
  User: "What's the weather in Tokyo and book me a hotel"
  ┌─────────────────────────────────┐
  │          god_agent              │
  │  tools: [get_weather,          │
  │    book_hotel, search_flights,  │
  │    send_email, query_db,        │
  │    ... 15 more tools]           │
  └─────────────────────────────────┘
  Problem: LLM confused by 20 tool schemas → picks wrong tool → hallucinated args

AFTER — Focused Agents:
  User: "What's the weather in Tokyo and book me a hotel"
  ┌─────────────────────────────┐
  │       router_agent          │
  │  sub_agents:                │
  │  ┌───────────────────────┐  │
  │  │   weather_agent       │  │ ← 1 tool: get_weather
  │  │  tools: [get_weather] │  │
  │  └───────────────────────┘  │
  │  ┌───────────────────────┐  │
  │  │   hotel_agent         │  │ ← 2 tools: search_hotels, book_hotel
  │  │  tools: [search,      │  │
  │  │          book]         │  │
  │  └───────────────────────┘  │
  └─────────────────────────────┘
  Result: each agent sees only relevant tools → correct tool selection
```

**Anti-Pattern 2: Deep Nesting**

```
Too many layers — slow, hard to debug

root → coordinator → sub_coordinator → specialist → sub_specialist
(5 levels = 5 LLM calls just for routing!)

Keep hierarchy shallow (2-3 levels max)

root → specialist_a
     → specialist_b
     → specialist_c
```

**Anti-Pattern 3: Stateless Agents Sharing State Through Side Channels**

```python
# WRONG: Using global variables to share state between agents
global_data = {}

def tool_a(query: str) -> str:
    global_data["result"] = compute(query) # Side channel!
    return "Done"

def tool_b() -> str:
    return global_data.get("result", "No data") # Reads from side channel!

# CORRECT: Use session state — it's designed for this
def tool_a(query: str, tool_context: ToolContext) -> str:
    tool_context.state["result"] = compute(query)
    return "Done"

def tool_b(tool_context: ToolContext) -> str:
    return tool_context.state.get("result", "No data")
```

---

## Examples

### Summary: Top 10 Rules

| # | Rule | Why |
|---|------|-----|
| 1 | Agent names must be valid Python identifiers | ADK validates at construction |
| 2 | Return errors from tools, never raise exceptions | LLM handles strings, not stack traces |
| 3 | Write clear tool docstrings | It's the only thing the LLM reads |
| 4 | Don't use `output_schema` with tools | It silently disables all tools |
| 5 | Each agent instance belongs to one parent only | Use `.clone()` for reuse |
| 6 | Use exact callback parameter names | ADK uses names for injection |
| 7 | Don't duplicate config in `generate_content_config` | ADK validates and crashes |
| 8 | Store only JSON-serializable values in state | State is persisted to storage |
| 9 | Use specific `description` fields for sub-agents | LLM uses them for routing |
| 10 | Keep agent hierarchy shallow (2-3 levels) | Each level = more LLM calls |

### Performance Checklist

```
┌───────────────────────────────────────────────────────────────────┐
│ Performance Optimization                                         │
│                                                                   │
│ Use model inheritance — don't repeat model on every agent         │
│                                                                   │
│ Use gemini-2.5-flash for routing agents (fast, cheap)             │
│ Use gemini-2.5-pro only for agents that need deep reasoning       │
│                                                                   │
│ Set max_llm_calls in RunConfig to prevent infinite loops          │
│ runner.run_async(..., run_config=RunConfig(max_llm_calls=20))     │
│                                                                   │
│ Use include_contents='none' for agents that don't need history    │
│                                                                   │
│ Enable event compaction for long conversations                    │
│ App(events_compaction_config=EventsCompactionConfig(              │
│     compaction_interval=5, overlap_size=1                         │
│ ))                                                                │
│                                                                   │
│ Use ParallelAgent when sub-tasks are independent                  │
│                                                                   │
│ Use output_key to pass data between agents via state              │
│ (cheaper than re-processing in context)                           │
│                                                                   │
│ Keep instructions concise — every token costs money and time      │
└───────────────────────────────────────────────────────────────────┘
```

### Debugging Checklist

Check in order:

```
Agent not responding correctly?
│
├── 1. Check agent name validity (Python identifier, not "user")
│
├── 2. Check tool docstrings (are they clear enough for the LLM?)
│
├── 3. Check callback parameter names (must be exact)
│
├── 4. Check if output_schema is blocking tools
│
├── 5. Check state key prefixes (app:, user:, temp:, or none)
│
├── 6. Check generate_content_config for duplicated settings
│
├── 7. Enable tracing to see the full event stream:
│      async for event in runner.run_async(...):
│          print(f"[{event.author}] {event.content}")
│          print(f"  actions: {event.actions}")
│
├── 8. Check transfer configuration:
│      - Are sub_agents defined?
│      - Are descriptions clear?
│      - Is disallow_transfer_to_parent blocking returns?
│
└── 9. Check model availability:
       - Is the model string correct?
       - Are API credentials configured?
```

---

## Gotchas

- **`output_schema` silently disables all tools.** If you set both `output_schema` and `tools` on an agent, the tools are ignored without any warning.
- **Duplicate sub-agent names are not an error.** ADK only logs a warning, but agent transfer becomes unpredictable when two siblings share a name.
- **Callback parameter names must be exact.** ADK injects by parameter name, not position. Using `ctx` instead of `callback_context` will break your callback silently.
- **`generate_content_config` crashes on duplicates.** Setting `tools`, `system_instruction`, or `response_schema` in both the agent fields and `generate_content_config` causes a hard crash, not a warning.
- **`temp:` state disappears between requests.** It is only in memory for the current invocation. The next `run_async()` call will not see it.
- **Each agent instance can only have one parent.** Reusing the same agent object in two parent agents crashes at construction time. Use `.clone()` instead.
- **Blocking I/O in tools blocks the entire event loop.** Use `async` HTTP clients or wrap blocking calls with `asyncio.to_thread`.
- **Global mutable state shared across tool functions is a race condition.** Use `tool_context.state` instead.

---

## Related

- [00-onboarding-guide.md](00-onboarding-guide.md) — Start here if you're new
- [23-advanced-internals.md](23-advanced-internals.md) — Advanced patterns and internals
- [04-agents.md](04-agents.md) — Agent types deep dive
- [09-tools.md](09-tools.md) — Tool system reference
- [08-sessions.md](08-sessions.md) — Session state details
- [02-when-to-build-what.md](02-when-to-build-what.md) — Decision guide
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request
