# Flows — The Reason-Act Loop

> **Official docs:** [Flows](https://google.github.io/adk-docs/runtime/flows/) | **Source:** [`base_llm_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/base_llm_flow.py) · [`single_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/single_flow.py) · [`auto_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/auto_flow.py) | **Prereqs:** [04-agents.md](04-agents.md)

---

## What It Is

`BaseLlmFlow` implements the core **reason-act loop**. `LlmAgent` selects and assigns the flow at construction time based on its configuration, then `_run_async_impl` delegates to `self._llm_flow.run_async(ctx)`.

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

`AutoFlow` extends `SingleFlow` — it adds the `agent_transfer.py` response processor on top of the basic loop. See [04-agents.md](04-agents.md) for the full flow selection logic and [23-advanced-internals.md](23-advanced-internals.md) for the complete processor pipeline.

---

## Loop Iteration Flowchart

```
BaseLlmFlow Loop
│
├─ 1. PREPROCESS
│     build LlmRequest from session.events (history + tools)
│
├─ 2. CALL LLM
│     model.generate_content_async(request, stream=...)
│
├─ 3. CHECK RESPONSE
│     ├─ Has function calls? → execute tool(s) → loop back to step 1
│     ├─ Agent transfer?     → delegate to target agent → exit
│     └─ Final text?         → yield Event → exit
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

## Processors

The flow runs **request processors** (build `LlmRequest`) before each LLM call, and **response processors** (dispatch tools, handle transfers) after. Key processors: `instructions.py` (system prompt), `contents.py` (history), `functions.py` (tool definitions + tool dispatch), `agent_transfer.py` (routing in AutoFlow).

For the complete processor pipeline with all 12 processors, see [23-advanced-internals.md](23-advanced-internals.md).

---

## Tool Execution Inside the Flow

When the LLM returns a function call:

```
LLM returns FunctionCall(name='search', args={'query': 'ADK'})
 1. functions.py finds the matching BaseTool by name
 2. Runs before_tool_callback (can skip execution)
 3. tool.run_async(args=..., tool_context=...)
 4. Runs after_tool_callback (can replace result)
 5. Creates Event(author=agent.name, content=[FunctionResponse(...)])
 6. Appends to session, yields event
 7. Flow loops back — LLM gets the tool result and continues reasoning
```

---

## Example

A tool-use turn through the flow — the loop runs twice (tool call, then final answer):

```python
async for event in runner.run_async(
    user_id="user1",
    session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text="What's the weather in Tokyo?")]),
):
    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.function_call:
                print(f"Tool call: {part.function_call.name}({part.function_call.args})")
            elif part.text:
                print(f"Response: {part.text}")
```

---

## Related

- [`flows/llm_flows/base_llm_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/base_llm_flow.py) — the loop
- [`flows/llm_flows/single_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/single_flow.py) — no-routing variant
- [`flows/llm_flows/auto_flow.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/auto_flow.py) — agent-transfer variant
- [`flows/llm_flows/instructions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/instructions.py) — system prompt building
- [`flows/llm_flows/contents.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/contents.py) — history building
- [`flows/llm_flows/functions.py`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/llm_flows/functions.py) — tool dispatch
