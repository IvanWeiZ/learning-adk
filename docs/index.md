# Learning ADK

**Go beyond the API surface. Understand what actually happens inside Google's Agent Development Kit.**

| :material-file-document-multiple: **46** Deep Dives | :material-text-long: **21,500+** Lines | :material-robot: **26** ADK Topics | :material-language-python: **10** Python Guides |
|:---:|:---:|:---:|:---:|

Every claim traced to a specific line in the [ADK source code](https://github.com/google/adk-python).
Built from a Java developer's perspective learning Python and ADK from the ground up.

---

## The Problem

You're building agents with ADK. The official docs tell you to call `runner.run_async()` — but not what happens when you do. You hit a bug with state not persisting, agent transfers failing silently, or tools running in the wrong order. The docs just say *"ADK handles it."*

**This site is the missing manual.** It traces every layer of ADK — from the Runner entry point down to the processor pipeline — so you can debug, extend, and build with confidence.

| What you'll find here | What the official docs say instead |
|---|---|
| Full request lifecycle traced through source | *"Call `runner.run_async()`"* |
| `append_event` internals, state delta mechanics | *"State is persisted"* |
| Flow selection logic (3 conditions for SingleFlow) | *"ADK handles routing"* |
| Agent transfer mechanics via `_get_transfer_targets` | *"Agents can transfer"* |
| Processor pipeline ordering (12 req + 3 resp) | *(not exposed)* |
| Error paths, silent failures, recovery points | *(only happy path)* |
| Concurrency gotchas (last-writer-wins, locking) | *(not covered)* |

!!! note "This is NOT the official docs"
    For API reference: [google.github.io/adk-docs](https://google.github.io/adk-docs/) · For working code: [134 ADK samples](https://github.com/google/adk-python/tree/main/contributing/samples/)

---

## Get Started

| Step | File | What You'll Learn |
|:----:|------|-------------------|
| **1** | [**Onboarding Guide**](adk/00-onboarding-guide.md) | Build your first agent in 5 lines |
| **2** | [**Request Lifecycle**](adk/01-request-lifecycle.md) | Trace exactly what happens inside |
| **3** | [**When to Build What**](adk/02-when-to-build-what.md) | Pick the right component for your use case |
| **4** | [**Glossary**](reference/glossary.md) | Keep open for unfamiliar terms |

---

## Architecture

```
User ──► Runner ──► Agent ──► Flow ──► LLM + Tools ──► Events
            │                                              │
            └──────── Session (state + history) ◄──────────┘
```

| Layer | Role |
|-------|------|
| **Entry & Orchestration** | Runner (session bookkeeping, event streaming), Agents (LlmAgent, Loop, Parallel, Sequential), Flow (reason-act loop) |
| **Models & Tools** | Gemini, Anthropic, LiteLLM (100+ providers), FunctionTool, MCP, OpenAPI, 50+ integrations |
| **State & Services** | Sessions (InMemory, SQLite, Database, Vertex AI), Memory (cross-session recall, RAG), Auth, Artifacts, Telemetry |

??? info "Six architectural patterns that appear everywhere in ADK"

    | Pattern | How ADK Uses It |
    |---------|----------------|
    | **Async-First** | Every agent produces an `AsyncGenerator[Event, None]` |
    | **Context Threading** | `InvocationContext` carries session, state, credentials through every call |
    | **Adapter / Strategy** | `BaseLlm`, `BaseSessionService`, `BaseTool` — one interface, many implementations |
    | **Hook / Callback** | `before_agent`, `before_model`, `before_tool` + after/error variants at every layer |
    | **Pipeline / Processor** | `BaseLlmFlow` runs 12 request processors + 3 response processors in order |
    | **Event-Driven Side Effects** | State mutations, transfers, escalations carried in `EventActions`, not direct calls |

---

## Python Guides

For developers coming from Java or other languages — the Python you need to be productive with ADK.

| Fundamentals | Advanced |
|---|---|
| [Learning Plan](python/python-for-adk-learning-plan.md) — 2-week curriculum | [Metaprogramming](python/python-metaprogramming-deep-dive.md) — Descriptors, metaclasses |
| [Gotchas for Java Devs](python/python-gotchas-for-java-developers.md) — 13 traps | [Pydantic Core](python/python-pydantic-deep-dive.md) — BaseModel, validators |
| [Asyncio Deep Dive](python/python-asyncio-deep-dive.md) — async/await | [Pydantic Advanced](python/python-pydantic-advanced.md) — Generics, JSON schema |
| [Asyncio Advanced](python/python-asyncio-advanced.md) — Primitives, queues | [Testing](python/python-testing-and-mocking-guide.md) — pytest, Mock, fixtures |
| [Decorators](python/python-decorators-deep-dive.md) — Closures, class-based | [Testing Advanced](python/python-testing-advanced.md) — Async, ADK patterns |

**Quick reference:** [Glossary](reference/glossary.md) · [Java → Python Cheat Sheet](reference/java-to-python-cheat-sheet.md)
