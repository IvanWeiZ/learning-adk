# 20 — Best Practices: Anti-Patterns & Rules

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** ADK source code (agents, tools, sessions, runners modules) | **Prereqs:** [00-onboarding-guide.md](00-onboarding-guide.md)

## At a Glance

Full debugging checklist: see [debugging-guide.md](debugging-guide.md).

This document collects the most common ADK mistakes, anti-patterns, and rules. Each section covers one category of error with wrong/correct examples and the reasoning behind the rule.

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

# CORRECT: Use underscores
agent = Agent(name="my_agent", ...)
```

### 2. Tool Design — Return Errors, Never Raise Exceptions

```python
# WRONG: Raising exceptions
def search_database(query: str) -> str:
    results = db.search(query)
    if not results:
        raise ValueError("No results found") # LLM sees raw stack trace!
    return str(results)

# CORRECT: Return error dict
def search_database(query: str) -> str:
    try:
        results = db.search(query)
        if not results:
            return "No results found for your query. Try different search terms."
        return str(results)
    except ConnectionError:
        return "Database is temporarily unavailable. Please try again."
```

### 3. Tool Docstrings — The LLM's Only Documentation

```python
# WRONG: No docstring
def process(data: str) -> str:
    return api.call(data)

# CORRECT: Clear, action-oriented
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

### 4. The `output_schema` Trap — It Disables All Tools

```python
# WRONG: output_schema + tools — tools are silently ignored!
agent = Agent(
    name="analyzer",
    output_schema=Analysis,
    tools=[search_knowledge], # IGNORED!
)

# CORRECT: Use output_schema WITHOUT tools
analyzer = Agent(name="analyzer", output_schema=Analysis)

# CORRECT: Or use tools WITHOUT output_schema
researcher = Agent(name="researcher", tools=[search_knowledge])
```

### 5. Agent Reuse — One Parent Only

```python
# WRONG: Same instance in two parents
shared_helper = Agent(name="helper", instruction="Help with tasks")
parent_a = Agent(name="parent_a", sub_agents=[shared_helper])
parent_b = Agent(name="parent_b", sub_agents=[shared_helper]) # CRASHES

# CORRECT: Use clone()
template = Agent(name="helper", instruction="Help with tasks")
parent_a = Agent(name="parent_a", sub_agents=[template.clone(update={"name": "helper_a"})])
parent_b = Agent(name="parent_b", sub_agents=[template.clone(update={"name": "helper_b"})])
```

### 6. Callback Parameter Naming — Must Be Exact

```
Callback parameter names (must be exact):
│
├── before_agent_callback
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

```python
# WRONG: tools in both places
agent = Agent(
    tools=[search],
    generate_content_config=types.GenerateContentConfig(
        tools=[search], # CRASHES
    ),
)

# CORRECT: Only use generate_content_config for LLM-specific settings
agent = Agent(
    instruction="Be helpful",
    tools=[search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7, max_output_tokens=2048,
    ),
)
```

### 8. State Management — Avoid These Traps

```python
# CONFUSING: Reading without prefix
name = tool_context.state.get("name") # Gets session-scoped, NOT "user:name"!

# CORRECT: Always include the full key with prefix
name = tool_context.state.get("user:name")

# WRONG: Storing Python objects
tool_context.state["db_connection"] = get_db_connection() # Not JSON-serializable!

# CORRECT: Store only JSON-serializable values
tool_context.state["timestamp"] = datetime.now().isoformat()

# RISKY: Two parallel agents writing the same state key
agent_a = Agent(name="a", output_key="result") # Race condition!
agent_b = Agent(name="b", output_key="result")

# CORRECT: Different keys for each parallel agent
agent_a = Agent(name="a", output_key="result_a")
agent_b = Agent(name="b", output_key="result_b")
```

### 9. Model Inheritance — Don't Over-Specify

```python
# WASTEFUL: Setting the same model on every agent
root = Agent(name="root", model="gemini-2.5-flash", sub_agents=[
    Agent(name="child_a", model="gemini-2.5-flash"), # Redundant
])

