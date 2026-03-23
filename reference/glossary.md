# ADK Glossary

Quick-reference for ADK terminology. Terms link to the relevant deep-dive documentation.

---

## A

- **Agent** — A blueprint that defines behavior for processing user requests. ADK provides several agent types: `LlmAgent` (LLM-powered), `SequentialAgent`, `ParallelAgent`, and `LoopAgent`. Agents are stateless blueprints; state lives in the session. → [04-agents.md](../adk/04-agents.md)

- **AgentTool** — A tool that wraps another agent, allowing one agent to call another as a sub-agent without a full agent transfer. The caller retains control of the conversation. → [09-tools.md](../adk/09-tools.md)

- **App** — The top-level container (`google.adk.apps.App`) that wires together a root agent, session service, artifact service, and memory service. Provides plugin hooks and compaction configuration. → [10-apps.md](../adk/10-apps.md)

- **Artifact** — A binary file (image, PDF, CSV, etc.) stored alongside a session. Identified by a filename key and versioned automatically. → [12-artifacts.md](../adk/12-artifacts.md)

- **ArtifactService** — The storage backend for artifacts. Implementations include `InMemoryArtifactService` and `GcsArtifactService`. → [12-artifacts.md](../adk/12-artifacts.md)

- **AsyncGenerator** — The Python type (`AsyncGenerator[Event, None]`) that every agent's `_run_async_impl` returns, enabling streaming event production. → [python-asyncio-deep-dive.md](../python/python-asyncio-deep-dive.md)

- **AutoFlow** — The default LLM flow that loops between model calls and tool execution until the model produces a final text response or an agent transfer occurs. → [05-flows.md](../adk/05-flows.md)

## B

- **BaseAgent** — Abstract base class for all agents. Defines the `_run_async_impl` contract and sub-agent management. Non-LLM agents (Sequential, Parallel, Loop) inherit directly from this. → [04-agents.md](../adk/04-agents.md)

- **BaseLlm** — Abstract adapter interface for language models. Concrete implementations: `GeminiLlm`, `AnthropicLlm`, `LiteLlm`. → [06-models.md](../adk/06-models.md)

- **BaseLlmFlow** — Abstract base for the reason-act loop inside `LlmAgent`. Manages the processor pipeline that builds requests and handles responses. → [05-flows.md](../adk/05-flows.md)

- **BasePlugin** — Abstract base for App-level plugins that hook into cross-cutting concerns (telemetry, logging, guardrails). → [10-apps.md](../adk/10-apps.md), [23-advanced-internals.md](../adk/23-advanced-internals.md)

- **BaseSessionService** — Abstract interface for session persistence. Implementations: `InMemorySessionService`, `DatabaseSessionService`, `VertexAiSessionService`. → [08-sessions.md](../adk/08-sessions.md)

- **BaseTool** — Abstract base class for tools that need lifecycle control beyond simple function wrapping. Override `run_async` to implement custom tool logic. → [09-tools.md](../adk/09-tools.md)

- **BaseToolset** — Abstract base for dynamic tool collections that resolve at runtime (e.g., `McpToolset`, `OpenApiToolset`). → [09-tools.md](../adk/09-tools.md)

## C

- **CallbackContext** — Alias for `ToolContext`. These names are used interchangeably in ADK source; they refer to the same context object. → see: **ToolContext**

- **Callback** — Hook functions on `LlmAgent` that intercept processing at defined points.

- **Context** — Shorthand for `InvocationContext`. See **InvocationContext**. Use to intercept execution without stopping it (log, validate, modify state). Six slots: `before_agent_callback` / `after_agent_callback`, `before_model_callback` / `after_model_callback`, `before_tool_callback` / `after_tool_callback`. Error variants: `on_model_error_callback`, `on_tool_error_callback`. → [04-agents.md](../adk/04-agents.md), [21-advanced-patterns.md](../adk/21-advanced-patterns.md)

- **Compaction** — Automatic summarization of long conversation histories to stay within model context limits. Configured on `App` or at the agent level. → [10-apps.md](../adk/10-apps.md)

- **Content** — A message unit containing one or more `Part` objects (text, function calls, function responses). The building block of conversation history stored in sessions. → [07-events.md](../adk/07-events.md)

- **CredentialService** — Manages OAuth tokens and API keys for tools that require authenticated access to external services. → [13-auth.md](../adk/13-auth.md)

## D

- **DatabaseSessionService** — A persistent session service backed by a SQL database (SQLAlchemy). Suitable for production deployments. → [08-sessions.md](../adk/08-sessions.md), [18-session-lifecycle.md](../adk/18-session-lifecycle.md)

## E

- **Escalate** — A special `EventActions` flag that causes the current agent to yield control back to its parent agent, signaling it cannot handle the request. → contrast: **Transfer** (sibling agent handoff) → [07-events.md](../adk/07-events.md), [04-agents.md](../adk/04-agents.md)

