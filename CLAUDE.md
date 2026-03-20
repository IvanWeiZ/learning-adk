# CLAUDE.md — AI Assistant Guide for learning-adk

This file provides context for AI assistants (Claude, Copilot, etc.) working in this repository.

## What This Repository Is

A curated documentation and learning resource for **Google ADK (Agent Development Kit)** — a Python framework for building multi-agent AI systems. The repository contains no runnable source code; all content is Markdown files.

**Primary audience:** Experienced Java developers transitioning to Python and ADK.

**Reference codebase:** `~/Documents/adk-python` (Google ADK source, not included here).

---

## Repository Structure

```
learning-adk/
├── README.md                                      # Architecture overview and reading order
├── adk/
│   ├── 01-request-lifecycle.md                    # Full traced request — the mental model
│   ├── 02-when-to-build-what.md                   # Decision guide: scenario → ADK component
│   ├── 03-runners.md                              # Runner lifecycle (fetch → build → run → persist)
│   ├── 04-agents.md                               # Agent types (LlmAgent, Loop, Parallel, Sequential)
│   ├── 05-flows.md                                # LLM reason-act loop (SingleFlow, AutoFlow)
│   ├── 06-models.md                               # LLM adapters (Gemini, Anthropic, LiteLLM)
│   ├── 07-events.md                               # Event class hierarchy and side-effects
│   ├── 08-sessions.md                             # Session state and storage backends
│   ├── 09-tools.md                                # Tool system (FunctionTool, BaseTool, Toolset)
│   ├── 10-apps.md                                 # App container, plugins, compaction
│   ├── 11-memory.md                               # Cross-session recall, RAG
│   ├── 12-artifacts.md                            # Binary file storage
│   ├── 13-auth.md                                 # OAuth, credential management
│   ├── 14-planners.md                             # Thinking mode, plan-then-act
│   ├── 15-evaluation.md                           # Agent quality testing
│   ├── 16-error-reference.md                      # Error paths, recovery, silent failures
│   ├── 17-concurrency.md                          # Thread safety, parallel tools, locking
│   ├── 18-session-lifecycle.md                    # Session service timeline, optimization
│   ├── 19-session-security.md                     # Security considerations
│   ├── 20-best-practices.md                       # Anti-patterns, common mistakes
│   ├── 21-advanced-patterns.md                    # YAML configs, ReflectAndRetry, triage gates
│   ├── 22-testing.md                              # MockModel, deterministic testing
│   ├── 23-advanced-internals.md                   # Processor pipeline, plugins, A2A internals
│   ├── 24-faq.md                                  # Tool versioning, state scoping
│   └── 25-adk-2.0-preview.md                      # ADK 2.0: graph workflows, collaborative agents
├── python/
│   ├── python-for-adk-learning-plan.md            # 2-week Python curriculum
│   ├── python-asyncio-deep-dive.md                # Async/await patterns
│   ├── python-decorators-metaprogramming-deep-dive.md # Decorators and metaprogramming
│   ├── python-pydantic-deep-dive.md               # Pydantic v2 reference
│   └── python-testing-and-mocking-guide.md        # pytest, AsyncMock, mocking strategies
└── reference/
    ├── glossary.md                                # ADK terminology quick-reference
    └── java-to-python-cheat-sheet.md              # Side-by-side Java → Python mappings
```

**Total:** ~14,000+ lines across 33 Markdown files.

---

## Lessons Learned (Do NOT Repeat These Mistakes)

**Content accuracy:**
1. **Verify class names against source** — `BaseEvaluator` → `Evaluator`. `ConversationTurn`, `ToolUse` don't exist. Always grep before writing.
2. **Verify method signatures** — `run_live(user_id: str)` was wrong (`Optional[str] = None`). `BaseTool.run_async(args, context)` is keyword-only.
3. **Verify field types** — `branch: str` → `Optional[str]`. `custom_metadata: Optional[dict]` → `dict[str, Any] = Field(default_factory=dict)`.
4. **Never invent APIs** — ADK has no `@tool` decorator. `CompactionPlugin` doesn't exist. `App(agent=)` → `App(root_agent=)`.
5. **Mark deprecated APIs** — `save_input_blobs_as_artifacts`, `MCPToolset` are deprecated.
6. **`AgentEvaluator.evaluate()` is async** — must `await`. Returns None, asserts internally.
7. **`ToolContext` = `CallbackContext` = `Context`** — aliases, not subclass relationship.

