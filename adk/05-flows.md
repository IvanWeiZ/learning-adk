# Flows — The Reason-Act Loop

**Source:** [`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) · [`flows/llm_flows/single_flow.py`](../adk-python/src/google/adk/flows/llm_flows/single_flow.py) · [`flows/llm_flows/auto_flow.py`](../adk-python/src/google/adk/flows/llm_flows/auto_flow.py)

---

## What It Is

`BaseLlmFlow` implements the core **reason-act loop**. `LlmAgent._run_async_impl` delegates to `self._llm_flow.run_async(ctx)`.

The flow is responsible for:
1. Building the LLM request (history, system prompt, tool definitions)
2. Calling the LLM model adapter
3. Handling the response (stream events, execute tools)
4. Looping until the LLM produces a final text response

Flows are auto-selected. Understanding them helps when debugging transfers or writing custom processors.

---

## Flow Variants

```
BaseLlmFlow (base_llm_flow.py) — abstract, implements the loop
 ├── SingleFlow — no agent routing; pure tool-use loop
 └── AutoFlow — adds agent transfer/delegation support
```

`LlmAgent._llm_flow` selects:
- `SingleFlow` when `disallow_transfer_to_parent=True`, `disallow_transfer_to_peers=True`, and no `sub_agents`
- `AutoFlow` in all other cases (the default)

---

## Loop Iteration Flowchart

```
┌─────────────────────────────────────────────┐
│ BaseLlmFlow Loop │
│ │
│ ┌─────────────┐ │
│ │ preprocess │ ← build LlmRequest │
│ │ (history + │ from session.events │
│ │ tools) │ │
│ └──────┬───────┘ │
│ ▼ │
│ ┌─────────────┐ │
│ │ call LLM │ │
│ └──────┬───────┘ │
│ ▼ │
│ Has function ──── No ──── ► yield │
│ calls? final │
│ │ Event │
│ Yes (EXIT) │
│ ▼ │
│ ┌─────────────┐ │
│ │ execute │ │
│ │ tool(s) │ │
│ └──────┬───────┘ │
│ │ │
│ └──────── loop back ─────────────┘ │
└─────────────────────────────────────────────┘
```

### Two Iterations in Practice

```
User: "What's the weather in Tokyo?"

Iteration 1:
 preprocess → LlmRequest with [user message]
 LLM returns → FunctionCall(get_weather, city="Tokyo")
 execute → get_weather("Tokyo") → {temp: 18, condition: "cloudy"}
 → loop back

Iteration 2:
 preprocess → LlmRequest with [user message + function call + function response]
 LLM returns → "The weather in Tokyo is 18°C and cloudy."
 no function calls → yield final Event → EXIT
```

---

## The Loop in Detail

```
BaseLlmFlow.run_async(ctx)
│
└─ loop until done:
 │
 ├─ PREPROCESS (build LlmRequest)
 │ ├── _preprocess_async(ctx, llm_request)
 │ │ Each registered BaseLlmRequestProcessor runs in order:
 │ │ - instructions.py → inject system prompt + variable substitution
 │ │ - contents.py → inject conversation history (filtered by branch)
 │ │ - functions.py → inject tool definitions from agent.tools
 │ │ - context_cache.py → apply explicit context cache config
 │ │ - output_schema.py → inject response schema (if output_schema set)
 │ └── before_model_callback → can mutate request or short-circuit
 │
 ├─ CALL LLM
 │ ├── _call_llm_async(ctx, llm_request)
 │ │ → model.generate_content_async(llm_request, stream=...)
 │ │ → yields LlmResponse chunks (partial=True ... partial=False)
 │ └── Streaming events yielded as they arrive
 │
 ├─ POSTPROCESS (handle response)
 │ ├── after_model_callback → can replace LlmResponse
 │ ├── _postprocess_async(ctx, llm_response)
 │ │ Each registered BaseLlmResponseProcessor runs:
 │ │ - code_execution.py → run code blocks if code_executor set
 │ │ - functions.py → execute tool calls, append tool response events
 │ │ - agent_transfer.py → handle transfer_to_agent responses (AutoFlow)
 │ └── Yield model response event
 │
 └─ DECIDE: loop again?
 - If function calls were made and handled → loop (tools ran, need LLM to continue)
 - If agent transfer happened → delegate and exit
 - If final text response → exit loop
```

---

## Request Processors (Preprocessors)

Each implements `BaseLlmRequestProcessor`, mutating `LlmRequest` before the model call.

| Processor | What it does |
|-----------|-------------|
| `instructions.py` | Injects `instruction` as system prompt; resolves `{variable}` placeholders from session state |
| `contents.py` | Builds the conversation history from `session.events`, filtered by branch |
| `functions.py` | Adds `FunctionDeclaration` for each tool; handles auth tool injection |
| `context_cache.py` | Applies explicit context cache tokens when configured |
| `output_schema.py` | Injects `response_schema` to force structured JSON output |

---

## Response Processors (Postprocessors)

Each implements `BaseLlmResponseProcessor`.

| Processor | What it does |
|-----------|-------------|
| `functions.py` | Dispatches `FunctionCall`s to the right tool; runs tools; appends function response Events |
| `code_execution.py` | If LLM outputs code blocks and `code_executor` is set, executes them |
| `agent_transfer.py` (AutoFlow) | Intercepts `transfer_to_agent` function calls; routes to the target agent |

---

## Tool Execution Inside the Flow

When the LLM returns a function call:

```
LLM → FunctionCall(name='search', args={'query': 'ADK'})
 → functions.py finds the matching BaseTool by name
 → Runs before_tool_callback (can skip execution)
 → tool.run_async(args=..., tool_context=...)
 → Runs after_tool_callback (can replace result)
 → Creates Event(author=agent.name, content=[FunctionResponse(...)])
 → Appends to session, yields event
 → Flow loops → LLM gets the tool result → continues reasoning
```

---

## Live Mode

`run_live(ctx)` supports Gemini Live API (bidirectional streaming) via `model.connect()` and `LiveRequestQueue`.

---

## Auth Flow

When a tool requires OAuth credentials:
1. Tool calls `tool_context.request_credential(auth_config)`
2. Flow yields an auth request Event with `EventActions.requested_auth_configs`
3. The client (UI/caller) presents the OAuth flow to the user
4. On the next invocation, the credential is available and the tool proceeds

---

## Related Files

- [`flows/llm_flows/base_llm_flow.py`](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) — the loop
- [`flows/llm_flows/single_flow.py`](../adk-python/src/google/adk/flows/llm_flows/single_flow.py) — no-routing variant
- [`flows/llm_flows/auto_flow.py`](../adk-python/src/google/adk/flows/llm_flows/auto_flow.py) — agent-transfer variant
- [`flows/llm_flows/instructions.py`](../adk-python/src/google/adk/flows/llm_flows/instructions.py) — system prompt building
- [`flows/llm_flows/contents.py`](../adk-python/src/google/adk/flows/llm_flows/contents.py) — history building
- [`flows/llm_flows/functions.py`](../adk-python/src/google/adk/flows/llm_flows/functions.py) — tool dispatch