- **Event** — The universal data unit flowing through every ADK layer. Key fields: `author` (str), `branch` (str | None), `content` (Content | None), `actions` (EventActions), `id` (str). Every agent call yields a stream of events. → [07-events.md](../adk/07-events.md)

- **EventActions** — A structured object carried by an `Event` that declares side effects: state mutations (`state_delta`), agent transfers (`transfer_to_agent`), escalations, and artifact operations. → [07-events.md](../adk/07-events.md)

## F

- **Flow** — The reason-act loop inside `LlmAgent`. See `BaseLlmFlow`. The two built-in flows are `SingleFlow` (one model call, no tool loop) and `AutoFlow` (iterative reason-act loop). → [05-flows.md](../adk/05-flows.md)

- **FunctionDeclaration** — The schema object sent to the LLM describing a tool's name, description, and parameter types. ADK auto-generates these from Python function signatures. → [09-tools.md](../adk/09-tools.md), [06-models.md](../adk/06-models.md)

- **FunctionTool** — The most common tool type. Wraps a plain Python function (sync or async) as an ADK tool, automatically generating its `FunctionDeclaration` from the function's type hints and docstring. → [09-tools.md](../adk/09-tools.md)

## G

- **GeminiLlm** — The built-in adapter for Google Gemini models. The default model backend in ADK. → [06-models.md](../adk/06-models.md)

## I

- **InMemorySessionService** — A non-persistent session service that stores sessions in a Python dictionary. Useful for development and testing. → [08-sessions.md](../adk/08-sessions.md)

- **InvocationContext** — The context object threaded through every call in a single `Runner.run_async` invocation. Carries the session, agent reference, credentials, live request queue, and cancellation token. → [01-request-lifecycle.md](../adk/01-request-lifecycle.md), [04-agents.md](../adk/04-agents.md)

## L

- **LlmAgent** — The primary agent type. Wraps an LLM model with instructions, tools, callbacks, and sub-agents. Formerly called just `Agent` in some ADK examples. → [04-agents.md](../adk/04-agents.md)

- **LlmRequest** — The structured request object built by request processors and sent to the model adapter. Contains contents, system instructions, tool declarations, and config. → [05-flows.md](../adk/05-flows.md), [06-models.md](../adk/06-models.md)

- **LlmResponse** — The structured response from the model adapter, containing the model's content (text, function calls) and token usage metadata (input/output counts). → [05-flows.md](../adk/05-flows.md), [06-models.md](../adk/06-models.md)

- **LLMRegistry** — A global registry that maps model name strings (e.g., `"gemini-2.0-flash"`) to the appropriate `BaseLlm` adapter class. → [06-models.md](../adk/06-models.md)

- **LongRunningFunctionTool** — A tool variant for operations that take significant time (API calls, human-in-the-loop). Returns intermediate pending events and resumes when the operation completes. → [09-tools.md](../adk/09-tools.md)

- **LoopAgent** — An orchestration agent that runs its sub-agents repeatedly until an escalation event signals completion. Useful for iterative refinement patterns. → [04-agents.md](../adk/04-agents.md)

## M

- **Memory** — Cross-session recall capability. A `MemoryService` stores and retrieves information across different sessions for the same user or application. → [11-memory.md](../adk/11-memory.md)

- **MemoryService** — The abstract interface for memory backends. Implementations include `InMemoryMemoryService` and `VertexAiMemoryBankService`. → [11-memory.md](../adk/11-memory.md)

- **MockModel** — A test utility that replaces a real LLM with predetermined responses, enabling deterministic agent testing without API calls. → [22-testing.md](../adk/22-testing.md)

## O

- **Output key** — A state key (e.g., `state["output"]`) where an agent's final response is stored. Useful in `SequentialAgent` pipelines for passing results between sub-agents. → [04-agents.md](../adk/04-agents.md), [08-sessions.md](../adk/08-sessions.md)

- **Output schema** — A Pydantic model or JSON schema dict (e.g., `Model.model_json_schema()`) that constrains the LLM's final response to a structured format. Set via `LlmAgent.output_schema`. → different from **Output key** (processor-specific storage key) → [04-agents.md](../adk/04-agents.md), [python-pydantic-deep-dive.md](../python/python-pydantic-deep-dive.md)

## P

- **ParallelAgent** — An orchestration agent that runs all its sub-agents concurrently and merges their event streams. → [04-agents.md](../adk/04-agents.md), [17-concurrency.md](../adk/17-concurrency.md)

- **Planner** — An optional component that generates a step-by-step plan before the agent begins acting. Supports "thinking" mode and plan-then-act workflows. → [14-planners.md](../adk/14-planners.md)