**Diagram quality:**
8. **No cramped one-liners** — `None → X | Y → Z` is unreadable. Use `if returns None:` on separate lines.
9. **No stacked box separators** (`├───┤`) — use tree style.
10. **No side-by-side boxes** — always vertical tree.
11. **Descriptions on NEXT line** — not on same line as tree node.
12. **Links in code blocks aren't clickable** — use markdown tables.
13. **At a Glance must be compact** (5-10 lines) — not a full architecture walkthrough.
14. **Check box alignment** — edges must match longest content. Test in monospace.
15. **Use real model IDs** — not `claude-sonnet-4-5` or `gemini-pro`.
16. **No opaque IDs as labels** — `evt-002` means nothing. Use "Tool Call", "Final Response".

**User preferences:**
17. **Onboarding = motivation** — under 200 lines. "agent = prompt + model + tools". Don't teach callbacks here.
18. **No Java comparisons in onboarding** — keep those in deep-dive files.
19. **New concepts in Big Picture** — MCP, new capabilities must appear in overview.
20. **Ask about section order** — user changed mind about Examples vs How It Works.

**Process:**
21. **Agents reintroduce checkboxes** — run `perl -pi -e 's/^(#{2,4}) \[ \] /$1 /g'` after every agent.
22. **Agents reintroduce removed content** — verify after every agent completes.
23. **Agents overwrite each other** — never run multiple agents on same file.
24. **Verify content, not just formatting** — read the rendered output, don't just grep.
25. **Verify official doc URLs** — WebFetch every URL before using.
26. **Header format: `Official docs | Source | Prereqs`** — always this order, always on line 3.
27. **When removing content, verify it exists elsewhere** — move before delete.
28. **Fix the pattern, not the instance** — search ALL files for same issue.
29. **Test CI locally before pushing** — broken regex in CI caused multiple failures.
30. **Introduce concepts before using them** — key terms must be defined before the trace.

---

## Core ADK Architecture

Understanding these layers is essential for adding or updating documentation:

| Layer | Class | Role |
|---|---|---|
| Events | `Event`, `EventActions` | Universal data flowing through every layer |
| Agents | `BaseAgent`, `LlmAgent` | Blueprints for agent behavior |
| Runner | `Runner` | Stateless orchestrator: session → agent → events |
| Flows | `BaseLlmFlow` | Reason-act loop inside LlmAgent |
| Models | `BaseLlm`, `LLMRegistry` | Adapters for Gemini, Anthropic, LiteLLM |
| Sessions | `Session`, `BaseSessionService` | Conversation history + state dict |
| Tools | `BaseTool`, `FunctionTool`, `BaseToolset` | Pluggable capabilities |
| Apps | `App`, `BasePlugin` | High-level container, cross-cutting hooks |

**Key ADK modules** (in `google.adk.*`):
- `events`, `agents`, `runners`, `flows.llm_flows`, `models`
- `sessions`, `tools`, `apps`, `memory`, `artifacts`, `auth`, `telemetry`

---

## Document Conventions

Every deep-dive file (01–08) follows this structure:

1. **What It Is** — one-paragraph summary
2. **Class Hierarchy** — ASCII diagram of inheritance
3. **Key Fields / Methods** — table or list with types
4. **Usage Examples** — Python code snippets
5. **Cross-references** — links to related files in this repo

When adding or editing documentation, preserve this structure.

---

## Key Architectural Patterns

These patterns appear throughout the documentation and should be applied consistently in new content:

