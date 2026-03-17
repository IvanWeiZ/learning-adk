# ADK Python — Learning Notes

Codebase: [`~/Documents/adk-python`](../adk-python)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        User / CLI / API                         │
│                    cli/ · fast_api.py · a2a/                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ new_message
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         runners.py                              │
│  1. fetch/create Session   2. build InvocationContext           │
│  3. call agent.run_async() 4. stream Events back                │
│  5. compact events (optional)                                   │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│       agents/            │    │          sessions/              │
│  LlmAgent (primary)      │    │  Session (data model)           │
│  LoopAgent               │◄──►│  InMemorySessionService         │
│  ParallelAgent           │    │  SQLiteSessionService           │
│  SequentialAgent         │    │  DatabaseSessionService         │
│  base_agent.py           │    │  VertexAI SessionService        │
└──────────────┬───────────┘    └─────────────────────────────────┘
               │ run_async()
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     flows/llm_flows/                            │
│  BaseLlmFlow.run_async() — the reason-act loop:                 │
│    preprocess → call LLM → postprocess → repeat if tool calls   │
└──────────────┬─────────────────────────────┬────────────────────┘
               │                             │
               ▼                             ▼
┌──────────────────────────┐    ┌────────────────────────────────┐
│        models/           │    │           tools/               │
│  LLMRegistry             │    │  BaseTool / BaseToolset        │
│  GeminiLLM (primary)     │    │  50+ tools: BigQuery, MCP,     │
│  AnthropicLLM            │    │  OpenAPI, LangChain, CrewAI,   │
│  LiteLLM adapter         │    │  code_executors, bash, etc.    │
│  LlmRequest/Response     │    └────────────────────────────────┘
└──────────────────────────┘
               │  all layers emit/share
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          events/                                │
│  Event — the universal unit: user msg, LLM response,           │
│           function call, function response, tool result         │
└─────────────────────────────────────────────────────────────────┘
               │  cross-cutting services
               ▼
┌──────────────┬──────────────┬──────────────┬────────────────────┐
│   memory/    │  artifacts/  │    auth/     │   telemetry/       │
│ (long-term)  │  (files)     │  (OAuth etc) │  (OTel tracing)    │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

---

## Data Flow (one request)

```
Runner → fetch Session
       → create InvocationContext
       → LlmAgent.run_async()
           → BaseLlmFlow loops:
               build LlmRequest (prompt + tools)
               → LLM adapter → LlmResponse
               → if function_calls: execute Tools → append Events
               → if final text: yield Event → done
       → stream Events to caller
       → persist to Session
```

---

## Recommended Reading Order

| # | Deep-Dive Note | Source File | Why |
|---|---------------|-------------|-----|
| 1 | [01-events.md](01-events.md) | [events/event.py](../adk-python/src/google/adk/events/event.py) | Core data type — everything is an Event |
| 2 | [02-agents.md](02-agents.md) | [agents/base_agent.py](../adk-python/src/google/adk/agents/base_agent.py) | Abstract agent contract |
| 3 | [02-agents.md](02-agents.md) | [agents/llm_agent.py](../adk-python/src/google/adk/agents/llm_agent.py) | Primary agent — most complex, most used |
| 4 | [03-runners.md](03-runners.md) | [runners.py](../adk-python/src/google/adk/runners.py) | Orchestration engine — glues everything together |
| 5 | [04-flows.md](04-flows.md) | [flows/llm_flows/base_llm_flow.py](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py) | The reason-act loop itself |
| 6 | [05-models.md](05-models.md) | [models/base_llm.py](../adk-python/src/google/adk/models/base_llm.py) | LLM adapter contract |

---

## Module Summaries

### `events/` — The Universal Currency
Every action in ADK produces an `Event`: user messages, LLM responses, tool calls, tool results. Sessions are just ordered lists of Events. Understanding `Event` fields unlocks everything else.

→ [events/event.py](../adk-python/src/google/adk/events/event.py)

---

### `agents/` — Agent Blueprints
- **`LlmAgent`** — the primary class. Wraps an LLM + tools + system prompt. Delegates the reason-act loop to a `BaseLlmFlow`.
- **`LoopAgent`**, **`ParallelAgent`**, **`SequentialAgent`** — composition primitives for multi-agent hierarchies.
- **`InvocationContext`** — the shared context object threaded through every layer during one request.

→ [agents/base_agent.py](../adk-python/src/google/adk/agents/base_agent.py)
→ [agents/llm_agent.py](../adk-python/src/google/adk/agents/llm_agent.py)
→ [agents/invocation_context.py](../adk-python/src/google/adk/agents/invocation_context.py)