- **Plugin** — An App-level extension that hooks into cross-cutting concerns (telemetry, guardrails, logging). See `BasePlugin`. Plugins attach to `App` and receive lifecycle hooks for every invocation. → [10-apps.md](../adk/10-apps.md), [23-advanced-internals.md](../adk/23-advanced-internals.md)

- **Processor** — A pipeline stage inside `BaseLlmFlow`. Request processors build the `LlmRequest`; response processors handle the `LlmResponse`. Examples: `InstructionsProcessor`, `FunctionsProcessor`, `AgentTransferProcessor`. → [05-flows.md](../adk/05-flows.md), [23-advanced-internals.md](../adk/23-advanced-internals.md)

## R

- **ReadonlyContext** — A restricted view of `InvocationContext` passed to callbacks. Provides read access to session state and agent info but prevents direct mutations. State writes go via `EventActions.state_delta`, not direct assignment. → [04-agents.md](../adk/04-agents.md), [09-tools.md](../adk/09-tools.md)

- **Runner** — The stateless orchestrator that drives an invocation: fetches/creates a session, delegates to the root agent, collects events, and persists the updated session. Entry point for all ADK interactions. → [03-runners.md](../adk/03-runners.md), [01-request-lifecycle.md](../adk/01-request-lifecycle.md)

## S

- **SequentialAgent** — An orchestration agent that runs its sub-agents one after another in declared order. Each sub-agent can read state set by previous sub-agents. → [04-agents.md](../adk/04-agents.md)

- **Session** — The conversation container holding message history (`events`), state dictionary, and metadata (user ID, session ID). Managed by a `SessionService`. → [08-sessions.md](../adk/08-sessions.md), [18-session-lifecycle.md](../adk/18-session-lifecycle.md)

- **SessionService** — The persistence layer for sessions. See `BaseSessionService`. Implementations: `InMemorySessionService`, `DatabaseSessionService`, `VertexAiSessionService`. → [08-sessions.md](../adk/08-sessions.md)

- **SingleFlow** — A flow that makes exactly one model call with no tool execution loop. Useful for classification, summarization, or structured extraction tasks. → [05-flows.md](../adk/05-flows.md)

- **State (scoped)** — Key-value data attached to a session. Three scopes: **session state** (`state["key"]`) — current session only; **user state** (`state["user:key"]`) — shared across sessions for a user; **app state** (`state["app:key"]`) — shared across all sessions. → [08-sessions.md](../adk/08-sessions.md), [24-faq.md](../adk/24-faq.md)

- **StateDelta** — A dictionary of state changes carried in `EventActions`. Applied to the session when the event is committed. Enables event-sourced state management. → see: **State (scoped)** for scope prefix semantics → [07-events.md](../adk/07-events.md), [08-sessions.md](../adk/08-sessions.md)

## T

- **Tool** — Any callable capability exposed to an LLM agent. ADK's tool hierarchy: `BaseTool` > `FunctionTool`, `AgentTool`, `LongRunningFunctionTool`. Tools are declared on `LlmAgent` or provided by a `BaseToolset`. → [09-tools.md](../adk/09-tools.md), [02-when-to-build-what.md](../adk/02-when-to-build-what.md)

- **ToolContext** — The context object passed to tool functions at execution time. Extends `ReadonlyContext` with methods for state mutation, artifact access, and requesting auth credentials. → [09-tools.md](../adk/09-tools.md)

- **Toolset** — A dynamic collection of tools resolved at invocation time. See `BaseToolset`. → [09-tools.md](../adk/09-tools.md)

- **Transfer (agent transfer)** — When one agent hands off the conversation to a sibling agent by setting `EventActions.transfer_to_agent`. The runner re-routes subsequent processing to the target agent. → [07-events.md](../adk/07-events.md), [04-agents.md](../adk/04-agents.md), [21-advanced-patterns.md](../adk/21-advanced-patterns.md)

## V

- **VertexAiSessionService** — A production session service backed by Vertex AI infrastructure. Provides managed persistence without self-hosted databases. → [08-sessions.md](../adk/08-sessions.md)

- **VertexAiRagMemoryService** — A memory service implementation that uses Vertex AI RAG (Retrieval-Augmented Generation) for cross-session recall. → [11-memory.md](../adk/11-memory.md)

## Y

- **YAML agent config** — An alternative way to define agents declaratively in YAML files rather than Python code. Supports tools, sub-agents, and instructions. → [21-advanced-patterns.md](../adk/21-advanced-patterns.md)

---

> **Note:** Letters J, K, N, Q, U, W, X, Z have no entries yet. Terms added as documentation grows.

See also: [Architecture overview](../README.md) | [01-request-lifecycle.md](../adk/01-request-lifecycle.md) for a full traced request | [02-when-to-build-what.md](../adk/02-when-to-build-what.md) for decision guide
