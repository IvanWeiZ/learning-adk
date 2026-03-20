# 02 — When to Build What in ADK

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [`tools/`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/) · [`agents/`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/) · [`plugins/`](https://github.com/google/adk-python/blob/main/src/google/adk/plugins/) · [`flows/`](https://github.com/google/adk-python/blob/main/src/google/adk/flows/) | **Prereqs:** [01-request-lifecycle.md](01-request-lifecycle.md)

## At a Glance (big-picture diagram first, then one paragraph)

```
What are you trying to do?
│
├─ Add a capability to an agent?
│  ├─ Simple function               ► FunctionTool (auto-wrapped)
│  ├─ Needs lifecycle hooks          ► BaseTool subclass
│  ├─ Dynamic set of tools           ► BaseToolset
│  ├─ External API with auth         ► AuthenticatedFunctionTool
│  └─ Long-running / async           ► LongRunningFunctionTool
│
├─ Compose multiple agents?
│  ├─ LLM picks which agent          ► LlmAgent(sub_agents=[...]) (AutoFlow)
│  ├─ Fixed sequence                 ► SequentialAgent
│  ├─ Run in parallel                ► ParallelAgent
│  ├─ Repeat until done              ► LoopAgent
│  └─ Call a remote agent            ► RemoteA2aAgent (as sub_agent)
│
├─ Add cross-cutting behavior?
│  ├─ Guard all agents               ► BasePlugin (on App)
│  ├─ Guard one agent                ► before/after_agent_callback
│  ├─ Intercept LLM calls            ► before/after_model_callback
│  └─ Intercept tool calls           ► before/after_tool_callback
│
├─ Use a non-Gemini model?
│  ├─ OpenAI, Groq, etc.             ► LiteLlm ("provider/model")
│  ├─ Claude                         ► AnthropicLlm ("claude-*")
│  └─ Custom model                   ► BaseLlm subclass + LLMRegistry
│
├─ Stream to a web UI?
│  └─ RunConfig(streaming_mode=StreamingMode.SSE)
│
└─ Remember past conversations?
   └─ BaseMemoryService + load_memory_tool
```

Decision guide for every ADK extensibility point: **what**, **when**, **when not**, and **how**. This file maps real-world scenarios to the right ADK component and shows how to build each one.

---

## Key API

### Quick Decision Tree

```
I need to...
│
├─ Do something the LLM can request (call an API, query a DB, run code)
│  ├─ Single function, no setup/teardown          ► Plain function tool
│  ├─ Needs state, complex logic, or is_long_running ► Custom BaseTool subclass
│  └─ Many tools from one source (REST API, MCP)  ► Custom BaseToolset subclass
│
├─ Control HOW a single agent behaves
│  ├─ Before/after the agent runs                 ► before/after_agent_callback
│  ├─ Before/after each LLM call                  ► before/after_model_callback
│  ├─ Before/after each tool call                  ► before/after_tool_callback
│  └─ On LLM or tool errors                       ► on_model/tool_error_callback
│
├─ Control HOW ALL agents behave (app-wide)        ► Plugin
│
├─ Compose multiple agents
│  ├─ Run A, then B, then C in order              ► SequentialAgent
│  ├─ Run A, B, C at the same time                ► ParallelAgent
│  ├─ Repeat until done or N times                ► LoopAgent
│  └─ LLM decides which sub-agent to use          ► LlmAgent with sub_agents
│
├─ Change how an agent THINKS or RESPONDS
│  ├─ Custom reasoning / planning                 ► Custom BasePlanner subclass
│  └─ Run code the LLM generates                  ► BaseCodeExecutor subclass
│
├─ Use a non-Gemini model                          ► LiteLlm adapter or custom BaseLlm
│
├─ Remember past conversations / search knowledge  ► BaseMemoryService + load_memory_tool
│
├─ Stream tokens to a web UI in real-time          ► RunConfig(streaming_mode=SSE) or BIDI
│
├─ Expose / consume agents across services         ► A2A protocol (to_a2a / RemoteA2aAgent)
│
├─ Require user OAuth tokens for a tool            ► AuthenticatedFunctionTool
│
└─ Change where sessions/memory/artifacts are stored ► Custom service backend
```

---

## How It Works (diagram before prose)

### Real-World Use Cases → What to Build

Common scenarios mapped to ADK components.

#### Tools

| Real-world scenario | What to build |
|---------------------|---------------|
| Agent needs to call a weather API | Plain function tool |
| Agent needs to query a PostgreSQL database | Plain function tool |
| Agent needs to send a Slack message | Plain function tool |
| Agent needs to read/write files on disk | Plain function tool |
| Agent needs to search Google | Built-in `google_search` tool (no code needed) |
| Agent needs to call any REST API defined by an OpenAPI spec | `OpenAPIToolset` (no code needed) |
| Agent needs to export a report that takes 5 minutes to generate | `LongRunningFunctionTool` (or `BaseTool` subclass with `is_long_running=True`) |
| Agent needs to trigger a Cloud Run job and wait for the result | `LongRunningFunctionTool` (or `BaseTool` subclass with `is_long_running=True`) |
| Human-in-the-loop approval before executing an action | `LongRunningFunctionTool` — same pause mechanism as long-running tools. Invocation pauses, user's next message carries the approval. |
| Agent needs to execute Python code it generates | `BaseCodeExecutor` subclass. Options: `BuiltInCodeExecutor` (model-native), `ContainerCodeExecutor` (Docker), `UnsafeLocalCodeExecutor` (no isolation), `VertexAiCodeExecutor`, `GkeCodeExecutor`, `AgentEngineSandboxCodeExecutor`. |
| Agent should expose all tools from an MCP server | `McpToolset` (no code needed) |
| Agent should only show certain tools based on user role | `BaseToolset` subclass with `get_tools()` that filters by `ctx.state` |
| Agent connects to a third-party tool platform (LangChain, CrewAI) | `LangchainTool` / `CrewaiTool` wrapper |
| Agent needs to recall past conversations or search knowledge | `BaseMemoryService` + `load_memory_tool`. Three backends: `InMemoryMemoryService` (dev), `VertexAiRagMemoryService` (production vector search), `VertexAiMemoryBankService` (LLM-distilled memory). Wire via `Runner(memory_service=...)`. See [11-memory.md](11-memory.md). |
| Tool needs user OAuth tokens (e.g. Google Drive, GitHub) | `AuthenticatedFunctionTool` wraps any callable with the full OAuth flow. When credentials are missing, the invocation pauses for user authorization. See [13-auth.md](13-auth.md). |
| Multiple independent API calls in one turn | Automatic. When the LLM returns multiple function calls in a single response, ADK runs them concurrently via `asyncio.gather`. No configuration needed. Don't confuse with `ParallelAgent` (concurrent sub-agents across invocations). |

#### Agent Callbacks (single-agent hooks)

| Real-world scenario | What to build |
|---------------------|---------------|
| Block the agent if the user is not authenticated | `before_agent_callback` → return Content if not authed |
| Cache the agent's full response for repeated identical inputs | `before_agent_callback` (check cache) + `after_agent_callback` (write cache) |
| Always append "Disclaimer: AI-generated" to agent replies | `after_agent_callback` → return extra Content |
| Inject today's date into the system prompt before every LLM call | `before_model_callback` → mutate `llm_request` |
| Return a cached LLM response to avoid redundant API calls | `before_model_callback` → return cached `LlmResponse` |
| Log token usage for every LLM call on a specific agent | `after_model_callback` → read `llm_response.usage_metadata` |
| Sanitize PII from LLM output before it reaches the user | `after_model_callback` → return scrubbed `LlmResponse` |
| Show a friendly message when the LLM quota is exceeded | `on_model_error_callback` → return fallback `LlmResponse` |
| Validate tool arguments (e.g. reject SQL with DROP TABLE) | `before_tool_callback` → return error dict if invalid |
| Rate-limit tool calls per user per minute | `before_tool_callback` → check counter in state, return error if exceeded |
| Normalize/clean a tool's return value before the LLM sees it | `after_tool_callback` → return transformed dict |
| Alert on-call when a tool raises an exception | `on_tool_error_callback` → send alert, return fallback dict |

#### Plugins (app-wide hooks)

| Real-world scenario | What to build |
|---------------------|---------------|
| Log every LLM call and token count across all agents | `BasePlugin` with `before/after_model_callback` |
| Add OpenTelemetry tracing spans around every agent and tool call | `BasePlugin` with all `before/after` hooks |
| Block all invocations for users on a deny-list, globally | `BasePlugin` with `before_run_callback` |
| Attach a request ID to every event for distributed tracing | `BasePlugin` with `on_event_callback` |
| Enforce a global system prompt added to every LLM call | `BasePlugin` with `before_model_callback` |
| Clean up DB connections when the server shuts down | `BasePlugin.close()` |

#### Agent Composition

| Real-world scenario | What to build |
|---------------------|---------------|
| Research → Draft → Review pipeline, each step depends on the previous | `SequentialAgent` |
| Summarize 10 documents at once, then merge summaries | `ParallelAgent` → `LlmAgent` synthesizer |
| Run a code-generate → test → fix loop until tests pass | `LoopAgent` with `max_iterations`, sub-agent calls `escalate()` when tests pass |
| Customer support router: billing vs tech vs sales | `LlmAgent` with `sub_agents` (LLM decides routing) |
| Multi-step form wizard (collect name, then address, then payment) | `SequentialAgent` with one `LlmAgent` per step |
| Competitive analysis: run 3 different analyst agents in parallel | `ParallelAgent` with 3 specialized `LlmAgent`s |
| Expose an ADK agent as a remote service for other systems | `to_a2a(agent)` creates a Starlette ASGI app implementing the A2A protocol. |
| Consume a remote agent as a sub-agent | `RemoteA2aAgent(agent_card=...)` as a drop-in `sub_agent`. |

#### Custom Agents

| Real-world scenario | What to build |
|---------------------|---------------|
| Deterministic FAQ bot with no LLM needed | `BaseAgent` subclass with rule-matching logic |
| Wrap a LangGraph graph as an ADK agent | `BaseAgent` subclass that calls the graph in `_run_async_impl` |
| An agent that calls an external orchestration API and streams its events back | `BaseAgent` subclass |
| Use a non-Gemini model (OpenAI, Anthropic, etc.) | `LiteLlm` adapter supports 100+ providers via `'provider/model-name'` format (e.g., `'openai/gpt-4o'`). For fully custom models, subclass `BaseLlm`, implement `generate_content_async()`, and register via `LLMRegistry.register(MyLlm)`. See [06-models.md](06-models.md). |

#### Runtime & Configuration

| Real-world scenario | What to build |
|---------------------|---------------|
| Stream tokens to a web frontend in real-time | `RunConfig(streaming_mode=StreamingMode.SSE)`. Partial events (`event.partial=True`) arrive as LLM generates; final aggregated event follows. For bidirectional audio/video, use `runner.run_live()` with `StreamingMode.BIDI`. |

---

## Examples

### 1–8: Component Examples

See inline code for each component: plain function tools, BaseTool subclass, BaseToolset, agent callbacks, plugins, custom agents, composition agents, and LLM-controlled transfer in [custom-use-cases.md](custom-use-cases.md).

---

## Gotchas

### Summary Table

| What to build | When | Key base class / pattern |
|--------------|------|--------------------------|
| Plain function tool | Simple stateless callable | Python `def` / `async def` |
| Custom tool | Long-running, custom schema, request mutation | `BaseTool` |
| Custom toolset | Dynamic tool set, external source, shared cleanup | `BaseToolset` |
| `before_agent_callback` | Pre-check or short-circuit one specific agent | Inline on `LlmAgent` |
| `after_agent_callback` | Post-process or audit one specific agent | Inline on `LlmAgent` |
| `before_model_callback` | Mutate/cache/guard LLM requests for one agent | Inline on `LlmAgent` |
| `after_model_callback` | Log/replace LLM responses for one agent | Inline on `LlmAgent` |
| `on_model_error_callback` | Recover from LLM errors on one agent | Inline on `LlmAgent` |
| `before_tool_callback` | Validate/gate tool calls on one agent | Inline on `LlmAgent` |
| `after_tool_callback` | Transform tool results on one agent | Inline on `LlmAgent` |
| `on_tool_error_callback` | Recover from tool errors on one agent | Inline on `LlmAgent` |
| Plugin | Any of the above but app-wide, or Runner-level hooks | `BasePlugin` |
| Custom agent | Non-LLM logic, external framework adapter, custom loop | `BaseAgent` |
| `SequentialAgent` | Ordered pipeline | Instantiate directly |
| `ParallelAgent` | Concurrent independent tasks | Instantiate directly |
| `LoopAgent` | Repeat until done | Instantiate directly |
| LLM-routed sub-agents | LLM decides delegation | `LlmAgent(sub_agents=[...])` |
| Memory / RAG | Agent needs past conversations or knowledge search | `BaseMemoryService` + `load_memory_tool` |
| Streaming UI | Real-time token streaming to frontend | `RunConfig(streaming_mode=SSE)` or `BIDI` |
| OAuth-gated tools | Tool requires user authorization | `AuthenticatedFunctionTool` |
| A2A protocol | Expose or consume agents as remote services | `to_a2a()` / `RemoteA2aAgent` |
| Custom model | Non-Gemini LLM provider | `LiteLlm` adapter or `BaseLlm` subclass |
| Parallel tool execution | Multiple independent tool calls in one turn | Automatic (`asyncio.gather`) |
| Human-in-the-loop | Pause for user approval | `LongRunningFunctionTool` |

---

## Related

- [custom-use-cases.md](custom-use-cases.md) — Custom use cases: parse-enrich-respond patterns with three implementation options
- [01-request-lifecycle.md](01-request-lifecycle.md) — Full traced request
- [09-tools.md](09-tools.md) — Tool system reference
- [04-agents.md](04-agents.md) — Agent types deep dive
- [10-apps.md](10-apps.md) — App container and plugins
