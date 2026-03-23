# 15 — Evaluation: Agent Quality Testing

> **Official docs:** [Evaluation](https://google.github.io/adk-docs/evaluate/) | **Source:** [`evaluation/eval_case.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/eval_case.py) · [`evaluation/eval_set.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/eval_set.py) · [`evaluation/agent_evaluator.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/agent_evaluator.py) · [`evaluation/evaluator.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/evaluator.py) | **Prereqs:** [09-tools.md](09-tools.md), [03-runners.md](03-runners.md)

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

---

## At a Glance

```
┌─────────────────────────────────────────┐
│         adk eval / AgentEvaluator       │
│                                         │
│  EvalSet (.json)                        │
│    │  contains EvalCase (scenario)      │
│    ▼                                    │
│  Runner (live agent)                    │
│    │  replays conversation turns        │
│    ▼                                    │
│  actual events                          │
│    │                                    │
│    ▼                                    │
│  Evaluator                              │
│    │  TrajectoryEvaluator               │
│    │  ResponseEvaluator                 │
│    ▼                                    │
│  EvalCaseResult (PASSED / FAILED /      │
│                  NOT_EVALUATED)          │
└─────────────────────────────────────────┘
```

ADK's evaluation framework measures agent behavior -- correct responses, right tool calls, right conclusions. You define test scenarios as `EvalCase` objects grouped into an `EvalSet`, then `AgentEvaluator` replays them against a live agent and scores the results using configurable metrics (tool trajectory, response quality). This is distinct from unit testing, which validates code logic.

---

## Class Hierarchy

```
EvalCase (evaluation/eval_case.py — one scenario)
EvalSet (evaluation/eval_set.py — collection of EvalCases)

Evaluator (evaluation/evaluator.py — abstract scorer)
 ├── TrajectoryEvaluator (scores tool call sequence)
 └── ResponseEvaluator (scores final response text)

AgentEvaluator (evaluation/agent_evaluator.py — orchestrates runs + scoring)
```

---

## Key API

### EvalCase — One Test Scenario

```python
class EvalCase(BaseModel):
    eval_id: str # unique name for this case

    # The conversation to replay (each entry is one invocation):
    conversation: Optional[list[Invocation]] = None

    # Scenario description for the conversation:
    conversation_scenario: Optional[str] = None
    # NOTE: exactly one of conversation or conversation_scenario must be provided (enforced by validator)

    # Rubrics for scoring (applied across the whole case):
    rubrics: Optional[list[Rubric]] = None # Rubric from eval_rubrics.py

    # Expected final session state after all turns:
    final_session_state: Optional[dict[str, Any]] = Field(default_factory=dict)

    session_input: SessionInput | None = None # pre-seeded state/history
    creation_timestamp: float = 0.0
```

### Invocation — One Turn in the Conversation

```python
class Invocation(BaseModel):
    invocation_id: str = "" # unique ID for this turn
    user_content: types.Content # the user's message for this turn
    final_response: Optional[types.Content] = None # expected agent reply
    intermediate_data: Optional[IntermediateData] = None # expected tool calls/responses
    rubrics: Optional[list[Rubric]] = None # per-turn scoring rubrics (Rubric from eval_rubrics.py)
    creation_timestamp: float = 0.0
```

### IntermediateData — Expected Tool Calls and Responses

```python
class IntermediateData(BaseModel):
    tool_uses: list[FunctionCall] # expected tool calls (google.genai.types.FunctionCall)
    tool_responses: list[FunctionResponse] # expected tool responses
    intermediate_responses: list[tuple[str, list[types.Part]]] = [] # (author, parts) tuples
```

### EvalSet — A Suite of Cases

```python
class EvalSet(BaseModel):
    eval_set_id: str
    name: Optional[str] = None # human-readable name
    description: Optional[str] = None
    eval_cases: list[EvalCase]
    creation_timestamp: float = 0.0
```

### EvalMetric — What to Measure

```python
class EvalMetric(BaseModel):
    metric_name: str # e.g. "tool_trajectory_avg_score", "response_match_score"
    threshold: Optional[float] = None # deprecated — use criterion instead
    criterion: Optional[BaseCriterion] = None # evaluation criterion (BaseCriterion or subclass)
    custom_function_path: Optional[str] = None # dotted path to custom metric function

class PrebuiltMetrics(Enum): # 12 built-in metrics
    TOOL_TRAJECTORY_AVG_SCORE = "tool_trajectory_avg_score"
    RESPONSE_EVALUATION_SCORE = "response_evaluation_score"
    RESPONSE_MATCH_SCORE = "response_match_score"
    SAFETY_V1 = "safety_v1"
    FINAL_RESPONSE_MATCH_V2 = "final_response_match_v2"
    RUBRIC_BASED_FINAL_RESPONSE_QUALITY_V1 = "rubric_based_final_response_quality_v1"
    HALLUCINATIONS_V1 = "hallucinations_v1"
    RUBRIC_BASED_TOOL_USE_QUALITY_V1 = "rubric_based_tool_use_quality_v1"
    PER_TURN_USER_SIMULATOR_QUALITY_V1 = "per_turn_user_simulator_quality_v1"
    MULTI_TURN_TASK_SUCCESS_V1 = "multi_turn_task_success_v1"
    MULTI_TURN_TRAJECTORY_QUALITY_V1 = "multi_turn_trajectory_quality_v1"
    MULTI_TURN_TOOL_USE_QUALITY_V1 = "multi_turn_tool_use_quality_v1"
```

### EvalCaseResult — What You Get Back

```python
class EvalCaseResult(BaseModel):
    eval_set_id: str
    eval_id: str # matches EvalCase.eval_id
    final_eval_status: EvalStatus # PASSED | FAILED | NOT_EVALUATED
    overall_eval_metric_results: list[EvalMetricResult]
    eval_metric_result_per_invocation: list[EvalMetricResultPerInvocation] # per-turn results
    session_id: str # the session used for this run
    session_details: Optional[Session] = None # full Session object after eval
    user_id: Optional[str] = None
```

```python
class EvalMetricResult(EvalMetric): # extends EvalMetric (inherits metric_name, threshold, criterion)
    score: Optional[float] = None # actual score (0.0–1.0), None if not evaluated
    eval_status: EvalStatus # PASSED | FAILED | NOT_EVALUATED
```

---

## How It Works

### AgentEvaluator — Running Evaluations

```
await AgentEvaluator.evaluate()
├── 1. Scan for .test.json files in the given path
├── 2. For each EvalCase:
│   ├── Create Runner + Session
│   ├── Replay conversation invocations
│   └── Collect actual tool calls + responses
├── 3. Score with configured evaluators
└── 4. Assert results internally (raises on failure)
```

`AgentEvaluator` is the main entry point. It scans for `.test.json` files, replays each `EvalCase` against a real agent, scores results, and **asserts internally** — failures raise `AssertionError`.

```python
from google.adk.evaluation import AgentEvaluator

# evaluate() asserts internally; it does NOT return results.
# Default num_runs=2 (runs each case twice for consistency).
await AgentEvaluator.evaluate(
    agent_module="my_package.my_agent", # importable module with 'agent' variable
    eval_dataset_file_path_or_dir="tests/evals/", # directory with .test.json files
    num_runs=2, # default: 2
    agent_name=None, # optional: evaluate a sub-agent instead of root
    initial_session_file=None, # optional: JSON file with initial session state
    print_detailed_results=True, # default: True — print per-invocation details
)
```


### Metrics Deep Dive

#### 1. `tool_trajectory_avg_score`

Scores whether the agent called the right tools in the right order.

Scoring logic:
- Each expected `FunctionCall` is checked against the actual tool calls in sequence
- `tool_name` must match exactly
- `tool_input` is compared if provided (partial match is allowed -- only specified keys are checked)
- Score = (matched steps) / (total expected steps)

Example: if you expect `[search, summarize]` and agent did `[search, translate, summarize]`, score is 1.0 (both expected steps matched, extras don't penalize).

```
Scoring Example — tool_trajectory_avg_score:

Expected: [search_flights, book_flight]
Actual:   [search_flights, get_weather, book_flight]

Step 1: search_flights → found? YES (score: 1)
Step 2: book_flight    → found? YES (score: 1)
Extra:  get_weather    → not penalized (extras are OK)

Final score: (1 + 1) / 2 = 1.0 ← perfect!

If book_flight was MISSING:
Step 2: book_flight → found in actual? NO ✗ (score: 0)
Final score: (1 + 0) / 2 = 0.5
```

#### 2. `response_match_score`

Scores how well the agent's final response matches `reference_answer`.

Uses an LLM judge with a rubric like:
> "Does the candidate response convey the same information and intent as the reference answer? Score 0–5."

The raw score is normalized to 0.0–1.0.

This is a **model-graded** metric — fuzzy by design. Two semantically equivalent phrasings both score high. The LLM judge defaults to Gemini; configurable via `EvalMetric.criterion`.

---

## Examples

### Eval File Format

EvalSets are stored as JSON files with the extension `.test.json`:

```json
{
 "eval_set_id": "weather_agent_evals",
 "name": "Weather Agent Tests",
 "description": "Basic weather query scenarios",
 "eval_cases": [
 {
 "eval_id": "basic_weather_query",
 "creation_timestamp": 1700000000.0,
 "conversation": [
 {
  "invocation_id": "turn_1",
  "user_content": {
  "parts": [{ "text": "What is the weather in Paris?" }],
  "role": "user"
  },
  "final_response": {
  "parts": [{ "text": "The weather in Paris is currently 18°C and partly cloudy." }],
  "role": "model"
  },
  "intermediate_data": {
  "tool_uses": [
   { "name": "get_weather", "args": { "city": "Paris" } }
  ],
  "tool_responses": [
   { "name": "get_weather", "response": { "result": { "temp": "18°C", "condition": "partly cloudy" } } }
  ]
  },
  "creation_timestamp": 1700000000.0
 }
 ]
 }
 ],
 "creation_timestamp": 1700000000.0
}
```

### Running Evals via CLI

```bash
# Run all eval sets in a directory:
adk eval my_agent_module/ tests/evals/

# Run a specific eval set file:
adk eval my_agent_module/ tests/evals/weather.test.json

# Verbose output (shows per-turn tool calls):
adk eval --verbose my_agent_module/ tests/evals/
```

The CLI exits with code 0 if all cases pass, non-zero if any fail -- suitable for CI.

### Running Evals Programmatically (pytest Integration)

Since `AgentEvaluator.evaluate()` asserts internally, the simplest integration is via pytest:

```python
# tests/test_agent_eval.py
import pytest
from google.adk.evaluation import AgentEvaluator

@pytest.mark.asyncio
async def test_weather_agent_evals():
    # evaluate() asserts internally — if any case fails, pytest catches the AssertionError.
    await AgentEvaluator.evaluate(
        agent_module="weather_agent",
        eval_dataset_file_path_or_dir="tests/evals/", # scans for .test.json files
        num_runs=2, # default: runs each case twice
    )
```

Run with: `pytest tests/test_agent_eval.py -v`

No need to inspect return values — `evaluate()` raises on failure, which pytest reports as a test failure.

## Writing Good Eval Cases

**Use empty `args` when argument values are flexible:**
```json
{ "name": "search_web", "args": {} }
```
This checks that the agent *called* the tool without asserting which exact query it used.

**Set `final_response` for open-ended responses, skip it for tool-only cases:**
- If you only care about tool trajectory, set `intermediate_data.tool_uses`, leave `final_response` null
- If you only care about the response content, set `final_response`, leave `intermediate_data` null
- For full coverage, set both

---

## When to Use Evals

### Testing Pyramid for Agents

```
Testing Pyramid for Agents:
│
├── Unit Tests (MockModel)
│      many, fast, cheap
│      "Does my tool return the right data?"
│      "Does my callback fire correctly?"
│
├── Integration Tests (InMemoryRunner + MockModel)
│      some, medium speed
│      "Did the right tools get called in order?"
│      "Does the multi-agent pipeline work end-to-end?"
│
└── Evals (real LLM)
       few, slow, expensive
       "Did the agent give a good answer?"
       "Is the response safe and grounded?"
```

### Eval vs Unit Test — When to Use Each

| Scenario | Use |
|---|---|
| Tool function returns correct value | `pytest` unit test |
| Agent calls the right tool | Eval with `tool_trajectory_avg_score` |
| Agent's answer is factually correct | Eval with `response_match_score` |
| Multi-turn conversation flow | Eval with multi-turn `conversation` |
| Callback fires correctly | `pytest` unit test with `AsyncMock` |
| Agent handles ambiguous input gracefully | Eval with `response_match_score` |

### Java Comparison

| Java concept | ADK equivalent |
|---|---|
| JUnit `@Test` | `EvalCase` |
| Test suite (`@Suite`) | `EvalSet` / `.test.json` |
| AssertJ / Hamcrest matchers | `EvalMetric` thresholds |
| Integration test | Multi-turn `EvalCase` with tool trajectory |
| Contract test | `tool_trajectory_avg_score` (verifies tool API usage) |
| Snapshot test | `response_match_score` with fixed `reference_answer` |

---

## Related

- [`evaluation/eval_case.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/eval_case.py) — EvalCase, Invocation, IntermediateData
- [`evaluation/eval_set.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/eval_set.py) — EvalSet, EvalMetric
- [`evaluation/agent_evaluator.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/agent_evaluator.py) — main entry point
- [`evaluation/evaluator.py`](https://github.com/google/adk-python/blob/main/src/google/adk/evaluation/evaluator.py) — Evaluator, metric implementations
- [`python-testing-and-mocking-guide.md`](../python/python-testing-and-mocking-guide.md) — unit testing with pytest/AsyncMock
- [`09-tools.md`](./09-tools.md) — tool system (what evals are testing)
- [`02-when-to-build-what.md`](./02-when-to-build-what.md) — decision guide including when to write evals
