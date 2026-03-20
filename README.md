# ADK Python — Learning Notes

> **Official docs:** [google.github.io/adk-docs](https://google.github.io/adk-docs/) — API reference, tutorials, samples
> **Source code:** [google/adk-python](https://github.com/google/adk-python) (v1.27.2)
> **Traced against:** commit `15ddf2d` (2026-03-19) — content may drift as ADK evolves

---

## How These Notes Relate to Official Docs

```
Official docs (google.github.io/adk-docs/)
├── WHO: any developer, any background
├── WHAT: how to USE ADK (API surface, tutorials, samples)
├── DEPTH: "call this method to do X"
└── Trust: always up-to-date, canonical API reference

These notes (learning-adk)
├── WHO: Java dev learning Python+ADK internals
├── WHAT: how ADK WORKS INSIDE (source-traced, layer by layer)
├── DEPTH: "this method calls that method at line 458 because..."
└── Trust: point-in-time snapshot, may drift from source
```

These notes are strongest where official docs are weakest:

| This repo covers | Official docs typically don't |
|---|---|
| Full request lifecycle traced through source | Just shows the API call |
| `append_event` internals, state delta mechanics | Just says "state is persisted" |
| Flow selection logic (3 conditions for SingleFlow) | Just says "ADK handles routing" |
| Branch filtering rules for multi-agent history | Not documented |
| `_get_transfer_targets` transfer rules | Just says "agents can transfer" |
| Processor pipeline ordering | Not exposed |
| Error paths, silent failures | Only happy path |
| Concurrency gotchas (last-writer-wins) | Not covered |

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
│  ParallelAgent           │    │  DatabaseSessionService         │
│  SequentialAgent         │    │  VertexAI SessionService        │
│  base_agent.py           │    │                                 │
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
│  Gemini (primary)        │    │  50+ tools: BigQuery, MCP,     │
│  AnthropicLlm            │    │  OpenAPI, LangChain, CrewAI,   │
│  LiteLlm adapter         │    │  code_executors, bash, etc.    │
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

## Reading Order

Start with the big picture, then follow the execution path layer by layer.

### Start Here

| # | File | What You Learn |
|---|------|---------------|
| 0 | [00-onboarding-guide.md](adk/00-onboarding-guide.md) | **Zero to first agent** — hands-on walkthrough, no prior ADK knowledge needed |

### Part 1: The Big Picture

| # | File | What You Learn |
|---|------|---------------|
| 1 | [01-request-lifecycle.md](adk/01-request-lifecycle.md) | Full traced request through every layer — the mental model |
| 2 | [02-when-to-build-what.md](adk/02-when-to-build-what.md) | Decision guide: scenario → ADK component |

### Part 2: Core Layers (in execution order)

| # | File | Layer |
|---|------|-------|
| 3 | [03-runners.md](adk/03-runners.md) | Entry point — session fetch, context setup, event streaming |
| 4 | [04-agents.md](adk/04-agents.md) | Agent types, callbacks, InvocationContext |
| 5 | [05-flows.md](adk/05-flows.md) | The reason-act loop inside agents |
| 6 | [06-models.md](adk/06-models.md) | LLM adapters (Gemini, Anthropic, LiteLLM) |
| 7 | [07-events.md](adk/07-events.md) | The universal data type flowing through everything |
| 8 | [08-sessions.md](adk/08-sessions.md) | State persistence, session backends |
| 9 | [09-tools.md](adk/09-tools.md) | Tool system, ToolContext, function wrapping |

### Part 3: Extended Capabilities

| # | File | What It Adds |
|---|------|-------------|
| 10 | [10-apps.md](adk/10-apps.md) | App container, plugins, compaction |
| 11 | [11-memory.md](adk/11-memory.md) | Cross-session recall, RAG |
| 12 | [12-artifacts.md](adk/12-artifacts.md) | Binary file storage |
| 13 | [13-auth.md](adk/13-auth.md) | OAuth, credential management |
| 14 | [14-planners.md](adk/14-planners.md) | Thinking mode, plan-then-act |
| 15 | [15-evaluation.md](adk/15-evaluation.md) | Agent quality testing |

### Part 4: Operations & Safety

| # | File | What It Covers |
|---|------|---------------|
| 16 | [16-error-reference.md](adk/16-error-reference.md) | Every error path, recovery points, silent failures |
| 17 | [17-concurrency.md](adk/17-concurrency.md) | Thread safety, parallel tools, session locking |
| 18 | [18-session-lifecycle.md](adk/18-session-lifecycle.md) | Session service call timeline, latency optimization |
| 19 | [19-session-security.md](adk/19-session-security.md) | Security considerations for session/event data |

### Part 5: Patterns & Practices

| # | File | What It Covers |
|---|------|---------------|
| 20 | [20-best-practices.md](adk/20-best-practices.md) | Anti-patterns, common mistakes, rules |
| 21 | [21-advanced-patterns.md](adk/21-advanced-patterns.md) | YAML configs, ReflectAndRetry, triage gates, arg mutation |
| 22 | [22-testing.md](adk/22-testing.md) | MockModel, deterministic testing, pytest patterns |
| 23 | [23-advanced-internals.md](adk/23-advanced-internals.md) | Processor pipeline, plugins, A2A, auth flow internals |

### Part 6: Reference

| # | File | What It Covers |
|---|------|---------------|
| 24 | [24-faq.md](adk/24-faq.md) | Tool versioning, state scoping, agent messaging |
| 26 | [25-adk-2.0-preview.md](adk/25-adk-2.0-preview.md) | ADK 2.0: graph workflows, collaborative agents, dynamic workflows |

### Python for Java Developers

| # | File | What It Covers |
|---|------|---------------|
| — | [python-for-adk-learning-plan.md](python-for-adk-learning-plan.md) | 2-week curriculum: Python fundamentals → ADK patterns |
| — | [python-asyncio-deep-dive.md](python-asyncio-deep-dive.md) | async/await, event loop, AsyncGenerator (critical for ADK) |
| — | [python-decorators-metaprogramming-deep-dive.md](python-decorators-metaprogramming-deep-dive.md) | Decorators, ABCs, descriptors, metaclasses |
| — | [python-pydantic-deep-dive.md](python-pydantic-deep-dive.md) | Pydantic v2: BaseModel, validators, serialization |
| — | [python-testing-and-mocking-guide.md](python-testing-and-mocking-guide.md) | pytest, AsyncMock, fixtures, mocking strategies |

### Quick Reference

| # | File | What It Covers |
|---|------|---------------|
| — | [glossary.md](glossary.md) | ADK terminology quick-reference with links |
| — | [java-to-python-cheat-sheet.md](java-to-python-cheat-sheet.md) | Side-by-side Java → Python mappings |

---

## Example Agents

100+ examples live in [`contributing/samples/`](https://github.com/google/adk-python/tree/main/contributing/samples/).
