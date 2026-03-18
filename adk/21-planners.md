# Planners — Guided Reasoning for Agents

**Source:** [`planners/base_planner.py`](../adk-python/src/google/adk/planners/base_planner.py) · [`planners/built_in_planner.py`](../adk-python/src/google/adk/planners/built_in_planner.py) · [`planners/plan_re_act_planner.py`](../adk-python/src/google/adk/planners/plan_re_act_planner.py)

---

## What It Is

A planner gives an `LlmAgent` the ability to **think before it acts**. Instead of jumping straight into tool calls, an agent with a planner will first produce a structured plan (or use the model's internal thinking mode), then execute that plan step by step, re-planning when things go wrong.

Planners are optional. When `LlmAgent.planner` is `None` (the default), the agent runs its normal reason-act loop without any planning overlay. When set, the planner hooks into the flow's request and response processing pipeline via two methods: one that injects planning instructions into the LLM request, and one that post-processes the LLM response to separate reasoning from actions.

Use a planner when:
- Tasks require **multi-step reasoning** (research, analysis, multi-tool workflows)
- You want the agent to **decompose complex queries** before acting
- You need **visible chain-of-thought** for debugging or auditability
- The agent frequently makes wrong tool calls on the first attempt

---

## Class Hierarchy

```
BasePlanner           (base_planner.py)         — abstract, defines the two-method contract
    ├── BuiltInPlanner    (built_in_planner.py)  — delegates to Gemini's native thinking mode
    └── PlanReActPlanner  (plan_re_act_planner.py) — explicit plan-then-act via prompt engineering
```

---

## How Planners Integrate with Flows

Planners are invoked by the `_NlPlanningRequestProcessor` and `_NlPlanningResponse` processors inside the LLM flow pipeline (see [04-flows.md](04-flows.md)). The integration works like this:

```
BaseLlmFlow.run_async(ctx)
│
├─ PREPROCESS
│   ├─ ... (instructions, contents, functions)
│   └─ _NlPlanningRequestProcessor
│       ├─ BuiltInPlanner? → apply thinking_config to LlmRequest
│       └─ PlanReActPlanner? → append planning system instruction
│
├─ CALL MODEL
│
└─ POSTPROCESS
    ├─ _NlPlanningResponse
    │   ├─ BuiltInPlanner? → no-op (model handles thinking internally)
    │   └─ PlanReActPlanner? → split response into thought/action/final_answer parts
    └─ ... (function calls, agent transfer)
```

The planner is read from `agent.planner` on the current `InvocationContext`. If the field exists but is not a `BasePlanner` instance, ADK falls back to a default `PlanReActPlanner()`.

---

## BasePlanner — The Contract

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

### How the methods are used

| Method | Called by | Purpose |
|---|---|---|
| `build_planning_instruction` | `_NlPlanningRequestProcessor` (before model call) | Inject planning-related system instructions or config |
| `process_planning_response` | `_NlPlanningResponse` (after model call) | Parse response to separate reasoning from actions/answers |

---

## BuiltInPlanner — Model-Native Thinking

`BuiltInPlanner` leverages Gemini's built-in thinking features (extended thinking / chain-of-thought). It does not inject any prompt instructions. Instead, it configures `ThinkingConfig` on the LLM request, letting the model handle planning internally.

### Configuration

```python
class BuiltInPlanner(BasePlanner):
    thinking_config: types.ThinkingConfig

    def __init__(self, *, thinking_config: types.ThinkingConfig):
        self.thinking_config = thinking_config
```

The single configuration parameter is `thinking_config`, which is a `google.genai.types.ThinkingConfig` object. Key fields include:

| Field | Type | Description |
|---|---|---|
| `thinking_budget` | `int` | Maximum number of thinking tokens the model can use |

### Behavior

- **Request phase:** Calls `apply_thinking_config(llm_request)`, which sets `llm_request.config.thinking_config`. If a `thinking_config` was already set in `generate_content_config`, the planner's config overwrites it (with a warning).
- **Response phase:** Returns `None` (no post-processing). The model's thinking output is handled natively by the Gemini API.
- **Model requirement:** Only works with models that support thinking mode. An error is returned if used with unsupported models.

### Example

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

---

## PlanReActPlanner — Explicit Plan-Then-Act

`PlanReActPlanner` uses prompt engineering to enforce a structured planning loop. It injects a detailed system instruction that tells the model to follow a Plan-Reasoning-Action-FinalAnswer format, then post-processes the response to label parts as thoughts or actions.

### Configuration

`PlanReActPlanner` takes no constructor arguments:

```python
planner = PlanReActPlanner()
```

### Structured Tags

The planner defines five tags that structure the model's output:

| Tag | Purpose |
|---|---|
| `/*PLANNING*/` | Initial plan — numbered steps decomposing the query |
| `/*REPLANNING*/` | Revised plan after a failed or incomplete execution |
| `/*REASONING*/` | Summary of current state and next steps between tool calls |
| `/*ACTION*/` | Tool call section |
| `/*FINAL_ANSWER*/` | The final answer returned to the user |

### Behavior

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

### Example

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

### What the model output looks like (conceptual)

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

The planner marks everything before `/*FINAL_ANSWER*/` as thought (internal reasoning), and only the final answer text is surfaced to the user.

---

## When to Use Which

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

### Decision guide

```
Need an agent to reason before acting?
│
├─ Using Gemini with thinking support?
│   ├─ Want structured, visible plans? → PlanReActPlanner
│   └─ Trust model's internal reasoning? → BuiltInPlanner
│
├─ Using non-Gemini model (Anthropic, LiteLLM)?
│   └─ → PlanReActPlanner (only option)
│
└─ Simple task, no multi-step reasoning needed?
    └─ → No planner (leave planner=None)
```

---

## Writing a Custom Planner

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

## Cross-References

- [02-agents.md](02-agents.md) — `LlmAgent.planner` field definition; agent configuration
- [04-flows.md](04-flows.md) — How the planning processors fit into the request/response pipeline
- [05-models.md](05-models.md) — Model adapters and `ThinkingConfig` support
- [10-when-to-build-what.md](10-when-to-build-what.md) — Decision tree for custom `BasePlanner` subclasses
- [14-advanced-adk.md](14-advanced-adk.md) — Additional planner examples in the advanced topics section
