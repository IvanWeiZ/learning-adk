# Learning ADK — Source-Traced Deep Dives for Google's Agent Development Kit

[![CI](https://github.com/IvanWeiZ/learning-adk/actions/workflows/ci.yml/badge.svg)](https://github.com/IvanWeiZ/learning-adk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ADK Version](https://img.shields.io/badge/ADK-v1.27.2-blue)](https://github.com/google/adk-python)

> **Not the official docs.** For API reference and tutorials, see [google.github.io/adk-docs](https://google.github.io/adk-docs/).
>
> These notes go deeper: every claim is traced to a specific line in the [ADK source code](https://github.com/google/adk-python). They cover the internals, gotchas, and patterns that the official docs don't.

## What's Inside

| This repo covers | Official docs typically don't |
|---|---|
| Full request lifecycle traced through source | Just shows the API call |
| `append_event` internals, state delta mechanics | Just says "state is persisted" |
| Flow selection logic (3 conditions for SingleFlow) | Just says "ADK handles routing" |
| Branch filtering rules for multi-agent history | Not documented |
| Agent transfer mechanics (`_get_transfer_targets`) | Just says "agents can transfer" |
| Processor pipeline ordering (12 request + 3 response) | Not exposed |
| Error paths, silent failures, recovery points | Only happy path |
| Concurrency gotchas (last-writer-wins, locking) | Not covered |

## Quick Start

**New to ADK?** Start here:

1. Read [00-onboarding-guide.md](adk/00-onboarding-guide.md) — build your first agent in 5 lines
2. Read [01-request-lifecycle.md](adk/01-request-lifecycle.md) — trace what happens inside
3. Pick a topic from the reading order below

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User / CLI / API                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Runner ─── session bookkeeping, event streaming, compaction    │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│  Agents                  │    │  Sessions                       │
│  LlmAgent, LoopAgent,   │◄──►│  InMemory, SQLite, Database,    │
│  ParallelAgent,          │    │  Vertex AI                      │
│  SequentialAgent         │    │                                 │
└──────────────┬───────────┘    └─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Flow ─── reason-act loop: preprocess → LLM → tools → repeat   │
└──────────────┬─────────────────────────────┬────────────────────┘
               │                             │
               ▼                             ▼
┌──────────────────────────┐    ┌────────────────────────────────┐
│  Models                  │    │  Tools                         │
│  Gemini, Anthropic,      │    │  FunctionTool, MCP, OpenAPI,   │
│  LiteLLM (100+)          │    │  LangChain, CrewAI, 50+ more  │
└──────────────────────────┘    └────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Events ─── the universal data type flowing through everything  │
└─────────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────┬──────────────┬──────────────┬────────────────────┐
│  Memory      │  Artifacts   │  Auth        │  Telemetry         │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

## Reading Order

### Start Here

| # | File | What You Learn |
|---|------|---------------|
| 0 | [00-onboarding-guide.md](adk/00-onboarding-guide.md) | **Zero to first agent** — an agent is just prompt + model + tools |

### Part 1: The Big Picture

| # | File | What You Learn |
|---|------|---------------|
| 1 | [01-request-lifecycle.md](adk/01-request-lifecycle.md) | Full traced request through every layer — the mental model |
| 2 | [02-when-to-build-what.md](adk/02-when-to-build-what.md) | Decision guide: scenario → ADK component |

### Part 2: Core Layers

| # | File | Layer |
|---|------|-------|
| 3 | [03-runners.md](adk/03-runners.md) | Entry point — session fetch, context setup, event streaming |
| 4 | [04-agents.md](adk/04-agents.md) | Agent types, callbacks, transfer mechanics |
| 5 | [05-flows.md](adk/05-flows.md) | The reason-act loop inside agents |
| 6 | [06-models.md](adk/06-models.md) | LLM adapters (Gemini, Anthropic, LiteLLM) |
| 7 | [07-events.md](adk/07-events.md) | The universal data type flowing through everything |
| 8 | [08-sessions.md](adk/08-sessions.md) | State persistence, session backends |
| 9 | [09-tools.md](adk/09-tools.md) | Tool system, MCP, ToolContext |

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
| 21 | [21-advanced-patterns.md](adk/21-advanced-patterns.md) | YAML configs, ReflectAndRetry, triage gates |
| 22 | [22-testing.md](adk/22-testing.md) | MockModel, deterministic testing, pytest patterns |
| 23 | [23-advanced-internals.md](adk/23-advanced-internals.md) | Processor pipeline, plugins, A2A internals |

### Part 6: Reference

| # | File | What It Covers |
|---|------|---------------|
| 24 | [24-faq.md](adk/24-faq.md) | Tool versioning, state scoping, agent messaging |
| 25 | [25-adk-2.0-preview.md](adk/25-adk-2.0-preview.md) | ADK 2.0: graph workflows, collaborative agents |

### Python Guides

For developers coming from Java or other languages:

| File | Topic |
|------|-------|
| [python-for-adk-learning-plan.md](python/python-for-adk-learning-plan.md) | 2-week curriculum: Python fundamentals → ADK patterns |
| [python-asyncio-deep-dive.md](python/python-asyncio-deep-dive.md) | async/await, event loop, AsyncGenerator |
| [python-decorators-deep-dive.md](python/python-decorators-metaprogramming-deep-dive.md) | Decorators, ABCs, descriptors, metaclasses |
| [python-pydantic-deep-dive.md](python/python-pydantic-deep-dive.md) | Pydantic v2: BaseModel, validators, serialization |
| [python-testing-guide.md](python/python-testing-and-mocking-guide.md) | pytest, AsyncMock, fixtures, mocking strategies |

### Quick Reference

| File | Topic |
|------|-------|
| [glossary.md](reference/glossary.md) | ADK terminology |
| [java-to-python-cheat-sheet.md](reference/java-to-python-cheat-sheet.md) | Side-by-side Java → Python mappings |

## Key Architectural Patterns

Six patterns that appear throughout ADK:

1. **Async-First** — every agent produces an `AsyncGenerator[Event, None]`
2. **Context Threading** — `InvocationContext` carries session, state, and credentials through every call
3. **Adapter/Strategy** — `BaseLlm`, `BaseSessionService`, `BaseTool` define contracts; multiple implementations exist
4. **Hook/Callback** — `before_agent`, `before_model`, `before_tool` + after/error variants at every layer
5. **Pipeline/Processor** — `BaseLlmFlow` runs 12 request processors and 3 response processors in order
6. **Event-Driven Side Effects** — state mutations, transfers, and escalations are carried in `EventActions`, not via direct calls

## Example Agents

100+ working examples in the ADK repo: [`contributing/samples/`](https://github.com/google/adk-python/tree/main/contributing/samples/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on fixing errors, adding content, and diagram style.

## License

[MIT](LICENSE)
