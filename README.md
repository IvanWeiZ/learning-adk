<div align="center">

# Learning ADK

### The Unofficial Deep Dive into Google's Agent Development Kit

[![CI](https://github.com/IvanWeiZ/learning-adk/actions/workflows/ci.yml/badge.svg)](https://github.com/IvanWeiZ/learning-adk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ADK Version](https://img.shields.io/badge/ADK-v1.27.2-blue)](https://github.com/google/adk-python)
[![Docs](https://img.shields.io/badge/docs-45_files-green)](adk/)
[![Lines](https://img.shields.io/badge/lines-21%2C000%2B-orange)](#)

**The official docs show you the API. This repo shows you what happens underneath.**

Every claim traced to a specific line in the [ADK source code](https://github.com/google/adk-python).<br/>
Built from a Java developer's perspective learning Python and ADK from the ground up.

[Get Started](#-quick-start) · [Reading Order](#-reading-order) · [Contributing](CONTRIBUTING.md)

</div>

---

## Why This Exists

The official ADK docs tell you *what* to call. They don't tell you *what happens when you call it*. This repo fills that gap:

| What you'll find here | What the official docs say instead |
|---|---|
| Full request lifecycle traced through source | "Call `runner.run_async()`" |
| `append_event` internals, state delta mechanics | "State is persisted" |
| Flow selection logic (3 conditions for SingleFlow) | "ADK handles routing" |
| Branch filtering rules for multi-agent history | *(not documented)* |
| Agent transfer mechanics via `_get_transfer_targets` | "Agents can transfer" |
| Processor pipeline ordering (12 request + 3 response) | *(not exposed)* |
| Error paths, silent failures, recovery points | *(only happy path)* |
| Concurrency gotchas (last-writer-wins, locking) | *(not covered)* |

> For the official API reference: [google.github.io/adk-docs](https://google.github.io/adk-docs/) · For working code: [134 ADK samples](https://github.com/google/adk-python/tree/main/contributing/samples/)

---

## 🚀 Quick Start

**Who this is for:** Developers (especially those coming from Java) who want to understand ADK internals, not just the API surface.

```
1. Read 00-onboarding-guide.md  →  Build your first agent in 5 lines
2. Read 01-request-lifecycle.md →  Trace what happens inside
3. Pick a topic below           →  Go as deep as you want
4. Keep glossary.md open        →  For unfamiliar terms
```

| Start here | Then go deeper |
|---|---|
| [00 — Onboarding Guide](adk/00-onboarding-guide.md) | [01 — Request Lifecycle](adk/01-request-lifecycle.md) |

---

## 🏗 Architecture

```
User ──► Runner ──► Agent ──► Flow ──► LLM + Tools ──► Events
            │                                              │
            └──────── Session (state + history) ◄──────────┘
```

| Layer | What It Does |
|-------|-------------|
| **Runner** | Session bookkeeping, event streaming, compaction |
| **Agents** | LlmAgent, LoopAgent, ParallelAgent, SequentialAgent |
| **Flow** | Reason-act loop: preprocess → LLM → tools → repeat |
| **Models** | Gemini, Anthropic, LiteLLM (100+ providers) |
| **Tools** | FunctionTool, MCP, OpenAPI, LangChain, CrewAI, 50+ more |
| **Events** | The universal data type flowing through everything |
| **Sessions** | InMemory, SQLite, Database, Vertex AI |
| **Cross-cutting** | Memory, Artifacts, Auth, Telemetry |

<details>
<summary><b>Six architectural patterns that appear everywhere in ADK</b></summary>

1. **Async-First** — every agent produces an `AsyncGenerator[Event, None]`
2. **Context Threading** — `InvocationContext` carries session, state, and credentials through every call
3. **Adapter/Strategy** — `BaseLlm`, `BaseSessionService`, `BaseTool` define contracts; multiple implementations exist
4. **Hook/Callback** — `before_agent`, `before_model`, `before_tool` + after/error variants at every layer
5. **Pipeline/Processor** — `BaseLlmFlow` runs 12 request processors and 3 response processors in order
6. **Event-Driven Side Effects** — state mutations, transfers, and escalations are carried in `EventActions`, not via direct calls

</details>

---

## 📖 Reading Order

### Part 1: The Big Picture

| # | File | What You Learn |
|---|------|---------------|
| 0 | [00-onboarding-guide.md](adk/00-onboarding-guide.md) | **Zero to first agent** — an agent is just prompt + model + tools |
| 1 | [01-request-lifecycle.md](adk/01-request-lifecycle.md) | Full traced request through every layer — the mental model |
| 2 | [02-when-to-build-what.md](adk/02-when-to-build-what.md) | Decision guide: scenario → ADK component |
| | [custom-use-cases.md](adk/custom-use-cases.md) | Component code examples |

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

<details>
<summary><b>Part 4: Operations & Safety</b></summary>

| # | File | What It Covers |
|---|------|---------------|
| 16 | [16-error-reference.md](adk/16-error-reference.md) | Every error path, recovery points, silent failures |
| 17 | [17-concurrency.md](adk/17-concurrency.md) | Thread safety, parallel tools, session locking |
| 18 | [18-session-lifecycle.md](adk/18-session-lifecycle.md) | Session service call timeline, latency optimization |
| 19 | [19-session-security.md](adk/19-session-security.md) | Security considerations for session/event data |
| | [security-checklist.md](adk/security-checklist.md) | Audit checklist, threat model, deployment hardening |

</details>

<details>
<summary><b>Part 5: Patterns & Practices</b></summary>

| # | File | What It Covers |
|---|------|---------------|
| 20 | [20-best-practices.md](adk/20-best-practices.md) | Anti-patterns, common mistakes, rules |
| | [debugging-guide.md](adk/debugging-guide.md) | Debugging checklist, latency optimization |
| 21 | [21-advanced-patterns.md](adk/21-advanced-patterns.md) | YAML configs, ReflectAndRetry, triage gates |
| 22 | [22-testing.md](adk/22-testing.md) | MockModel, deterministic testing, pytest patterns |
| | [testing-examples.md](adk/testing-examples.md) | Test examples for callbacks, plugins, tools |
| 23 | [23-advanced-internals.md](adk/23-advanced-internals.md) | Processor pipeline, reason-act loop |
| | [plugins-and-a2a.md](adk/plugins-and-a2a.md) | Custom tools, A2A, code executors |

</details>

<details>
<summary><b>Part 6: Reference & FAQ</b></summary>

| # | File | What It Covers |
|---|------|---------------|
| 24 | [24-faq.md](adk/24-faq.md) | Tool versioning, state scoping, agent messaging |
| 25 | [25-adk-2.0-preview.md](adk/25-adk-2.0-preview.md) | ADK 2.0: graph workflows, collaborative agents |

</details>

---

## 🐍 Python Guides

For developers coming from Java or other languages:

| File | Topic |
|------|-------|
| [python-for-adk-learning-plan.md](python/python-for-adk-learning-plan.md) | 2-week curriculum: Python fundamentals → ADK patterns |
| [python-asyncio-deep-dive.md](python/python-asyncio-deep-dive.md) | async/await, event loop, AsyncGenerator |
| [python-asyncio-advanced.md](python/python-asyncio-advanced.md) | Sync primitives, queues, error handling, debugging |
| [python-decorators-deep-dive.md](python/python-decorators-deep-dive.md) | Decorators, closures, class-based decorators |
| [python-metaprogramming-deep-dive.md](python/python-metaprogramming-deep-dive.md) | Descriptors, metaclasses, registry pattern |
| [python-pydantic-deep-dive.md](python/python-pydantic-deep-dive.md) | Pydantic v2: BaseModel, validators, serialization |
| [python-pydantic-advanced.md](python/python-pydantic-advanced.md) | Generics, JSON schema, custom types, performance |
| [python-testing-and-mocking-guide.md](python/python-testing-and-mocking-guide.md) | pytest, Mock, fixtures, mocking strategies |
| [python-testing-advanced.md](python/python-testing-advanced.md) | Async testing, parametrize, ADK patterns |

**Quick reference:** [Glossary](reference/glossary.md) · [Java → Python Cheat Sheet](reference/java-to-python-cheat-sheet.md)

---

## 🤝 Contributing

Found an error? Want to add a deep dive? See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
