# 20b — Debugging Guide: Checklist & Performance Optimization

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** ADK source code | **Prereqs:** [20-best-practices.md](20-best-practices.md)

*This file continues from [20-best-practices.md](20-best-practices.md), which covers anti-patterns and rules.*

---

## Debugging Checklist

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

## Common Debugging Scenarios

### Agent Ignores My Tools

```
Possible causes:
│
├── output_schema is set → removes all tool declarations
│   Fix: Remove output_schema, use output_key instead
│
├── Tool docstrings are unclear → LLM doesn't understand when to use
│   Fix: Write specific, action-oriented docstrings
│
├── Too many tools (20+) → LLM confused, picks wrong one
│   Fix: Split into focused sub-agents
│
└── Tool name is ambiguous → LLM confuses similar tools
    Fix: Use specific names (search_products vs get_order_status)
```

### Agent Transfer Not Working

```
Possible causes:
│
├── Sub-agent has no description → LLM doesn't know when to transfer
│   Fix: Add specific description field
│
├── disallow_transfer_to_parent = True → agent can't return
│   Fix: Set to False (default)
│
├── disallow_transfer_to_peers = True → agent can't transfer sideways
│   Fix: Set to False (default)
│
├── Sub-agent names are duplicated → transfer is ambiguous
│   Fix: Use unique names for all siblings
│
└── No sub_agents defined → no transfer_to_agent tool injected
    Fix: Add sub_agents to the parent agent
```

### State Not Persisting

```
Possible causes:
│
├── Using temp: prefix → state only lives for current request
│   Fix: Remove "temp:" prefix for persistent state
│
├── Value not JSON-serializable → crashes on session save
│   Fix: Convert to dict/list/str/int/float/bool
│
├── Wrong prefix for reading → session "name" vs user: "user:name"
│   Fix: Always read with the same prefix used when writing
│
└── Using InMemorySessionService → data lost on restart
    Fix: Use DatabaseSessionService for production
```

### Infinite Tool-Call Loops

```
Possible causes:
│
├── Tool returns error → LLM retries indefinitely
│   Fix: Set RunConfig(max_llm_calls=20)
│
├── Tool returns success but LLM misinterprets → keeps calling
│   Fix: Return clear, unambiguous success messages
│
├── Instruction tells LLM to "always" use a tool → loops
│   Fix: Use conditional language ("if needed", "when relevant")
│
└── Model hallucinating nonexistent tools → error → retry
    Fix: Check tool names match exactly
```

---

## Performance Checklist

- Use model inheritance — don't repeat model on every agent
- Use `gemini-2.5-flash` for routing agents (fast, cheap); `gemini-2.5-pro` only where deep reasoning is needed
- Set `max_llm_calls` in `RunConfig` to prevent infinite loops: `RunConfig(max_llm_calls=20)`
- Use `include_contents='none'` for agents that don't need conversation history
- Enable event compaction for long conversations: `App(events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=1))`
- Use `ParallelAgent` when sub-tasks are independent
- Use `output_key` to pass data between agents via state (cheaper than re-processing in context)
- Keep instructions concise — every token costs money and time

For detailed latency analysis and model selection guidance, see below.

---

## Latency Optimization

### Reduce LLM Calls

```
Common causes of unnecessary LLM calls:
│
├── Deep agent hierarchy (each level = 1+ LLM calls for routing)
│   Fix: Flatten to 2-3 levels max
│
├── God agent with too many tools (LLM confused, retries)
│   Fix: Split into focused agents with 3-5 tools each
│
├── Missing max_llm_calls limit (infinite tool-call loops)
│   Fix: RunConfig(max_llm_calls=20)
│
├── Full conversation history on every turn (large context)
│   Fix: include_contents='none' where possible
│
└── No event compaction (context grows unbounded)
    Fix: EventsCompactionConfig(compaction_interval=5)
```

### Model Selection Strategy

```
Model selection for latency:
│
├── Routing agents
│   Use: gemini-2.5-flash (fastest, cheapest)
│   These agents just pick which sub-agent to use
│
├── Data extraction / parsing
│   Use: gemini-2.5-flash
│   Structured extraction doesn't need deep reasoning
│
├── Complex reasoning / analysis
│   Use: gemini-2.5-pro
│   Only where quality justifies the latency cost
│
└── Simple classification / confirmation
    Use: gemini-2.5-flash
    Binary decisions don't need a large model
```

### Parallel Execution

```
Opportunities for parallelism:
│
├── Independent sub-tasks → ParallelAgent
│   Example: search web + query DB + check cache simultaneously
│
├── Multiple tool calls in one turn → Automatic
│   ADK runs concurrent function calls via asyncio.gather
│   No configuration needed
│
└── Async I/O in tools → aiohttp / httpx
    Never use blocking requests.get() in tools
```

---

## Testing Agents

For `MockModel`, `InMemoryRunner`, deterministic testing patterns, and complete examples, see [22-testing.md](22-testing.md) and [22c-testing-examples.md](22c-testing-examples.md).

---

## Related

- [20-best-practices.md](20-best-practices.md) — Anti-patterns and rules
- [22-testing.md](22-testing.md) — MockModel, deterministic testing
- [23-advanced-internals.md](23-advanced-internals.md) — Advanced patterns and internals
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request
