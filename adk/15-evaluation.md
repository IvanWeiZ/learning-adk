# Evaluation — Measuring Agent Quality

**Source:** [`evaluation/eval_case.py`](../adk-python/src/google/adk/evaluation/eval_case.py) · [`evaluation/eval_set.py`](../adk-python/src/google/adk/evaluation/eval_set.py) · [`evaluation/agent_evaluator.py`](../adk-python/src/google/adk/evaluation/agent_evaluator.py) · [`evaluation/evaluator.py`](../adk-python/src/google/adk/evaluation/evaluator.py)

---

## What It Is

ADK's evaluation framework lets you systematically measure whether your agents produce correct, high-quality responses. It is distinct from unit testing (which tests code logic) — evaluation tests **agent behavior**: does the agent say the right things, call the right tools, and reach the right conclusions?

The framework is built around three concepts:

1. **EvalCase** — a single test scenario (input + expected behavior)
2. **EvalSet** — a collection of EvalCases (a test suite)
3. **AgentEvaluator** — runs EvalCases against a live agent and scores results

The CLI command `adk eval` drives this system.

---

## Class Hierarchy

```
EvalCase                    (evaluation/eval_case.py — one scenario)
EvalSet                     (evaluation/eval_set.py — collection of EvalCases)

BaseEvaluator               (evaluation/evaluator.py — abstract scorer)
    ├── TrajectoryEvaluator     (scores tool call sequence)
    └── ResponseEvaluator       (scores final response text)

AgentEvaluator              (evaluation/agent_evaluator.py — orchestrates runs + scoring)
```

---

## Core Data Types

### EvalCase — One Test Scenario

```python
class EvalCase(BaseModel):
    eval_id: str                         # unique name for this case

    # The conversation to replay:
    conversation: list[ConversationTurn]
    # Each turn has a user message and optionally an expected agent response.

    # What the agent should have done (optional, for trajectory scoring):
    expected_tool_use: list[ToolUse] | None = None

    # Reference answer for response quality scoring:
    reference_answer: str | None = None

    # Per-case metric config overrides (inherits from EvalSet if absent):
    eval_metrics: list[EvalMetric] | None = None

    session_input: SessionInput | None = None  # pre-seeded state/history
```

### ConversationTurn

```python
class ConversationTurn(BaseModel):
    user_content: types.Content          # the user's message for this turn
    expected_tool_use: list[ToolUse] | None = None
    reference_answer: str | None = None  # expected agent reply for this turn
```

### ToolUse — Expected Tool Call

```python
class ToolUse(BaseModel):
    tool_name: str                       # e.g. "search_web"
    tool_input: dict[str, Any] | None    # expected arguments (None = any args ok)
    tool_output: str | None              # optional: mock output to inject
```

### EvalSet — A Suite of Cases

```python
class EvalSet(BaseModel):
    eval_set_id: str
    eval_cases: list[EvalCase]
    eval_metrics: list[EvalMetric]       # default metrics for all cases
    creation_timestamp: float
```

### EvalMetric — What to Measure

```python
class EvalMetric(BaseModel):
    metric_name: EvalMetricEnum          # which metric (see below)
    threshold: float                     # minimum passing score (0.0–1.0)

class EvalMetricEnum(str, Enum):
    TOOL_TRAJECTORY_AVG_SCORE = "tool_trajectory_avg_score"
    RESPONSE_MATCH_SCORE      = "response_match_score"
    # (custom metrics can be registered)
```

---

## AgentEvaluator — Running Evaluations

`AgentEvaluator` is the main entry point. It:
1. Replays each `EvalCase` against a real agent (using a `Runner`)
2. Collects actual tool calls and final responses
3. Scores them against expectations using configured evaluators
4. Returns pass/fail results per metric

```python
from google.adk.evaluation import AgentEvaluator

results = await AgentEvaluator.evaluate(
    agent_module="my_package.my_agent",  # importable module with 'agent' variable
    eval_dataset_file_path_or_dir="tests/evals/",  # .evalset.json files
    num_runs=1,                          # how many times to run each case
)
```

The returned `results` is a list of `EvalCaseResult` objects, one per case.

---

## EvalCaseResult — What You Get Back

```python
class EvalCaseResult(BaseModel):
    eval_set_id: str
    eval_id: str                             # matches EvalCase.eval_id
    final_eval_status: EvalStatus            # PASSED | FAILED
    eval_metric_results: list[EvalMetricResult]
    session_id: str                          # the session used for this run
```

```python
class EvalMetricResult(BaseModel):
    metric_name: str
    score: float                             # actual score (0.0–1.0)
    threshold: float                         # passing threshold
    eval_status: EvalStatus                  # PASSED | FAILED
```

---

## Metrics Deep Dive

### 1. `tool_trajectory_avg_score`

Measures whether the agent called the **right tools in the right order**.

Scoring logic:
- Each expected `ToolUse` is checked against the actual tool calls in sequence
- `tool_name` must match exactly
- `tool_input` is compared if provided (partial match is allowed — only specified keys are checked)
- Score = (matched steps) / (total expected steps)

