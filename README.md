<div align="center">

# Learning ADK

### Go beyond the API surface. Understand what actually happens inside Google's Agent Development Kit.

<br/>

[![CI](https://github.com/IvanWeiZ/learning-adk/actions/workflows/ci.yml/badge.svg)](https://github.com/IvanWeiZ/learning-adk/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ADK Version](https://img.shields.io/badge/ADK-v1.27.2-blue)](https://github.com/google/adk-python)

<br/>

<table>
<tr>
<td align="center"><b>46</b><br/>Deep Dives</td>
<td align="center"><b>21,500+</b><br/>Lines</td>
<td align="center"><b>26</b><br/>ADK Topics</td>
<td align="center"><b>10</b><br/>Python Guides</td>
</tr>
</table>

Every claim traced to a specific line in the [ADK source code](https://github.com/google/adk-python).<br/>
Built from a Java developer's perspective learning Python and ADK from the ground up.

<br/>

[**Get Started**](#-get-started) · [**Reading Order**](#-reading-order) · [**Python Guides**](#-python-guides) · [**Contributing**](CONTRIBUTING.md)

<br/>

---

</div>

## The Problem

You're building agents with ADK. The official docs tell you to call `runner.run_async()` — but not what happens when you do. You hit a bug with state not persisting, agent transfers failing silently, or tools running in the wrong order. The docs just say *"ADK handles it."*

**This repo is the missing manual.** It traces every layer of ADK — from the Runner entry point down to the processor pipeline — so you can debug, extend, and build with confidence.

<table>
<tr>
<td width="50%">

**What you'll find here**

- Full request lifecycle traced through source
- `append_event` internals, state delta mechanics
- Flow selection logic (3 conditions for SingleFlow)
- Branch filtering rules for multi-agent history
- Agent transfer mechanics via `_get_transfer_targets`
- Processor pipeline ordering (12 req + 3 resp)
- Error paths, silent failures, recovery points
- Concurrency gotchas (last-writer-wins, locking)

</td>
<td width="50%">

**What the official docs say instead**

- *"Call `runner.run_async()`"*
- *"State is persisted"*
- *"ADK handles routing"*
- *(not documented)*
- *"Agents can transfer"*
- *(not exposed)*
- *(only happy path)*
- *(not covered)*

</td>
</tr>
</table>

> **This is NOT the official docs.** For API reference: [google.github.io/adk-docs](https://google.github.io/adk-docs/) · For working code: [134 ADK samples](https://github.com/google/adk-python/tree/main/contributing/samples/)

---

## 🚀 Get Started

> **Who this is for:** Developers (especially those coming from Java) who want to understand ADK internals, not just the API surface.

| Step | File | What You'll Learn |
|:----:|------|-------------------|
| **1** | [**00 — Onboarding Guide**](adk/00-onboarding-guide.md) | Build your first agent in 5 lines |
| **2** | [**01 — Request Lifecycle**](adk/01-request-lifecycle.md) | Trace exactly what happens inside |
| **3** | [**02 — When to Build What**](adk/02-when-to-build-what.md) | Pick the right component for your use case |
| **4** | [**Glossary**](reference/glossary.md) | Keep open for unfamiliar terms |

---

## 🏗 Architecture

```
User ──► Runner ──► Agent ──► Flow ──► LLM + Tools ──► Events
            │                                              │
            └──────── Session (state + history) ◄──────────┘
```

<table>
<tr>
<td width="33%">

**Entry & Orchestration**
- **Runner** — session bookkeeping, event streaming, compaction
- **Agents** — LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
- **Flow** — reason-act loop: preprocess → LLM → tools → repeat

</td>
<td width="33%">

**Models & Tools**
- **Models** — Gemini, Anthropic, LiteLLM (100+ providers)
- **Tools** — FunctionTool, MCP, OpenAPI, LangChain, CrewAI, 50+ more
- **Events** — the universal data type flowing through everything

</td>
<td width="33%">

**State & Services**
- **Sessions** — InMemory, SQLite, Database, Vertex AI
- **Memory** — cross-session recall, RAG
- **Auth, Artifacts, Telemetry** — cross-cutting services

</td>
</tr>
</table>

<details>
<summary><b>Six architectural patterns that appear everywhere in ADK</b></summary>
<br/>

| Pattern | How ADK Uses It |
|---------|----------------|
| **Async-First** | Every agent produces an `AsyncGenerator[Event, None]` |
| **Context Threading** | `InvocationContext` carries session, state, credentials through every call |
| **Adapter / Strategy** | `BaseLlm`, `BaseSessionService`, `BaseTool` — one interface, many implementations |
| **Hook / Callback** | `before_agent`, `before_model`, `before_tool` + after/error variants at every layer |
| **Pipeline / Processor** | `BaseLlmFlow` runs 12 request processors + 3 response processors in order |
| **Event-Driven Side Effects** | State mutations, transfers, escalations carried in `EventActions`, not direct calls |

</details>

---

## 📖 Reading Order

### Part 1 — The Big Picture

| # | File | What You Learn |
|:-:|------|---------------|
| 0 | [00-onboarding-guide.md](adk/00-onboarding-guide.md) | **Zero to first agent** — an agent is just prompt + model + tools |
| 1 | [01-request-lifecycle.md](adk/01-request-lifecycle.md) | Full traced request through every layer — the mental model |
| 2 | [02-when-to-build-what.md](adk/02-when-to-build-what.md) | Decision guide: scenario → ADK component |
| | [24b-custom-use-cases.md](adk/24b-custom-use-cases.md) | Component code examples |

### Part 2 — Core Layers

| # | File | Layer |
|:-:|------|-------|
| 3 | [03-runners.md](adk/03-runners.md) | Entry point — session fetch, context setup, event streaming |
| 4 | [04-agents.md](adk/04-agents.md) | Agent types, callbacks, transfer mechanics |
| 5 | [05-flows.md](adk/05-flows.md) | The reason-act loop inside agents |
| 6 | [06-models.md](adk/06-models.md) | LLM adapters (Gemini, Anthropic, LiteLLM) |
| 7 | [07-events.md](adk/07-events.md) | The universal data type flowing through everything |
| 8 | [08-sessions.md](adk/08-sessions.md) | State persistence, session backends |
| 9 | [09-tools.md](adk/09-tools.md) | Tool system, MCP, ToolContext |

### Part 3 — Extended Capabilities

| # | File | What It Adds |
|:-:|------|-------------|
| 10 | [10-apps.md](adk/10-apps.md) | App container, plugins, compaction |
| 11 | [11-memory.md](adk/11-memory.md) | Cross-session recall, RAG |
| 12 | [12-artifacts.md](adk/12-artifacts.md) | Binary file storage |
| 13 | [13-auth.md](adk/13-auth.md) | OAuth, credential management |
| 14 | [14-planners.md](adk/14-planners.md) | Thinking mode, plan-then-act |
| 15 | [15-evaluation.md](adk/15-evaluation.md) | Agent quality testing |

<details>
<summary><b>Part 4 — Operations & Safety</b> (5 files)</summary>
<br/>

| # | File | What It Covers |
|:-:|------|---------------|
| 16 | [16-error-reference.md](adk/16-error-reference.md) | Every error path, recovery points, silent failures |
| 17 | [17-concurrency.md](adk/17-concurrency.md) | Thread safety, parallel tools, session locking |
| 18 | [18-session-lifecycle.md](adk/18-session-lifecycle.md) | Session service call timeline, latency optimization |
| 19 | [19-session-security.md](adk/19-session-security.md) | Security considerations for session/event data |
| | [19b-security-checklist.md](adk/19b-security-checklist.md) | Audit checklist, threat model, deployment hardening |

</details>

<details>
<summary><b>Part 5 — Patterns & Practices</b> (7 files)</summary>
<br/>

| # | File | What It Covers |
|:-:|------|---------------|
| 20 | [20-best-practices.md](adk/20-best-practices.md) | Anti-patterns, common mistakes, rules |
| | [20b-debugging-guide.md](adk/20b-debugging-guide.md) | Debugging checklist, latency optimization |
| 21 | [21-advanced-patterns.md](adk/21-advanced-patterns.md) | YAML configs, ReflectAndRetry, triage gates |
| 22 | [22-testing.md](adk/22-testing.md) | MockModel, deterministic testing, pytest patterns |
| | [22b-testing-context-setup.md](adk/22b-testing-context-setup.md) | Context setup, ToolContext, InvocationContext fixtures |
| | [22c-testing-examples.md](adk/22c-testing-examples.md) | Test examples for callbacks, plugins, tools |
| 23 | [23-advanced-internals.md](adk/23-advanced-internals.md) | Processor pipeline, reason-act loop |
| | [23b-custom-tools-and-toolsets.md](adk/23b-custom-tools-and-toolsets.md) | Custom tools, toolsets, advanced patterns |

</details>

<details>
<summary><b>Part 6 — Reference & FAQ</b> (2 files)</summary>
<br/>

| # | File | What It Covers |
|:-:|------|---------------|
| 24 | [24-faq.md](adk/24-faq.md) | Tool versioning, state scoping, agent messaging |
| 25 | [25-adk-2.0-preview.md](adk/25-adk-2.0-preview.md) | ADK 2.0: graph workflows, collaborative agents |
| | [25b-adk-2.0-patterns.md](adk/25b-adk-2.0-patterns.md) | Collaborative agents, dynamic workflows, migration |

</details>

---

## 🐍 Python Guides

> For developers coming from Java or other languages — the Python you need to be productive with ADK.

<table>
<tr>
<td width="50%">

**Fundamentals**
| File | Topic |
|------|-------|
| [Learning Plan](python/python-for-adk-learning-plan.md) | 2-week curriculum |
| [Gotchas for Java Devs](python/python-gotchas-for-java-developers.md) | 13 traps that break at runtime |
| [Asyncio Deep Dive](python/python-asyncio-deep-dive.md) | async/await, event loop |
| [Asyncio Advanced](python/python-asyncio-advanced.md) | Primitives, queues, debugging |
| [Decorators](python/python-decorators-deep-dive.md) | Closures, class-based decorators |

</td>
<td width="50%">

**Advanced**
| File | Topic |
|------|-------|
| [Metaprogramming](python/python-metaprogramming-deep-dive.md) | Descriptors, metaclasses |
| [Pydantic Core](python/python-pydantic-deep-dive.md) | BaseModel, validators |
| [Pydantic Advanced](python/python-pydantic-advanced.md) | Generics, JSON schema |
| [Testing](python/python-testing-and-mocking-guide.md) | pytest, Mock, fixtures |
| [Testing Advanced](python/python-testing-advanced.md) | Async testing, ADK patterns |

</td>
</tr>
</table>

**Quick reference:** [Glossary](reference/glossary.md) · [Java → Python Cheat Sheet](reference/java-to-python-cheat-sheet.md)

---

<div align="center">

## 🤝 Contributing

Found an error? Want to add a deep dive? See [CONTRIBUTING.md](CONTRIBUTING.md).

Every claim should be traceable to the [ADK source](https://github.com/google/adk-python). That's what makes this repo different.

<br/>

**If this helped you understand ADK better, consider giving it a ⭐**

<br/>

[MIT License](LICENSE)

</div>