### 1. Async-First / Streaming
Every agent produces an `AsyncGenerator[Event, None]`:
```python
async def _run_async_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    yield Event(...)
```

### 2. Context Threading
`InvocationContext` is passed through every call chain. It carries the session, state, credentials, and enables callbacks.

### 3. Adapter / Strategy Pattern
Abstract base classes define contracts; multiple concrete implementations exist:
- `BaseLlm` → `GeminiLlm`, `AnthropicLlm`, `LiteLlm`
- `BaseSessionService` → `InMemorySessionService`, `SQLiteSessionService`, `DatabaseSessionService`
- `BaseTool` → `FunctionTool`, `AgentTool`, `LongRunningFunctionTool`

### 4. Hook / Callback Pattern
LlmAgent supports layered interception:
- `before_agent_callback` / `after_agent_callback`
- `before_model_callback` / `after_model_callback`
- `before_tool_callback` / `after_tool_callback`
- `on_model_error_callback` / `on_tool_error_callback`

### 5. Pipeline / Processor Pattern
`BaseLlmFlow` runs processors in order:
- **Request processors**: instructions, contents, functions, output_schema
- **Response processors**: code_execution, functions, agent_transfer

### 6. Event-Driven Side Effects
Side effects (state mutations, agent transfers, escalations) are carried in `EventActions` — not via direct method calls.

---

## Python Style & Conventions

Code examples in documentation should follow these conventions:

- **Python 3.10+** syntax (use `X | Y` unions, `match`/`case` where appropriate)
- **Type hints** on all function signatures
- **Pydantic v2** for data models (`model_validator`, `field_validator`, `model_config`)
- **PascalCase** for classes, **snake_case** for methods and variables
- **Agent names** must be valid Python identifiers; `"user"` is reserved by ADK
- **`asyncio`** for all I/O-bound concurrency — no threading
- **`pytest` + `pytest-asyncio`** for tests (`@pytest.mark.asyncio`)

---

## Content Decision Guide

Use `10-when-to-build-what.md` as the authoritative source for mapping scenarios to ADK components. When describing a new use case, follow its decision tree format:

```
Need to add a capability to an agent?
├── Simple function → FunctionTool (automatic wrapping)
├── Needs lifecycle hooks → BaseTool subclass
├── Dynamic set of tools → BaseToolset subclass
└── Long-running operation → LongRunningFunctionTool
```

---

## What to Add / What to Avoid

**Add:**
- Deep dives on any ADK component not yet covered (e.g., `memory`, `artifacts`, `auth`, `a2a`, `code_executors`, `evaluation`)
- Additional Python guides (e.g., `python-generators-deep-dive.md`, `python-context-managers-deep-dive.md`)
- Real-world scenario walkthroughs following the `01-request-lifecycle.md` format
- Java-to-Python comparison tables where helpful

**Avoid:**
- Adding runnable code or build artifacts — this is a docs-only repo
- Creating configuration files (no `pyproject.toml`, `requirements.txt`, etc. needed)
- Duplicating content already covered in existing files
- Referencing ADK internals that differ from the `google.adk.*` module structure

---

## Git Workflow

**Active branch:** `claude/document-project-contents-n0J8I`

```bash
# Stage and commit new documentation
git add <file>.md
git commit -m "docs: <short description>"

# Push to remote
git push -u origin claude/document-project-contents-n0J8I
```

**Commit message conventions:**
- `docs: add <topic> deep dive` — new documentation file
- `docs: update <file> — <what changed>` — update existing file
- `docs: fix <file> — <correction>` — factual correction
- `feat: add <feature>` — non-doc additions (rare in this repo)

---

## Reading Order for New Contributors

1. `README.md` — big picture architecture
2. `01-request-lifecycle.md` — full traced request through every layer
3. `03-runners.md` through `09-tools.md` — core layers in execution order
4. `10-when-to-build-what.md` — practical decision guide
5. `python-for-adk-learning-plan.md` — if you need Python fundamentals
6. Python deep dives as needed (asyncio, Pydantic, decorators, testing)