---

### `runners.py` — Stateless Orchestrator
`Runner` owns the outermost lifecycle per invocation. It never holds state — it fetches sessions, creates context, calls the agent, and streams events back. Think of it as the request handler.

→ [runners.py](../adk-python/src/google/adk/runners.py)

---

### `flows/llm_flows/` — The Reason-Act Loop
`BaseLlmFlow.run_async()` drives the inner loop:
1. Build `LlmRequest` (history + system prompt + tool definitions)
2. Call the LLM adapter → stream `LlmResponse`
3. If function calls → execute tools → loop again
4. If final text → yield Event → stop

→ [flows/llm_flows/base_llm_flow.py](../adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py)
→ [flows/llm_flows/single_flow.py](../adk-python/src/google/adk/flows/llm_flows/single_flow.py)

---

### `models/` — LLM Adapters
Thin wrappers over Gemini, Google, Anthropic, and LiteLLM. `LLMRegistry` dispatches to the right adapter by model name string. The contract is `generate_content_async(LlmRequest) → AsyncIterator[LlmResponse]`.

→ [models/base_llm.py](../adk-python/src/google/adk/models/base_llm.py)
→ [models/registry.py](../adk-python/src/google/adk/models/registry.py)
→ [models/gemini_llm.py](../adk-python/src/google/adk/models/gemini_llm.py)

---

### `sessions/` — Conversation History & State
`Session` holds: id, user_id, app_name, a `state` dict (arbitrary key-value), and an ordered list of `Event`s. Service implementations: in-memory (default), SQLite, generic database, Vertex AI managed.

→ [sessions/session.py](../adk-python/src/google/adk/sessions/session.py)
→ [sessions/base_session_service.py](../adk-python/src/google/adk/sessions/base_session_service.py)
→ [sessions/in_memory_session_service.py](../adk-python/src/google/adk/sessions/in_memory_session_service.py)

---

### `tools/` — 50+ Pluggable Tools
Agents declare tools; the LLM requests tool execution by name; `BaseLlmFlow` dispatches to the right `BaseTool.run_async()`. Key tools: Google Search, BigQuery, Bigtable, Spanner, OpenAPI spec tools, MCP, LangChain/CrewAI adapters, code executors.

→ [tools/base_tool.py](../adk-python/src/google/adk/tools/base_tool.py)
→ [tools/base_toolset.py](../adk-python/src/google/adk/tools/base_toolset.py)

---

### `apps/` — High-Level App Container
`App` wraps a root agent with plugins and event compaction config. Use `App` over a bare agent when you need compaction (sliding window summarization), plugins, or context caching.

→ [apps/app.py](../adk-python/src/google/adk/apps/app.py)

---

### Cross-Cutting Services

| Module | Purpose |
|--------|---------|
| [memory/](../adk-python/src/google/adk/memory/) | Long-term memory across sessions |
| [artifacts/](../adk-python/src/google/adk/artifacts/) | File/blob storage per session |
| [auth/](../adk-python/src/google/adk/auth/) | OAuth, API key credential management |
| [telemetry/](../adk-python/src/google/adk/telemetry/) | OpenTelemetry tracing throughout |
| [code_executors/](../adk-python/src/google/adk/code_executors/) | Local, Docker, GKE, Vertex AI sandbox execution |
| [a2a/](../adk-python/src/google/adk/a2a/) | Agent-to-Agent remote protocol |
| [evaluation/](../adk-python/src/google/adk/evaluation/) | Rubric-based eval, EvalSet, EvalCase |

---

## Deep-Dive: Request Lifecycle

[`09-request-lifecycle.md`](09-request-lifecycle.md) — a complete traced walkthrough of one user message through every layer, with exact payload shapes at each step.

---

## New Team Member Guides

| # | Guide | What It Covers |
|---|-------|---------------|
| 1 | [12-onboarding-guide.md](adk/12-onboarding-guide.md) | Zero-to-first-agent walkthrough with diagrams |
| 2 | [13-best-practices.md](adk/13-best-practices.md) | Common mistakes, anti-patterns, debugging checklist |
| 3 | [14-advanced-adk.md](adk/14-advanced-adk.md) | Processor pipeline, plugins, auth, artifacts, A2A |
| 4 | [15-faq.md](adk/15-faq.md) | Tool versioning, testing, state scoping, agent messaging |

---

## Example Agents

100+ examples live in [`contributing/samples/`](../adk-python/contributing/samples/).
