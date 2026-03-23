# 14 — Planners: Think Before Acting

> **Official docs:** [LLM Agents](https://google.github.io/adk-docs/agents/llm-agents/) | **Source:** [`planners/base_planner.py`](https://github.com/google/adk-python/blob/main/src/google/adk/planners/base_planner.py) · [`planners/built_in_planner.py`](https://github.com/google/adk-python/blob/main/src/google/adk/planners/built_in_planner.py) · [`planners/plan_re_act_planner.py`](https://github.com/google/adk-python/blob/main/src/google/adk/planners/plan_re_act_planner.py) | **Prereqs:** [04-agents.md](04-agents.md), [05-flows.md](05-flows.md)

---

## At a Glance

```
LlmAgent(planner=...)
│
▼
BaseLlmFlow.run_async(ctx)
│
├─ PREPROCESS ─► _NlPlanningRequestProcessor (internal processor)
│ ├─ BuiltInPlanner → flow processor calls apply_thinking_config() directly
│ └─ PlanReActPlanner → calls build_planning_instruction(), appends to system prompt
│
├─ CALL MODEL
│
└─ POSTPROCESS ─► _NlPlanningResponse (internal processor)
  ├─ BuiltInPlanner → no-op (model handles thinking natively)
  └─ PlanReActPlanner → splits response into thought / action / final_answer
```

A planner gives an `LlmAgent` the ability to produce a structured plan before acting, then execute step by step, re-planning on failure. It is optional -- default `None` means normal reason-act loop. When set, the planner injects planning instructions into the request and post-processes the response to separate reasoning from actions.

Use a planner when:
- Tasks require **multi-step reasoning** (research, analysis, multi-tool workflows)
- You want the agent to **decompose complex queries** before acting
- You need **visible chain-of-thought** for debugging or auditability
- The agent frequently makes wrong tool calls on the first attempt

---

## Class Hierarchy

```
BasePlanner (base_planner.py) — abstract, defines the two-method contract
 ├── BuiltInPlanner (built_in_planner.py) — delegates to Gemini's native thinking mode
 └── PlanReActPlanner (plan_re_act_planner.py) — explicit plan-then-act via prompt engineering
```

---

## Key API

### BasePlanner -- The Contract

Every planner implements two abstract methods:

```python
class BasePlanner(ABC):
    """Abstract base class for all planners."""

    @abc.abstractmethod
    def build_planning_instruction(
        self,
        readonly_context: ReadonlyContext,
        llm_request: LlmRequest,
    ) -> str | None:
        """Builds a system instruction appended to the LLM request for planning.

        Returns the instruction string, or None if no instruction is needed.
        """

    @abc.abstractmethod
    def process_planning_response(
        self,
        callback_context: CallbackContext,
        response_parts: list[types.Part],
    ) -> list[types.Part] | None:
        """Post-processes the LLM response parts for planning.

        Returns processed parts, or None if no processing is needed.
        """
```

| Method | Called by | Purpose |
|---|---|---|
| `build_planning_instruction` | `_NlPlanningRequestProcessor` (before model call) | Inject planning-related system instructions or config |
| `process_planning_response` | `_NlPlanningResponse` (after model call) | Parse response to separate reasoning from actions/answers |

### BuiltInPlanner

`BuiltInPlanner` configures `ThinkingConfig` on the LLM request, delegating to Gemini's native thinking mode. No prompt injection.

```python
class BuiltInPlanner(BasePlanner):
    thinking_config: types.ThinkingConfig

    def __init__(self, *, thinking_config: types.ThinkingConfig):
        self.thinking_config = thinking_config
```

`ThinkingConfig` has one key field: `thinking_budget: int` — the maximum number of thinking tokens the model can use.

Behavior:

- **Request phase:**
  - The flow processor (`_NlPlanningRequestProcessor`) calls `planner.apply_thinking_config(llm_request)` directly.
  - It does **not** call `build_planning_instruction()` — that method returns `None` for `BuiltInPlanner`. (BuiltInPlanner skips instruction injection — it configures the model directly via `apply_thinking_config` instead.)
  - `apply_thinking_config` sets `llm_request.config.thinking_config`. If a `thinking_config` was already set in `generate_content_config`, the planner's config overwrites it (with a `debug`-level log).
- **Response phase:** Returns `None` (no post-processing). The model's thinking output is handled natively by the Gemini API.
- **Model requirement:** Only works with models that support thinking mode. An error is returned if used with unsupported models.

### PlanReActPlanner

`PlanReActPlanner` injects a system instruction enforcing Plan-Reasoning-Action-FinalAnswer format, then post-processes responses to label parts as thoughts or actions. Takes no constructor arguments:

```python
planner = PlanReActPlanner()
```

Structured tags that the planner defines:

| Tag | Purpose |
|---|---|
| `/*PLANNING*/` | Initial plan -- numbered steps decomposing the query |
| `/*REPLANNING*/` | Revised plan after a failed or incomplete execution |
| `/*REASONING*/` | Summary of current state and next steps between tool calls |
| `/*ACTION*/` | Tool call section |
| `/*FINAL_ANSWER*/` | The final answer returned to the user |

Behavior:

- **Request phase:** `build_planning_instruction()` returns a multi-section system prompt that instructs the model to:
  1. Create a numbered plan under `/*PLANNING*/`
  2. Interleave tool calls (`/*ACTION*/`) with reasoning (`/*REASONING*/`)
  3. Re-plan under `/*REPLANNING*/` if execution fails
  4. Produce a final answer under `/*FINAL_ANSWER*/`

- **Response phase:** `process_planning_response()` parses the model's output:
  - Text starting with `/*PLANNING*/`, `/*REASONING*/`, `/*ACTION*/`, or `/*REPLANNING*/` is marked as `thought=True` (hidden from the user by default)
  - Text after the last `/*FINAL_ANSWER*/` tag is preserved as the visible response
  - Function call parts are preserved and grouped together
  - Empty function call names are filtered out

---

## How It Works

### Planner Integration with Flows

Planners are invoked by internal processors (`_NlPlanningRequestProcessor` and `_NlPlanningResponse`) inside the LLM flow pipeline (see [05-flows.md](05-flows.md) and [23-advanced-internals.md](23-advanced-internals.md)). The planner is read from `agent.planner` on the current `InvocationContext`. If the field exists but is not a `BasePlanner` instance, ADK falls back to a default `PlanReActPlanner()`.

### What the Model Output Looks Like (PlanReActPlanner)

```
/*PLANNING*/
1. Query the database for sales data from Q1 2026
2. Create a bar chart comparing monthly totals
3. Export the results as CSV

/*ACTION*/
[function_call: query_database(query="SELECT ...")]

/*REASONING*/
The query returned 3 rows with monthly totals. Next, I'll create a chart.

/*ACTION*/
[function_call: create_chart(data=..., type="bar")]

/*FINAL_ANSWER*/
Here are the Q1 2026 sales results: ...
```

Everything before `/*FINAL_ANSWER*/` is internal reasoning (marked as `thought=True`). Only the final answer (marked `thought=False`) reaches the user.

### When to Use Which

| Criteria | BuiltInPlanner | PlanReActPlanner |
|---|---|---|
| **Mechanism** | Model-native thinking mode | Prompt-injected planning structure |
| **Model requirement** | Gemini models with thinking support | Any model (no special features needed) |
| **Configuration** | `ThinkingConfig` (thinking budget) | None (zero-config) |
| **Plan visibility** | Internal to model (opaque unless model exposes thinking) | Explicit tags in output (parseable, debuggable) |
| **Re-planning** | Model decides internally | Explicit `/*REPLANNING*/` when execution fails |
| **Response processing** | None (model handles it) | Splits response into thought/action/answer parts |
| **Token overhead** | Thinking tokens (counted separately) | Planning instructions added to system prompt |
| **Best for** | Simple-to-moderate tasks where model thinking is sufficient | Complex multi-step tasks needing visible, structured plans |

Decision guide:

```
Need an agent to reason before acting?
│
├─ Using Gemini with thinking support?
│ ├─ Want structured, visible plans? → PlanReActPlanner
│ └─ Trust model's internal reasoning? → BuiltInPlanner
│
├─ Using non-Gemini model (Anthropic, LiteLLM)?
│ └─ → PlanReActPlanner (only option)
│
└─ Simple task, no multi-step reasoning needed?
  └─ → No planner (leave planner=None)
```

---

## Examples

### BuiltInPlanner

```python
from google.adk import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

agent = Agent(
    name="research_agent",
    model="gemini-2.5-flash",
    instruction="You are a research assistant that thoroughly analyzes questions.",
    tools=[search_tool, summarize_tool],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(thinking_budget=2048)
    ),
)
```

### PlanReActPlanner

```python
from google.adk import Agent
from google.adk.planners import PlanReActPlanner

agent = Agent(
    name="data_analyst",
    model="gemini-2.5-flash",
    instruction="You are a data analyst. Answer questions using the available tools.",
    tools=[query_database, create_chart, export_csv],
    planner=PlanReActPlanner(),
)
```

### Writing a Custom Planner

Subclass `BasePlanner` and implement both methods:

```python
from google.adk.planners import BasePlanner
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types

class MyCustomPlanner(BasePlanner):
    def build_planning_instruction(
        self,
        readonly_context: ReadonlyContext,
        llm_request: LlmRequest,
    ) -> str | None:
        # Return a system instruction string, or None
        return "Before answering, outline your approach in 3 bullet points."

    def process_planning_response(
        self,
        callback_context: CallbackContext,
        response_parts: list[types.Part],
    ) -> list[types.Part] | None:
        # Post-process parts, or return None for no changes
        return None

agent = Agent(
    name="custom_planner_agent",
    model="gemini-2.5-flash",
    planner=MyCustomPlanner(),
    ...
)
```

---

## Gotchas

- `BuiltInPlanner` only works with Gemini models that support thinking mode. Using it with unsupported models returns an error.
- If `agent.planner` is set to something that is not a `BasePlanner` instance, ADK falls back to a default `PlanReActPlanner()` -- it does not raise an error.
- `BuiltInPlanner` overwrites any existing `thinking_config` in `generate_content_config` (with a `debug`-level log), so do not set both.
- `PlanReActPlanner` adds planning instructions to the system prompt, consuming tokens on every request even when planning is not needed for simple queries.
- Empty function call names in `PlanReActPlanner` output are silently filtered out.

---

## Related

- [04-agents.md](04-agents.md) -- `LlmAgent.planner` field definition; agent configuration
- [05-flows.md](05-flows.md) -- How the planning processors fit into the request/response pipeline
- [06-models.md](06-models.md) -- Model adapters and `ThinkingConfig` support
- [02-when-to-build-what.md](02-when-to-build-what.md) -- Decision tree for custom `BasePlanner` subclasses
- [23-advanced-internals.md](23-advanced-internals.md) -- Additional planner examples in the advanced topics section