# CORRECT: Set once on root, children inherit
root = Agent(name="root", model="gemini-2.5-flash", sub_agents=[
    Agent(name="child_a"), # Inherits gemini-2.5-flash
    Agent(name="smart_child", model="gemini-2.5-pro"), # Override only when different
])
```

### 10. Instruction Design — Dynamic vs Static

```python
# ADK supports {state_key} placeholders in instructions
agent = Agent(
    name="support",
    instruction="You are a support agent for {user:company_name}.",
)

# For complex logic, use a callable
async def build_instruction(ctx) -> str:
    if ctx.state.get("user:is_premium"):
        return "You are a premium support agent."
    return "You are a standard support agent."

agent = Agent(name="support", instruction=build_instruction)
```

### 11. Session Backend Selection

```
┌───────────────────────────────────────────────────────────────────────┐
│ Which Session Backend to Use?                                        │
│                                                                       │
│ ├── Local dev / tests → InMemorySessionService                       │
│ ├── Single-server → SqliteSessionService                              │
│ ├── Production / multi-server → DatabaseSessionService (PostgreSQL)   │
│ └── Google Cloud → VertexAiSessionService                             │
└───────────────────────────────────────────────────────────────────────┘
```

### 12. Async Best Practices

```python
# WRONG: Blocking I/O in a tool
import requests
def fetch_data(url: str) -> str:
    response = requests.get(url) # BLOCKS the entire event loop!
    return response.text

# CORRECT: Use async HTTP
import aiohttp
async def fetch_data(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

### 13. Description Field — Critical for Agent Transfer

```python
# WRONG: Vague descriptions
sub_agents=[Agent(name="agent_a", description="Handles stuff")]

# CORRECT: Specific, action-oriented descriptions
sub_agents=[Agent(
    name="billing_agent",
    description="Handles billing inquiries: invoices, payment methods, refunds",
)]
```

### 14. Common Architecture Anti-Patterns

**Anti-Pattern 1: God Agent** — One agent with 20 tools and a 2000-word instruction. Split into focused agents with 3-5 tools each.

**Anti-Pattern 2: Deep Nesting** — 5+ levels of agent hierarchy means 5+ LLM calls just for routing. Keep hierarchy shallow (2-3 levels max).

**Anti-Pattern 3: Global Mutable State** — Using global variables to share state between tools is a race condition. Use `tool_context.state` instead.

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

---

## Gotchas

- **`output_schema` silently disables all tools.** No warning.
- **Duplicate sub-agent names are not an error.** ADK only logs a warning, but agent transfer becomes unpredictable.
- **Callback parameter names must be exact.** ADK injects by parameter name, not position.
- **`generate_content_config` crashes on duplicates.** Hard crash, not a warning.
- **`temp:` state disappears between requests.** Only in memory for the current invocation.
- **Each agent instance can only have one parent.** Use `.clone()` instead.
- **Blocking I/O in tools blocks the entire event loop.** Use `async` HTTP clients or `asyncio.to_thread`.
- **Global mutable state shared across tool functions is a race condition.** Use `tool_context.state`.

*Continued in [debugging-guide.md](debugging-guide.md) — debugging checklist, latency optimization, and performance tips.*

---

## Related

- [debugging-guide.md](debugging-guide.md) — Debugging checklist and performance optimization
- [00-onboarding-guide.md](00-onboarding-guide.md) — Start here if you're new
- [23-advanced-internals.md](23-advanced-internals.md) — Advanced patterns and internals
- [04-agents.md](04-agents.md) — Agent types deep dive
- [09-tools.md](09-tools.md) — Tool system reference
- [08-sessions.md](08-sessions.md) — Session state details
- [02-when-to-build-what.md](02-when-to-build-what.md) — Decision guide
