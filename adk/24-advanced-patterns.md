# Advanced Patterns — Recipes from the ADK Samples

**Audience:** Developers comfortable with the core ADK APIs who want production-ready patterns drawn directly from the `contributing/samples/` reference implementations.

**Source:** All code examples reference files in [adk-python](https://github.com/google/adk-python).

---

## 1. YAML-Defined Agent Hierarchies

ADK agents can be declared entirely in YAML instead of Python. Each YAML file represents one agent and references sub-agents via `config_path` and tools via dotted Python import paths.

### Schema format

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/google/adk-python/refs/heads/main/src/google/adk/agents/config_schemas/AgentConfig.json
agent_class: LlmAgent
model: gemini-2.5-flash
name: root_agent
description: Coordinator agent to greet users.
instruction: |
  You are a helpful assistant that can roll dice and check if numbers are prime.
  You delegate rolling dice tasks to the roll_agent and prime checking tasks to the prime_agent.
sub_agents:
  - config_path: roll_agent.yaml
  - config_path: prime_agent.yaml
tools:
  - name: multi_agent_llm_config.example_tool
generate_content_config:
  safety_settings:
    - category: HARM_CATEGORY_DANGEROUS_CONTENT
      threshold: 'OFF'
```

### Key fields

- **`agent_class`** — Which agent type to instantiate (e.g., `LlmAgent`).
- **`config_path`** — Relative path to a child agent's YAML file. ADK loads and wires the hierarchy automatically.
- **`tools[].name`** — Dotted Python path resolved at load time. For `multi_agent_llm_config.roll_die`, ADK imports `roll_die` from the `multi_agent_llm_config` package's `__init__.py`.

### Sub-agent YAML

Each sub-agent is its own file with the same schema. Tools reference functions from the parent package:

```yaml
# roll_agent.yaml
agent_class: LlmAgent
model: gemini-2.5-flash
name: roll_agent
description: Handles rolling dice of different sizes.
instruction: |
  You are responsible for rolling dice based on the user's request.
  When asked to roll a die, you must call the roll_die tool with the number of sides as an integer.
tools:
  - name: multi_agent_llm_config.roll_die
```

The Python functions live in `__init__.py` alongside the YAML files and are plain functions — no decorator needed:

```python
# __init__.py
def roll_die(sides: int) -> int:
    """Roll a die and return the rolled result."""
    return random.randint(1, sides)
```

**Source:** `contributing/samples/multi_agent_llm_config/`

---

## 2. ReflectAndRetryToolPlugin

A built-in plugin that intercepts tool failures, sends structured reflection guidance back to the LLM, and retries up to a configurable limit. The LLM sees the error details and is prompted to correct its approach.

### Basic usage

```python
from google.adk.plugins.reflect_retry_tool_plugin import (
    ReflectAndRetryToolPlugin,
    TrackingScope,
)

# Default: 3 retries, raises on exhaustion, per-invocation tracking
plugin = ReflectAndRetryToolPlugin()

# Global tracking, no exception on exhaustion
plugin = ReflectAndRetryToolPlugin(
    max_retries=5,
    throw_exception_if_retry_exceeded=False,
    tracking_scope=TrackingScope.GLOBAL,
)
```

### Custom error extraction via subclass

The base plugin only catches exceptions. To detect errors in successful tool responses (e.g., `{"status": "error"}`), override `extract_error_from_result`:

```python
class CustomRetryPlugin(ReflectAndRetryToolPlugin):
    async def extract_error_from_result(
        self, *, tool, tool_args, tool_context, result
    ):
        if isinstance(result, dict) and result.get("status") == "error":
            return result  # Returning non-None triggers retry logic
        return None         # No error detected
```

### How it works internally

1. **`on_tool_error_callback`** catches exceptions and calls `_handle_tool_error`.
2. **`after_tool_callback`** calls `extract_error_from_result` on successful results, then routes any detected error through the same handler.
3. **`_handle_tool_error`** increments a per-tool counter under `asyncio.Lock`, builds a `ToolFailureResponse` with structured reflection guidance, and returns it as the function response the LLM sees.
4. On success, the failure counter for that tool resets — other tools' counters are unaffected.

### Wiring it to an agent

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(name="root_agent", model="gemini-2.5-flash", tools=[my_tool])

# Pass as a plugin to the runner or TestInMemoryRunner
runner = Runner(agent=agent, plugins=[ReflectAndRetryToolPlugin(max_retries=3)])
```

**Source:** `src/google/adk/plugins/reflect_retry_tool_plugin.py`, `tests/unittests/plugins/test_reflect_retry_tool_plugin.py`

---

## 3. process_llm_request Override

Every `BaseTool` subclass can override `process_llm_request` to modify the `LlmRequest` before it is sent to the model. This runs during the request-processor pipeline and lets you inject ephemeral content (content that appears in the LLM prompt but is not persisted to session history).

### Pattern: inject artifact content on-demand

The `QueryLargeDataTool` saves large reports as artifacts, then injects the artifact content into `llm_request.contents` so the model can reference it immediately:

```python
from google.adk.tools.function_tool import FunctionTool
from google.adk.models.llm_request import LlmRequest
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from typing_extensions import override


class QueryLargeDataTool(FunctionTool):
    def __init__(self):
        super().__init__(query_large_data)

    @override
    async def process_llm_request(
        self,
        *,
        tool_context: ToolContext,
        llm_request: LlmRequest,
    ) -> None:
        # Always call super() first to preserve default behavior
        await super().process_llm_request(
            tool_context=tool_context, llm_request=llm_request
        )
        # Check if the last message is our tool's function response
        if llm_request.contents and llm_request.contents[-1].parts:
            fn_resp = llm_request.contents[-1].parts[0].function_response
            if fn_resp and fn_resp.name == "query_large_data":
                artifact_name = fn_resp.response.get("artifact_name")
                if artifact_name:
                    artifact = await tool_context.load_artifact(artifact_name)
                    if artifact:
                        # Append ephemeral content — visible to LLM, not saved to session
                        llm_request.contents.append(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_text(
                                        text=f"Artifact {artifact_name} is:"
                                    ),
                                    artifact,
                                ],
                            )
                        )
```

### Why not just return the data from the tool?

Large data in a function response becomes part of the session history forever, bloating every subsequent LLM call. Injecting via `process_llm_request` makes the content ephemeral — it is included in the current prompt only, then discarded.

**Source:** `contributing/samples/context_offloading_with_artifact/agent.py`

---

## 4. before_agent_callback as Triage Gate

A factory function returns a closure that reads from `callback_context.state` to decide whether an agent should execute. Combined with `ParallelAgent`, this creates selective activation — only agents relevant to the current task run.

### The factory pattern

```python
from typing import Optional
from google.adk.agents.base_agent import BeforeAgentCallback
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


def before_agent_callback_check_relevance(
    agent_name: str,
) -> BeforeAgentCallback:
    """Returns a closure that skips the agent if it is not in the execution list."""

    def callback(callback_context: CallbackContext) -> Optional[types.Content]:
        if agent_name not in callback_context.state["execution_agents"]:
            # Returning Content short-circuits — the agent does not run
            return types.Content(
                parts=[
                    types.Part(
                        text=f"Skipping execution agent {agent_name} as it is "
                             "not relevant to the current state."
                    )
                ]
            )
        # Returning None lets the agent proceed normally

    return callback
```

### Wiring it up

A triage agent (upstream) writes a list of relevant agent names into `state["execution_agents"]`. A `ParallelAgent` then runs all worker agents simultaneously, but each one's `before_agent_callback` checks the list and short-circuits if not relevant:

```python
from google.adk.agents import Agent, ParallelAgent, SequentialAgent

code_agent = Agent(
    model="gemini-2.5-flash",
    name="code_agent",
    instruction="You are the Code Agent...",
    before_agent_callback=before_agent_callback_check_relevance("code_agent"),
    output_key="code_agent_output",
)

math_agent = Agent(
    model="gemini-2.5-flash",
    name="math_agent",
    instruction="You are the Math Agent...",
    before_agent_callback=before_agent_callback_check_relevance("math_agent"),
    output_key="math_agent_output",
)

worker_parallel_agent = ParallelAgent(
    name="worker_parallel_agent",
    sub_agents=[code_agent, math_agent],
)
```

### Return semantics

- **Return `None`** — agent proceeds normally.
- **Return `types.Content`** — agent is skipped; the returned content becomes the agent's output event.

**Source:** `contributing/samples/workflow_triage/execution_agent.py`

---

## 5. before_tool_callback Arg Mutation

The `before_tool_callback` receives the tool's `args` dict by reference. There are two modes of operation based on what you return.

### Mode 1: Short-circuit (return a dict)

Returning a non-None value from the callback replaces the tool's response entirely — the tool function never runs:

```python
def before_tool_cb(tool, args, tool_context):
    if args.get("sides") > 100:
        # Short-circuit: return a response dict instead of running the tool
        return {"error": "Maximum 100 sides allowed"}
```

### Mode 2: Mutate args in place (return None)

Returning `None` (or not returning anything) lets the tool execute normally. But because `args` is a mutable dict passed by reference, any modifications you make are visible to the tool:

```python
def before_tool_cb(tool, args, tool_context):
    # Clamp sides to a maximum of 20
    if args.get("sides", 0) > 20:
        args["sides"] = 20
    # Return None — tool runs with the modified args
```

### Callback lists

Callbacks can be a single callable or a list. They execute in order. The first callback that returns a non-None value short-circuits — remaining callbacks and the tool itself are skipped:

```python
root_agent = Agent(
    model="gemini-2.0-flash",
    name="data_processing_agent",
    tools=[roll_die, check_prime],
    before_tool_callback=[before_tool_cb1, before_tool_cb2, before_tool_cb3],
    after_tool_callback=[after_tool_cb1, after_tool_cb2, after_tool_cb3],
)
```

### after_tool_callback comparison

`after_tool_callback` works similarly — returning a dict replaces the tool's response; returning `None` passes through. The callback in the samples demonstrates response wrapping:

```python
def after_tool_cb2(tool, args, tool_context, tool_response):
    # Replace the tool response with a wrapped version
    return {"test": "after_tool_cb2", "response": tool_response}
```

**Source:** `contributing/samples/callbacks/agent.py`, `src/google/adk/flows/llm_flows/functions.py`

---

## 6. output_schema with list of Pydantic Models

Setting `output_schema` to a `list[PydanticModel]` forces the LLM to return a JSON array conforming to the model schema. Combined with `output_key`, the parsed result is stored in session state for downstream agents.

### Pattern

```python
from google.adk import Agent
from pydantic import BaseModel


class WeatherData(BaseModel):
    temperature: str
    humidity: str
    wind_speed: str


root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    instruction="""\
Answer user's questions based on the data you have.

Here are the data you have for San Jose:
* temperature: 26 C
* humidity: 20%
* wind_speed: 29 mph

Here are the data you have for Cupertino:
* temperature: 16 C
* humidity: 10%
* wind_speed: 13 mph
""",
    output_schema=list[WeatherData],
    output_key="weather_data",
    tools=[get_current_year],
)
```

### What happens at runtime

1. The `output_schema_processor` in the request pipeline tells the LLM to respond with a JSON array matching the `WeatherData` schema.
2. The LLM response is validated against `list[WeatherData]`.
3. The validated result is stored in `state["weather_data"]` (via `output_key`), making it available to downstream agents or application code.

### When to use this

- Extracting structured records from unstructured text.
- Multi-item queries where you need a consistent schema per item.
- Feeding structured output into a downstream `SequentialAgent` that reads from state.

**Source:** `contributing/samples/fields_output_schema/agent.py`

---

## 7. FunctionTool with require_confirmation Callable

`FunctionTool` accepts a `require_confirmation` parameter that can be `True` (always confirm) or a callable that decides at runtime whether human approval is needed.

### Conditional confirmation with a callable

The callable receives the same arguments as the tool function. It returns `True` to require confirmation, `False` to proceed automatically:

```python
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext


def reimburse(amount: int, tool_context: ToolContext) -> str:
    """Reimburse the employee for the given amount."""
    return {"status": "ok"}


async def confirmation_threshold(
    amount: int, tool_context: ToolContext
) -> bool:
    """Returns true if the amount is greater than 1000."""
    return amount > 1000


root_agent = Agent(
    model="gemini-2.5-flash",
    name="time_off_agent",
    instruction="You are a helpful assistant...",
    tools=[
        FunctionTool(
            reimburse,
            require_confirmation=confirmation_threshold,
        ),
    ],
)
```

With this configuration, reimbursements of 1000 or less execute immediately, while amounts above 1000 pause for human approval.

### Manual confirmation via tool_context

For more complex flows (e.g., manager approval with a custom payload), you can use `tool_context.request_confirmation` directly inside the tool function:

```python
def request_time_off(days: int, tool_context: ToolContext):
    """Request day off for the employee."""
    if days <= 2:
        return {"status": "ok", "approved_days": days}

    tool_confirmation = tool_context.tool_confirmation
    if not tool_confirmation:
        # First call — request confirmation with a payload
        tool_context.request_confirmation(
            hint="Please approve or reject the time off request.",
            payload={"approved_days": 0},
        )
        return {"status": "Manager approval is required."}

    # Second call — confirmation has been provided
    approved_days = tool_confirmation.payload["approved_days"]
    return {"status": "ok", "approved_days": min(approved_days, days)}
```

### Resumability

For confirmation flows to work end-to-end, enable resumability on the `App`:

```python
from google.adk.apps import App, ResumabilityConfig

app = App(
    name="human_tool_confirmation",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
```

**Source:** `contributing/samples/human_tool_confirmation/agent.py`