Example: if you expect `[search, summarize]` and agent did `[search, translate, summarize]`, score is 1.0 (both expected steps matched, extras don't penalize).

### 2. `response_match_score`

Measures how well the agent's **final text response** matches the `reference_answer`.

ADK uses an LLM judge (typically Gemini) with a rubric like:
> "Does the candidate response convey the same information and intent as the reference answer? Score 0–5."

The raw score is normalized to 0.0–1.0.

This is a **model-graded** metric — it's fuzzy by design. Two semantically equivalent phrasings both score high.

---

## Eval File Format

EvalSets are stored as JSON files with the extension `.evalset.json`:

```json
{
  "eval_set_id": "weather_agent_evals",
  "eval_metrics": [
    { "metric_name": "tool_trajectory_avg_score", "threshold": 0.8 },
    { "metric_name": "response_match_score", "threshold": 0.7 }
  ],
  "eval_cases": [
    {
      "eval_id": "basic_weather_query",
      "conversation": [
        {
          "user_content": {
            "parts": [{ "text": "What is the weather in Paris?" }],
            "role": "user"
          },
          "expected_tool_use": [
            {
              "tool_name": "get_weather",
              "tool_input": { "city": "Paris" }
            }
          ],
          "reference_answer": "The weather in Paris is currently 18°C and partly cloudy."
        }
      ]
    }
  ]
}
```

---

## Running Evals via CLI

```bash
# Run all eval sets in a directory:
adk eval my_agent_module/ tests/evals/

# Run a specific eval set file:
adk eval my_agent_module/ tests/evals/weather.evalset.json

# Verbose output (shows per-turn tool calls):
adk eval --verbose my_agent_module/ tests/evals/
```

The CLI exits with code 0 if all cases pass, non-zero if any fail — suitable for CI.

---

## Running Evals Programmatically

```python
import asyncio
from google.adk.evaluation import AgentEvaluator

async def run_evals():
    results = await AgentEvaluator.evaluate(
        agent_module="my_weather_agent",
        eval_dataset_file_path_or_dir="tests/evals/",
    )
    for r in results:
        status = r.final_eval_status.value
        print(f"{r.eval_id}: {status}")
        for m in r.eval_metric_results:
            print(f"  {m.metric_name}: {m.score:.2f} (threshold {m.threshold})")

asyncio.run(run_evals())
```

---

## Integration with pytest

The recommended pattern is a thin pytest wrapper around `AgentEvaluator`:

```python
# tests/test_agent_eval.py
import pytest
from google.adk.evaluation import AgentEvaluator, EvalStatus

@pytest.mark.asyncio
async def test_weather_agent_evals():
    results = await AgentEvaluator.evaluate(
        agent_module="weather_agent",
        eval_dataset_file_path_or_dir="tests/evals/",
    )
    failures = [r for r in results if r.final_eval_status == EvalStatus.FAILED]
    assert not failures, (
        f"{len(failures)} eval case(s) failed: "
        + ", ".join(f.eval_id for f in failures)
    )
```

Run with: `pytest tests/test_agent_eval.py -v`

---

## Writing Good Eval Cases

**Cover the happy path first:**
```json
{ "eval_id": "simple_greeting", ... }
```

**Then edge cases and refusals:**
```json
{ "eval_id": "out_of_scope_query", ... }
{ "eval_id": "ambiguous_city_name", ... }
```

**Use `tool_input: null` when argument values are flexible:**
```json
{ "tool_name": "search_web", "tool_input": null }
```
This checks that the agent *called* the tool without asserting which exact query it used.

**Set `reference_answer` for open-ended responses, skip it for tool-only cases:**
- If you only care about tool trajectory → set `expected_tool_use`, leave `reference_answer` null
- If you only care about the response content → set `reference_answer`, leave `expected_tool_use` null
- For full coverage → set both

---

## Eval vs Unit Test — When to Use Each

| Scenario | Use |
|---|---|
| Tool function returns correct value | `pytest` unit test |
| Agent calls the right tool | Eval with `tool_trajectory_avg_score` |
| Agent's answer is factually correct | Eval with `response_match_score` |
| Multi-turn conversation flow | Eval with multi-turn `conversation` |
| Callback fires correctly | `pytest` unit test with `AsyncMock` |
| Agent handles ambiguous input gracefully | Eval with `reference_answer` |

---

## Java Comparison

| Java concept | ADK equivalent |
|---|---|
| JUnit `@Test` | `EvalCase` |
| Test suite (`@Suite`) | `EvalSet` / `.evalset.json` |
| AssertJ / Hamcrest matchers | `EvalMetric` thresholds |
| Integration test | Multi-turn `EvalCase` with tool trajectory |
| Contract test | `tool_trajectory_avg_score` (verifies tool API usage) |
| Snapshot test | `response_match_score` with fixed `reference_answer` |

---

## Related Files

- [`evaluation/eval_case.py`](../adk-python/src/google/adk/evaluation/eval_case.py) — EvalCase, ConversationTurn, ToolUse
- [`evaluation/eval_set.py`](../adk-python/src/google/adk/evaluation/eval_set.py) — EvalSet, EvalMetric
- [`evaluation/agent_evaluator.py`](../adk-python/src/google/adk/evaluation/agent_evaluator.py) — main entry point
- [`evaluation/evaluator.py`](../adk-python/src/google/adk/evaluation/evaluator.py) — BaseEvaluator, metric implementations
- [`python-testing-and-mocking-guide.md`](./python-testing-and-mocking-guide.md) — unit testing with pytest/AsyncMock
- [`09-tools.md`](./09-tools.md) — tool system (what evals are testing)
- [`02-when-to-build-what.md`](./02-when-to-build-what.md) — decision guide including when to write evals
