# 24 — FAQ: Common Questions & Answers

> **Official docs:** [Quickstart](https://google.github.io/adk-docs/get-started/quickstart/) | **Source:** patterns across all ADK modules | **Prereqs:** [04-agents.md](04-agents.md), [08-sessions.md](08-sessions.md), [09-tools.md](09-tools.md)

## At a Glance

```
┌──────────────────────────────────────────────────────────────┐
│                    FAQ Topic Map                             │
│                                                              │
│  Q1  Tool Versioning ──► Named versions / Toolset / Callback │
│  Q2  Testing Strategy ──► Unit → Integration → E2E pyramid  │
│  Q3  Preprocessing ──► before_agent / Plugin / SequentialAgent│
│  Q4  Message Passing ──► State / Tool writes / Transfer / AgentTool│
│  Q5  State Scopes ──► session / user: / app: / temp:         │
│                                                              │
│  Each question maps a common scenario to concrete ADK code.  │
└──────────────────────────────────────────────────────────────┘
```

Five frequently asked questions that come up when building production ADK agents. Each answer provides multiple patterns with trade-off analysis so you can pick the right approach for your situation.

## Core Questions

### Q1: What Is the Best Way to Do Tool Versioning?

ADK has no built-in tool versioning. Three patterns:

#### Pattern A: Version in the Tool Name (Simplest)

Run versions side-by-side. The LLM picks based on description.

**Pros:** zero infrastructure, easy to understand, works immediately
**Cons:** LLM may ignore instructions and keep calling v1, pollutes tool namespace, no per-user control

```python
def search_products_v1(query: str) -> str:
    """Search products by name (basic text match).
    Use this for simple keyword searches."""
    return legacy_search(query)

def search_products_v2(query: str, category: str = "all", sort: str = "relevance") -> str:
    """Search products with filtering and sorting (recommended).
    Use this for all product searches — supports category filtering and sort order."""
    return advanced_search(query, category, sort)

agent = Agent(
    name="shop_assistant",
    tools=[search_products_v1, search_products_v2],
    instruction="Prefer search_products_v2 over v1 for all searches.",
)
```

```
Migration timeline:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ Phase 1: Both versions available                         │
│   tools=[search_v1, search_v2]                           │
│   instruction="Prefer v2"                                │
│   │                                                      │
│   ▼                                                      │
│ Phase 2: Monitor — is v1 still being called?             │
│   (Use before_tool_callback to log tool usage)           │
│   │                                                      │
│   ▼                                                      │
│ Phase 3: Remove old version                              │
│   tools=[search_v2] (rename to search_products)          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Pattern B: Toolset with Version Selection (Dynamic)

Use a `BaseToolset` to serve different versions based on context.

**Pros:** per-user rollout via feature flags, A/B testing, clean tool namespace (LLM sees one tool)
**Cons:** more code, requires feature flag infrastructure in session state, harder to debug which version ran

```python
from google.adk.tools import BaseToolset, FunctionTool

class VersionedToolset(BaseToolset):
    """Serves tool versions based on user's feature flags."""

    def __init__(self, tool_versions: dict):
        super().__init__()
        # {"search": {"v1": func_v1, "v2": func_v2, "default": "v2"}}
        self.tool_versions = tool_versions

    async def get_tools(self, readonly_context) -> list:
        feature_flags = readonly_context.state.get("user:feature_flags", {})
        tools = []

        for tool_name, versions in self.tool_versions.items():
            # Check if user has a specific version flag
            version = feature_flags.get(f"{tool_name}_version", versions["default"])
            func = versions.get(version, versions[versions["default"]])
            tools.append(FunctionTool(func=func))

        return tools

# Usage:
agent = Agent(
    name="shop",
    tools=[VersionedToolset(tool_versions={
        "search": {
            "v1": search_products_v1,
            "v2": search_products_v2,
            "default": "v2",
        },
    })],
)
```

```
How it works at runtime:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ User A (feature_flags: {search_version: "v1"})           │
│   │                                                      │
│   ▼                                                      │
│   VersionedToolset.get_tools()                           │
│   → returns [search_products_v1]                         │
│                                                          │
│ User B (feature_flags: {}) ← default                     │
│   │                                                      │
│   ▼                                                      │
│   VersionedToolset.get_tools()                           │
│   → returns [search_products_v2]                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Pattern C: Callback-Based Migration (Transparent)

Use `before_tool_callback` to silently redirect old tool calls to new implementations.

**Pros:** zero LLM retraining, existing prompts keep working, can transform args on the fly
**Cons:** hidden indirection (hard to debug), callback runs on every tool call, migration logic lives outside the tool

```python
async def version_migration_callback(tool, args, tool_context):
    """Redirect old tool calls to new implementations."""
    migrations = {
        "search_products": ("search_products_v2", lambda a: {**a, "sort": "relevance"}),
    }

    if tool.name in migrations:
        new_name, transform_args = migrations[tool.name]
        new_tool = find_tool(new_name)
        new_args = transform_args(args)
        # Execute new version, return its result (skips old tool)
        result = await new_tool.run_async(args=new_args, tool_context=tool_context)
        return result

    return None # No migration, run original

agent = Agent(
    name="shop",
    before_tool_callback=version_migration_callback,
)
```

#### Summary: When to Use Each Pattern

```
When to use each pattern:
│
├── A: Named versions
│      Best for: Simple migration, few tools
│
├── B: Toolset
│      Best for: Feature flags, A/B testing, per-user
│
└── C: Callback
       Best for: Transparent migration, no LLM retraining
```

---

### Q2: What Is the Best Way to Test Each ADK Component and E2E?

For MockModel, InMemoryRunner, deterministic test patterns, and complete test examples, see [22-testing.md](22-testing.md) and [22b-testing-examples.md](22b-testing-examples.md).

---

### Q3: What Is the Best Way to Preprocess User Requests (Extract IDs, Enrich Data)?

#### Pattern A: before_agent_callback (Recommended)

Intercept the request before the agent sees it, extract IDs, fetch additional data, and inject it into state:

**Pros:** runs before LLM (saves tokens), direct state access
**Cons:** per-agent only, not reusable

```python
import re
from google.adk import Agent

async def enrich_request(callback_context):
    """Extract IDs from user message and fetch additional data before the agent runs."""
    # Get the latest user message from session events
    session = callback_context.state._session # Access session
    last_user_msg = ""
    for event in reversed(session.events):
        if event.content and event.content.role == "user":
            for part in event.content.parts:
                if part.text:
                    last_user_msg = part.text
                    break
            break

    # Extract IDs using regex
    order_ids = re.findall(r'ORD-\d+', last_user_msg)
    customer_ids = re.findall(r'CUST-\d+', last_user_msg)

    # Fetch additional data for each ID
    if order_ids:
        order_data = await fetch_order_details(order_ids[0])
        callback_context.state["temp:order_context"] = order_data

    if customer_ids:
        customer_data = await fetch_customer_profile(customer_ids[0])
        callback_context.state["temp:customer_context"] = customer_data

    return None # Continue to agent (don't short-circuit)

root_agent = Agent(
    name="support",
    instruction="""You are a support agent.
    Check state key 'temp:order_context' for pre-loaded order data.
    Check state key 'temp:customer_context' for pre-loaded customer data.
    Use this data to assist the user without re-fetching.""",
    before_agent_callback=enrich_request,
    tools=[lookup_order, update_order],
)
```

```
Request flow with preprocessing:
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│ User: "Help with order ORD-123, I'm customer CUST-456"       │
│   │                                                          │
│   ▼                                                          │
│   ┌──────────────────────────────────────┐                   │
│   │ before_agent_callback                │                   │
│   │                                      │                   │
│   │ 1. Extract "ORD-123" from message    │                   │
│   │ 2. Extract "CUST-456" from message   │                   │
│   │ 3. Fetch order details from DB       │                   │
│   │ 4. Fetch customer profile from DB    │                   │
│   │ 5. Store in temp: state              │                   │
│   └──────────────────┬───────────────────┘                   │
│                      │                                       │
│                      ▼                                       │
│   ┌──────────────────────────────────────┐                   │
│   │ Agent runs with enriched context     │                   │
│   │                                      │                   │
│   │ state["temp:order_context"] =        │                   │
│   │   {status: "shipped", items: [...]}  │                   │
│   │                                      │                   │
│   │ state["temp:customer_context"] =     │                   │
│   │   {name: "Alice", tier: "premium"}   │                   │
│   │                                      │                   │
│   │ → Agent already knows the context    │                   │
│   │ → No need for extra tool calls       │                   │
│   │ → Faster, cheaper response           │                   │
│   └──────────────────────────────────────┘                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Pattern B: Plugin (Reusable Across Agents)

**Pros:** reusable across all agents, runs automatically
**Cons:** more boilerplate, harder to debug

```python
from google.adk.plugins import BasePlugin
import re

class IdEnrichmentPlugin(BasePlugin):
    """Extracts IDs from user messages and pre-fetches data."""

    name = "id_enrichment"

    def __init__(self, patterns: dict, fetchers: dict):
        """
        patterns: {"order": r'ORD-\\d+', "customer": r'CUST-\\d+'}
        fetchers: {"order": fetch_order_fn, "customer": fetch_customer_fn}
        """
        self.patterns = patterns
        self.fetchers = fetchers

    async def before_agent_callback(self, callback_context, **kwargs):
        session = callback_context.state._session
        last_msg = self._get_last_user_message(session)

        for key, pattern in self.patterns.items():
            matches = re.findall(pattern, last_msg)
            if matches and key in self.fetchers:
                data = await self.fetchers[key](matches[0])
                callback_context.state[f"temp:{key}_context"] = data

        return None

    def _get_last_user_message(self, session) -> str:
        for event in reversed(session.events):
            if event.content and event.content.role == "user":
                for part in event.content.parts:
                    if part.text:
                        return part.text
        return ""

# Reuse across all agents
enrichment = IdEnrichmentPlugin(
    patterns={"order": r'ORD-\d+', "customer": r'CUST-\d+'},
    fetchers={"order": fetch_order, "customer": fetch_customer},
)

app = App(name="my_app", root_agent=root_agent, plugins=[enrichment])
```

#### Pattern C: SequentialAgent with Preprocessor Agent

**Pros:** full LLM reasoning for extraction, handles complex cases
**Cons:** extra LLM call (cost + latency), overkill for regex-level tasks

```python
from google.adk import Agent
from google.adk.agents.sequential_agent import SequentialAgent

# Step 1: Extract and enrich
preprocessor = Agent(
    name="preprocessor",
    model="gemini-2.5-flash",
    instruction="""Extract any IDs from the user message (order IDs like ORD-XXX,
    customer IDs like CUST-XXX). Look up their details using the provided tools.
    Save results to state.""",
    tools=[lookup_order, lookup_customer],
    output_key="preprocessed_context",
)

# Step 2: Main agent uses enriched state
main_agent = Agent(
    name="support_agent",
    model="gemini-2.5-pro",
    instruction="""You are a support agent.
    The preprocessor has already fetched relevant data.
    Check state key 'preprocessed_context' for details.
    Help the user with their request.""",
    tools=[update_order, initiate_refund],
)

root_agent = SequentialAgent(
    name="support_pipeline",
    sub_agents=[preprocessor, main_agent],
)
```

```
┌─────────────────────────────────────────────────────┐
│ Pattern comparison:                                 │
│                                                     │
│ A: before_agent_callback                            │
│   + No extra LLM call (cheapest)                    │
│   + Deterministic extraction (regex)                │
│   - Only works for known patterns                   │
│                                                     │
│ B: Plugin                                           │
│   + Reusable across agents                          │
│   + No extra LLM call                               │
│   - Same limitation as A                            │
│                                                     │
│ C: SequentialAgent                                  │
│   + LLM handles ambiguous input                     │
│   + Can extract complex entities                    │
│   - Extra LLM call (slower, costlier)               │
│                                                     │
│ Recommendation: Use A or B for known ID formats,    │
│ use C when extraction requires understanding.       │
└─────────────────────────────────────────────────────┘
```

---

### Q4: What Is the Best Way to Pass Messages Between Agents?

Four mechanisms:

#### Method 1: Session State (Most Common)

Agents in the same session share state via `output_key` or direct writes:

**Pros:** simple, works immediately, persists across turns
**Cons:** global namespace (key collisions), no type safety

```python
# Agent A writes to state
agent_a = Agent(
    name="researcher",
    instruction="Research the topic and save findings.",
    output_key="research_findings", # Auto-saves text output to state
)

# Agent B reads from state
agent_b = Agent(
    name="writer",
    instruction="""Write an article based on state key 'research_findings'.
    Use the pre-researched material.""",
)

# Sequential pipeline: A → B
root = SequentialAgent(
    name="pipeline",
    sub_agents=[agent_a, agent_b],
)
```

```
State-based message passing:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ Agent A runs                                             │
│   │                                                      │
│   │ output_key="research_findings"                       │
│   │ Agent produces text → auto-saved to state            │
│   │                                                      │
│   │ state["research_findings"] = "Quantum computing..."  │
│   │                                                      │
│   ▼                                                      │
│ Agent B runs                                             │
│   │                                                      │
│   │ Instruction references {research_findings}           │
│   │ ADK replaces placeholder with state value            │
│   │                                                      │
│   │ Agent sees: "Write article based on:                 │
│   │   Quantum computing..."                              │
│   │                                                      │
│   ▼                                                      │
│ Final output                                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Method 2: Tool-Based State Writing

For more control over what gets passed:

**Pros:** LLM controls what gets written, natural language interface
**Cons:** unreliable (LLM may forget to call), extra tool call overhead

```python
def save_analysis(
    sentiment: str,
    confidence: float,
    key_themes: list[str],
    tool_context: ToolContext,
) -> str:
    """Save structured analysis results for downstream agents."""
    tool_context.state["analysis"] = {
        "sentiment": sentiment,
        "confidence": confidence,
        "themes": key_themes,
    }
    return "Analysis saved."

# Agent A uses the tool to write structured data
agent_a = Agent(
    name="analyzer",
    instruction="Analyze the text, then call save_analysis with your findings.",
    tools=[save_analysis],
)

# Agent B reads the structured data
agent_b = Agent(
    name="reporter",
    instruction="Read state['analysis'] and generate a report.",
)
```

#### Method 3: Agent Transfer (LLM-Driven Routing)

Transfer carries full session history:

**Pros:** LLM-driven routing, natural conversation flow
**Cons:** no structured data handoff, target sees full history (privacy)

```python
root = Agent(
    name="router",
    instruction="Route to the right specialist.",
    sub_agents=[
        Agent(
            name="billing",
            description="Handles billing and payment questions",
            instruction="Handle billing issues. Transfer back when done.",
        ),
        Agent(
            name="technical",
            description="Handles technical problems and bugs",
            instruction="Handle technical issues. Transfer back when done.",
        ),
    ],
)
```

```
Agent transfer message passing:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ User: "I have a billing question"                        │
│   │                                                      │
│   ▼                                                      │
│ router agent                                             │
│   │ LLM: transfer_to_agent("billing")                    │
│   │                                                      │
│   │ ┌─────────────────────────────────────┐              │
│   │ │ billing agent                       │              │
│   │ │ Sees FULL conversation history      │ ← shared     │
│   │ │ Sees ALL state                      │ ← session    │
│   │ │ Responds in same session            │              │
│   │ └─────────────────────────────────────┘              │
│   │                                                      │
│   │ When billing is done:                                │
│   │   transfer_to_agent("router") ← returns to parent    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Method 4: AgentTool (Isolated Execution)

Isolated execution without shared history:

**Pros:** isolated execution (own branch), structured input_schema
**Cons:** no shared history, heavier setup

```python
from google.adk.tools.agent_tool import AgentTool

helper = Agent(
    name="summarizer",
    instruction="Summarize the given text in 2-3 sentences.",
)

helper_tool = AgentTool(agent=helper)

main_agent = Agent(
    name="main",
    instruction="Use summarizer tool when you need to condense text.",
    tools=[helper_tool],
)
```

```
AgentTool message passing:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ main_agent                                               │
│   │                                                      │
│   │ LLM calls: summarizer(request="long text here...")   │
│   │   │                                                  │
│   │   ▼                                                  │
│   │   ┌───────────────────────────────────┐              │
│   │   │ summarizer agent (ISOLATED)       │              │
│   │   │ - New session (empty history)     │              │
│   │   │ - Only sees the request text      │              │
│   │   │ - Returns result as tool output   │              │
│   │   └──────────────────┬────────────────┘              │
│   │                      │                               │
│   │                      ▼                               │
│   │   Tool result: "Summary: ..."                        │
│   │   main_agent continues with summary                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Comparison Table

```
Message passing methods compared:
│
├── Session State (output_key)
│      Shares history: Yes
│      Shares state: Yes
│      Extra LLM call: No
│      Best for: Pipeline stages
│
├── Tool State Write (ToolContext.state)
│      Shares history: Yes
│      Shares state: Yes
│      Extra LLM call: No
│      Best for: Complex data
│
├── Agent Transfer (sub_agents)
│      Shares history: Yes
│      Shares state: Yes
│      Extra LLM call: Yes (route)
│      Best for: Dynamic routing
│
└── AgentTool (tool wrapper)
       Shares history: No (new session)
       Shares state: No (new session)
       Extra LLM call: Yes (child)
       Best for: Isolated helpers
```

---

### Q5: Explain All State Scopes — temp, user, app — and Their Visibility

State has four scopes controlled by key prefixes: session (no prefix), `user:`, `app:`, and `temp:` (invocation-only, never persisted). See [08-sessions.md](08-sessions.md) for the full scoping rules and nested diagram.

---

## Cross-references

- [00-onboarding-guide.md](00-onboarding-guide.md) — Start here if you're new
- [20-best-practices.md](20-best-practices.md) — Common mistakes to avoid
- [23-advanced-internals.md](23-advanced-internals.md) — Advanced patterns and internals
- [08-sessions.md](08-sessions.md) — Session state deep dive
- [09-tools.md](09-tools.md) — Tool system reference
- [12-artifacts.md](12-artifacts.md) — Artifact storage and versioning
- [13-auth.md](13-auth.md) — OAuth and credential management
- [04-agents.md](04-agents.md) — Agent types and configuration
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request example
