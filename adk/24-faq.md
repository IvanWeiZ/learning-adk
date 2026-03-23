# 24 — FAQ: Common Questions & Answers

> **Official docs:** [Quickstart](https://google.github.io/adk-docs/get-started/quickstart/) | **Source:** patterns across all ADK modules | **Prereqs:** [04-agents.md](04-agents.md), [08-sessions.md](08-sessions.md), [09-tools.md](09-tools.md)

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

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
        # Look up the new tool by name from the agent's resolved tool list.
        # Build this dict at setup time or inside the callback:
        all_tools = {t.name: t for t in tool_context.agent.tools}
        new_tool = all_tools[new_name]
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

Follow this test pyramid:

```
Testing pyramid for ADK agents:
│
├── Unit tests (tool functions)
│      Use: FunctionTool(fn).run_async(args, tool_context=MagicMock())
│      Fast, no LLM, no state
│
├── Component tests (single agent)
│      Use: InMemoryRunner(agent) + MockModel.create(responses=[...])
│      Deterministic LLM responses, real ADK pipeline
│
├── Integration tests (multi-agent / pipeline)
│      Use: InMemoryRunner(root_agent) + MockModel per sub-agent
│      Tests routing, state passing, callbacks end-to-end
│
└── E2E tests (real LLM, real storage)
       Use: Runner + DatabaseSessionService + real model
       Run only in CI — slow and costly
```

Key rules:
- Never mock ADK internals (`BaseLlmFlow`, `Runner`) — mock only the LLM and external services
- `InMemoryRunner` reuses the same session across `.run()` calls — tests multi-turn correctly
- `TestInMemoryRunner` creates a new session per call — tests isolation

For `MockModel`, `InMemoryRunner`, `simplify_events`, and complete test patterns, see [22-testing.md](22-testing.md) and [22c-testing-examples.md](22c-testing-examples.md).

---

### Q3: What Is the Best Way to Preprocess User Requests (Extract IDs, Enrich Data)?

> For full worked examples with production-ready code, see [24b-custom-use-cases.md](24b-custom-use-cases.md).

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
    # WARNING: _session is a private attribute — no public API exists for this.
    # It may change without notice in future ADK versions.
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
        # WARNING: _session is a private attribute — no public API exists for this.
        # It may change without notice in future ADK versions.
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

Four mechanisms are available: session state (via `output_key`), tool-based state writing, agent transfer, and `AgentTool`. Each differs in isolation, history sharing, and whether an extra LLM call is required.

See [24c-message-passing-patterns.md](24c-message-passing-patterns.md) for full code examples and comparison table.

---

### Q5: Explain All State Scopes — temp, user, app — and Their Visibility

State keys are prefixed to determine scope. ADK routes writes to separate storage tables and strips `temp:` before persisting.

```
State scopes at a glance:
│
├── (no prefix) — session scope
│      Visible to: all agents within this session
│      Persisted: yes, until session deleted
│      Use for: conversation context, cart, step tracking
│      NEVER store: passwords, credit cards, PII
│
├── user: — user scope
│      Visible to: all sessions for this user_id + app_name
│      Persisted: yes, until user data deleted
│      Use for: preferences, persona, history summaries
│      NEVER store: secrets, medical data, SSNs
│
├── app: — app scope
│      Visible to: ALL users in this app_name
│      Persisted: yes, global to the app
│      Use for: feature flags, shared config
│      NEVER store: any user data, any tenant-specific data
│
└── temp: — invocation scope
       Visible to: current invocation only
       Persisted: NO — stripped before session save
       Use for: OAuth tokens, scratch values, cache for this request
       NEVER store: data needed after this single invocation
```

The prefix determines the storage table. `temp:` is special — it lives only in memory during a single `runner.run_async()` call and is never written to the database.

See [08-sessions.md](08-sessions.md) for the full scoping rules and [19-session-security.md](19-session-security.md) for security considerations per scope.

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
