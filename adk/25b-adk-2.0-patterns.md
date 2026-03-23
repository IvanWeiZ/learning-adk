# 25b — ADK 2.0: Collaborative Agents, Dynamic Workflows & Migration

> **Official docs:** [ADK 2.0](https://google.github.io/adk-docs/2.0/) | **Source:** `pip install google-adk --pre` | **Prereqs:** [25-adk-2.0-preview.md](25-adk-2.0-preview.md)

*This file continues from [25-adk-2.0-preview.md](25-adk-2.0-preview.md), which covers overview and graph workflows.*

> **Warning:** ADK 2.0 is an **alpha release**. APIs, import paths, and behavior may change without notice between pre-release versions. Do not use in production. Install with `pip install google-adk --pre`.

---

## Collaborative Agents

> **Official docs:** [Collaborative Agents](https://google.github.io/adk-docs/workflows/collaboration/)

A coordinator agent delegates tasks to subagents. Three operating modes control how subagents interact.

### Mode comparison

```
Subagent Modes:
│
├── chat (default)
│   ├── Full user interaction (questions, clarifications)
│   ├── Manual return via transfer_to_agent
│   └── NOT parallel — blocks the coordinator
│
├── task
│   ├── Autonomous execution with optional clarification
│   ├── Automatic return via finish_task tool (FinishTaskTool)
│   └── Cannot have sub-agents of its own (leaf only)
│
└── single_turn
    ├── No user interaction at all
    ├── Automatic immediate return after one LLM call
    ├── Each agent gets isolated session branch
    └── CAN run in parallel with other single_turn agents
```

### Key difference from 1.x transfer

```
1.x transfer_to_agent:
├── LLM decides which agent to call
├── No structured return
├── No parallel execution within a transfer
└── All agents share the same branch

2.0 collaborative modes:
├── Coordinator orchestrates delegation
├── task/single_turn agents return automatically
├── single_turn agents run in parallel with branch isolation
└── Structured input/output schemas for data flow
```


### Chat mode — full conversation handoff

```python
# NOTE: Import paths are beta and subject to change in future pre-release versions.
# If you hit ModuleNotFoundError, check the latest: pip show google-adk
from google.adk import Agent  # or: from google.adk.agents.llm_agent import Agent

support_agent = Agent(
    name="support_agent",
    mode="chat",
    model="gemini-2.5-flash",
    instruction="""You are a support specialist. Ask clarifying
    questions. When resolved, transfer back to coordinator.""",
    tools=[search_kb, create_ticket],
)

coordinator = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    instruction="Route support requests to support_agent.",
    sub_agents=[support_agent],
)
```

### Task mode — autonomous with auto-return

```python
from pydantic import BaseModel

class ResearchResult(BaseModel):
    summary: str
    sources: list[str]
    confidence: float

research_agent = Agent(
    name="research_agent",
    mode="task",
    model="gemini-2.5-flash",
    instruction="""Research the given topic. When done, call the finish_task tool.""",
    input_schema=str,
    output_schema=ResearchResult,
    tools=[web_search, summarize_page],
)

coordinator = Agent(
    name="coordinator",
    model="gemini-2.5-flash",
    instruction="Delegate research requests to research_agent.",
    sub_agents=[research_agent],
)
```

### Single-turn mode — parallel, isolated, instant

```python
weather_agent = Agent(name="weather_checker", mode="single_turn",
    model="gemini-2.5-flash", instruction="Get current weather.",
    tools=[get_weather])

news_agent = Agent(name="news_checker", mode="single_turn",
    model="gemini-2.5-flash", instruction="Get top 3 news headlines.",
    tools=[fetch_news])

stock_agent = Agent(name="stock_checker", mode="single_turn",
    model="gemini-2.5-flash", instruction="Get watched stock prices.",
    tools=[get_stock_price])

# All three run in parallel
coordinator = Agent(
    name="morning_briefing",
    model="gemini-2.5-flash",
    # Coordinator receives results from each single_turn agent via their output schemas.
    # Each sub-agent result is available in session state (keyed by agent name) after
    # all parallel calls complete. The coordinator's instruction can reference them.
    instruction="""Create a morning briefing.
    Combine: weather from weather_checker, news from news_checker, stocks from stock_checker.
    Format as a concise briefing.""",
    sub_agents=[weather_agent, news_agent, stock_agent],
)
```


---

## Dynamic Workflows

> **Official docs:** [Dynamic Workflows](https://google.github.io/adk-docs/workflows/dynamic/)

For complex logic that doesn't fit a static graph — use Python control flow directly.

Dynamic Workflows are an ADK 2.0 concept separate from, but complementary to, the graph `Workflow` API in [25-adk-2.0-preview.md](25-adk-2.0-preview.md). Where `Workflow` uses a static `edges=` definition, Dynamic Workflows use Python code and the `@node` decorator to express flow. The two primitives — `@node` functions and `ctx.run_node()` — form a checkpointed execution model: each sub-node records its result, and on resume, already-completed nodes are skipped automatically.

### The @node decorator

```python
from google.adk.workflow import node  # node is in google.adk.workflow, not top-level
from google.adk import Context, Event

@node(name="checker")
async def check_code(ctx: Context, code: str) -> dict:
    return {"findings": ["unused import", "missing docstring"]}
```

### ctx.run_node() — execute and return

```python
@node(rerun_on_resume=True)
async def pipeline(ctx: Context, user_request: str) -> str:
    raw_draft = await ctx.run_node(draft_agent, user_request)
    formatted  = await ctx.run_node(format_function, raw_draft)
    reviewed   = await ctx.run_node(review_agent, formatted)
    return reviewed
```

### Loops with standard Python

```python
@node(rerun_on_resume=True)
async def code_review_loop(ctx: Context, code: str) -> str:
    check_resp = await ctx.run_node(compile_lint_check, code)

    while check_resp.findings:
        yield Event(state={"code": code, "findings": check_resp.findings})
        code = await ctx.run_node(fixer_agent, code)
        check_resp = await ctx.run_node(compile_lint_check, code)

    return code
```

### Checkpointing and resume

Successful sub-nodes are **automatically skipped** when a workflow resumes:

```python
@node(rerun_on_resume=True)
async def resilient_pipeline(ctx: Context, data: str) -> str:
    """On resume: step_1 and step_2 SKIPPED (checkpointed), step_3 re-runs."""
    result_1 = await ctx.run_node(step_1, data)
    result_2 = await ctx.run_node(step_2, result_1)
    result_3 = await ctx.run_node(step_3, result_2)
    return result_3
```

### Human-in-the-loop with RequestInput

```python
from google.adk.workflow import BaseNode  # BaseNode is in google.adk.workflow
from google.adk.events import RequestInput  # RequestInput is in google.adk.events
from google.adk import Context
from typing import AsyncGenerator, Any

class GetInput(BaseNode):
    rerun_on_resume = False

    def __init__(self, request: RequestInput, name: str):
        super().__init__(name=name)
        self.request = request

    async def run(self, *, ctx: Context, node_input: Any) -> AsyncGenerator[Any, None]:
        yield self.request

@node(rerun_on_resume=True)
async def approval_workflow(ctx: Context, proposal: str) -> str:
    summary = await ctx.run_node(summarize_agent, proposal)

    request = RequestInput(message=f"Approve this summary?\n\n{summary}\n\n(Yes/No)")
    user_response = await ctx.run_node(GetInput(request, "approval_step"))

    if user_response.lower() == "yes":
        return await ctx.run_node(publish_agent, summary)
    else:
        return "Publication cancelled by reviewer."
```

### Parallel node execution with asyncio.gather

```python
import asyncio
from google.adk.workflow import node
from google.adk import Context

@node(rerun_on_resume=True)
async def parallel_analysis(ctx: Context, document: str) -> dict:
    sentiment, summary, entities = await asyncio.gather(
        ctx.run_node(sentiment_agent, document),
        ctx.run_node(summary_agent, document),
        ctx.run_node(entity_extractor, document),
    )
    return {"sentiment": sentiment, "summary": summary, "entities": entities}
```

### Key features summary

```
Dynamic Workflows:
│
├── @node decorator — wraps functions into workflow nodes
├── FunctionNode — alternative without decorators
├── ctx.run_node() — executes child nodes, returns output
├── Automatic checkpointing — sub-nodes SKIPPED on resume
├── rerun_on_resume — controls parent re-execution
├── Standard Python loops — while/for with yield Event
├── asyncio.gather() — parallel node execution
├── RequestInput + BaseNode — human-in-the-loop
└── Custom execution IDs — stable checkpoint identity
```

---

## Migration Notes: 1.x to 2.0

**Known breaking changes and compatibility notes:**

```
Environment
│
├── Python 3.11+ required (1.x supports 3.10+)
├── Install separately: pip install google-adk --pre
└── NEVER mix 1.x and 2.0 in the same venv

Storage
│
├── Session databases are NOT compatible between 1.x and 2.0
├── Memory service formats changed — use separate storage
└── Eval datasets: format may differ — recreate for 2.0

Import paths changed
│
├── 1.x: from google.adk.agents.llm_agent import Agent
├── 2.0: from google.adk import Agent, Runner, Workflow, Context, Event
│         (Agent is LlmAgent aliased at top level)
├── @node: from google.adk.workflow import node
├── BaseNode: from google.adk.workflow import BaseNode
├── RequestInput: from google.adk.events import RequestInput
└── New types: Workflow, Event(message=), Event(route=), @node, Context

API additions (2.0-only)
│
├── Agent(mode="chat"|"task"|"single_turn") — new field
├── output_schema=str — bare Python types now accepted
├── input_schema= — structured graph node input
├── Workflow(edges=[...]) — new class
├── @node decorator and ctx.run_node()
└── Event(message=...) / Event(route=...) — graph event fields

Existing 1.x code
│
├── LlmAgent / Agent — unchanged
├── SequentialAgent, ParallelAgent, LoopAgent — unchanged
├── Tool functions and callbacks — unchanged
└── Sessions and state access — unchanged
```

---

## Related

| Topic | Link |
|---|---|
| Graph workflows overview | [25-adk-2.0-preview.md](25-adk-2.0-preview.md) |
| Official collaborative agents | [google.github.io/adk-docs/workflows/collaboration/](https://google.github.io/adk-docs/workflows/collaboration/) |
| Official dynamic workflows | [google.github.io/adk-docs/workflows/dynamic/](https://google.github.io/adk-docs/workflows/dynamic/) |
| 1.x agent transfer (this repo) | [04-agents.md](04-agents.md) |
| ADK Python GitHub | [github.com/google/adk-python](https://github.com/google/adk-python) |
