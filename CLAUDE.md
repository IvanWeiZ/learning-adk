# CLAUDE.md — AI Assistant Guide for learning-adk

This file provides context for AI assistants (Claude, Copilot, etc.) working in this repository.

## What This Repository Is

A curated documentation and learning resource for **Google ADK (Agent Development Kit)** — a Python framework for building multi-agent AI systems. The repository contains no runnable source code; all content is Markdown files.

**Primary audience:** Experienced Java developers transitioning to Python and ADK.

**Reference codebase:** `~/Documents/adk-python` (Google ADK source, not included here).

**ADK version traced:** v1.27.2 ([commit `15ddf2d`](https://github.com/google/adk-python/commit/15ddf2d50d9cca31d641c1c2aa572a2415198454)).

---

## Repository Structure

```
learning-adk/
├── README.md                                      # Architecture overview and reading order
├── CONTRIBUTING.md                                # Contribution guidelines, diagram style
├── adk/
│   ├── 00-onboarding-guide.md                     # Zero to first agent — motivation
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
│   ├── 23-advanced-internals.md                   # Processor pipeline, reason-act loop
│   ├── 24-faq.md                                  # Tool versioning, state scoping
│   ├── 25-adk-2.0-preview.md                      # ADK 2.0: graph workflows, collaborative agents
│   ├── 24b-custom-use-cases.md                        # Component code examples (split from 02)
│   ├── 19b-security-checklist.md                  # Audit checklist, threat model (split from 19)
│   ├── 20b-debugging-guide.md                     # Debugging checklist, performance (split from 20)
│   ├── 22b-testing-context-setup.md               # Context setup, fixtures (split from 22)
│   ├── 22c-testing-examples.md                    # Test examples for callbacks, plugins (split from 22)
│   ├── 23b-plugins-and-a2a.md                         # Custom tools, A2A, code executors (split from 23)
│   └── 25b-adk-2.0-patterns.md                         # Collaborative agents, dynamic workflows (split from 25)
├── python/
│   ├── python-for-adk-learning-plan.md            # 2-week Python curriculum
│   ├── python-gotchas-for-java-developers.md      # 13 runtime traps Java devs hit
│   ├── python-asyncio-deep-dive.md                # Async/await core patterns
│   ├── python-asyncio-advanced.md                 # Sync primitives, queues, debugging (split)
│   ├── python-decorators-deep-dive.md             # Decorators, closures, inspect
│   ├── python-metaprogramming-deep-dive.md        # Descriptors, metaclasses, registry (split)
│   ├── python-pydantic-deep-dive.md               # Pydantic v2 core reference
│   ├── python-pydantic-advanced.md                # Generics, JSON schema, custom types (split)
│   ├── python-testing-and-mocking-guide.md        # pytest, Mock, fixtures core
│   └── python-testing-advanced.md                 # Async testing, parametrize, ADK patterns (split)
└── reference/
    ├── glossary.md                                # ADK terminology quick-reference
    └── java-to-python-cheat-sheet.md              # Side-by-side Java → Python mappings
```

**Total:** ~21,500+ lines across 46 Markdown files.

---

## Documentation Site

The repo is served as a docs site via **MkDocs Material** at [ivanweiz.github.io/learning-adk](https://ivanweiz.github.io/learning-adk/).

**Key files:**

- `mkdocs.yml` — Site config (Material theme, Mermaid extension, nav structure)
- `requirements.txt` — Pinned `mkdocs-material==9.6.14`
- `docs/index.md` — Landing page (adapted from README)
- `docs/{adk,python,reference}` — Symlinks to content directories
- `.github/workflows/docs.yml` — Auto-deploys to GitHub Pages on push to `main`

**Local development:**

```bash
pip3 install -r requirements.txt
mkdocs serve                       # http://127.0.0.1:8000/learning-adk/
mkdocs build                       # builds to site/ (gitignored)
```

**Diagram policy:** ASCII diagrams are preferred for readability. Mermaid `sequenceDiagram` may be used for cross-component message flows (see `01-request-lifecycle.md`). Do NOT convert ASCII trees or class hierarchies to Mermaid flowcharts/classDiagrams — they become less readable.

---

## Pre-Commit Validation Checklist

**Run these checks before every commit.** You can run all checks at once:

```bash
bash scripts/validate.sh
```

**Agents MUST run `bash scripts/validate.sh` before every commit and fix any errors (non-zero exit) before committing.**

Each check is also documented individually below.

### 1. Heading checkboxes (agents reintroduce these every time)

```bash
grep -rn '^#.*\[ \]' adk/*.md python/*.md reference/*.md
```

Fix: `perl -pi -e 's/^(#{2,4}) \[ \] /$1 /g' adk/*.md python/*.md`

### 2. Heading spacing (## must be followed by a space)

```bash
grep -rn '^##[A-Z]' adk/*.md python/*.md reference/*.md
grep -rn '^####[A-Z]' adk/*.md python/*.md reference/*.md
```

**Previously violated by:** `adk/07-events.md` (7 headings), `adk/09-tools.md` (1 heading) — fixed.

### 3. Broken cross-references (stale "b-suffix" filenames)

Files were renamed from `XXb-name.md` to `name.md` but some references weren't updated:

```bash
grep -rn '[0-9]\+b-' adk/*.md
```

All 12 broken b-suffix links have been fixed. Run the check above to ensure no regressions.

### 4. Relative source paths (should use GitHub URLs)

```bash
grep -rn '\.\./adk-python/' adk/*.md
```

All relative paths have been converted to GitHub URLs. Run the check above to ensure no regressions.

### 5. Line-3 header format (`adk/*.md` only)

```bash
for f in adk/*.md; do h=$(sed -n '3p' "$f"); echo "$f: $h"; done | grep -v 'Official docs:'
```

Every `adk/*.md` file line 3 must follow: `> **Official docs:** [Link](URL) | **Source:** [...] | **Prereqs:** [...]`

All 6 previously missing headers have been fixed. Run the check above to ensure no regressions.

### 6. File length limits

```bash
for f in adk/*.md; do l=$(wc -l < "$f"); [ "$l" -gt 600 ] && echo "OVER: $f ($l lines, limit 600)"; done
for f in python/*.md; do l=$(wc -l < "$f"); [ "$l" -gt 1000 ] && echo "OVER: $f ($l lines, limit 1000)"; done
l=$(wc -l < adk/00-onboarding-guide.md); [ "$l" -gt 250 ] && echo "OVER: onboarding ($l lines, limit 250)"
```

Limits: ADK docs **600**, Python guides **1000**, Onboarding **250**.

**Files currently over limit:**
- `adk/01-request-lifecycle.md`: 621 (limit 600)
- `adk/18-session-lifecycle.md`: 603 (limit 600)
- `adk/24-faq.md`: 648 (limit 600)
- `adk/25-adk-2.0-preview.md`: 933 (limit 600)
- `adk/22c-testing-examples.md`: 633 (limit 600)
- `python/python-metaprogramming-deep-dive.md`: 1350 (limit 1000)
- `python/python-pydantic-advanced.md`: 1418 (limit 1000)

### 7. Reserved agent name `"user"`

```bash
grep -rn 'name="user"' adk/*.md python/*.md
```

`"user"` is reserved by ADK for the user role in events. Agent examples must use a different name. Currently violated in `adk/20-best-practices.md` (intentional anti-pattern example — verify it's clearly marked as **wrong**).

### 8. Links inside code blocks (not clickable)

```bash
grep -B5 'https://' adk/*.md | grep -A1 '```'
```

URLs inside `` ``` `` blocks aren't clickable. Use markdown tables or inline links outside code blocks.

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
10. **No side-by-side boxes** — always vertical tree. (Violated in `00-onboarding-guide.md` lines 160-184.)
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
21. **Agents reintroduce checkboxes** — run the check in §1 above after every agent completes.
22. **Agents reintroduce removed content** — diff the file before/after every agent.
23. **Agents overwrite each other** — never run multiple agents on same file.
24. **Agents drop heading spaces** — run the check in §2 above after every agent.
25. **Verify content, not just formatting** — read the rendered output, don't just grep.
26. **Verify official doc URLs** — WebFetch every URL before using.
27. **Header format: `Official docs | Source | Prereqs`** — always this order, always on line 3 of `adk/*.md`.
28. **When removing content, verify it exists elsewhere** — move before delete.
29. **Fix the pattern, not the instance** — search ALL files for same issue.
30. **Test CI locally before pushing** — broken regex in CI caused multiple failures.
31. **Introduce concepts before using them** — key terms must be defined before the trace.
32. **After renaming/splitting files, grep ALL files for old filename** — stale "b-suffix" links persisted across 5 files (see §3 above).
33. **Use GitHub URLs for source references** — not `../adk-python/` relative paths (see §4 above).

---

## Readability Edit Rules

When editing documentation for readability, follow these rules strictly.

### Allowed

| Type | Example |
|------|---------|
| Fix typos / grammar | "will raise" → "raises" |
| Fix factual errors | Wrong class name, wrong model ID |
| Fix broken links | `25-onboarding-guide.md` → `00-onboarding-guide.md` |
| Rename headings | "Quick Decision Tree" → "Decision Tree" |
| Clean up authoring notes | Remove "(big-picture diagram first...)" from heading |
| Backward cross-reference for dedup | Add "See [01-request-lifecycle.md]" from file `05` — **only higher → lower number** |
| Add "See [file]" notes | When content exists in two places, link to the earlier doc |
| Fix formatting | Missing heading space, stray `---` |
| Improve sentence clarity | Break a run-on sentence into bullets |
| Add missing context callouts | "> Not needed for ADK — listed for completeness" |
| Add vale tooling | `.vale.ini`, `.gitignore`, `validate.sh` updates |
| Fix contradictory statements | Clarify one to be consistent — don't delete either |
| Fix future tense → present tense | "will raise" → "raises" (mechanical, not content-changing) |

### Not Allowed

| Type | Why |
|------|-----|
| Delete sections or paragraphs | Content stays, even if duplicated |
| Remove code examples | Including Java comparison blocks |
| Shorten code blocks | Don't collapse 3 examples into 1 |
| Restructure file layout | Don't move sections between files |
| Split over-limit files | Keep files as-is even if over 600/1000 lines |
| Forward cross-references | Don't add "See [07]" from inside `01` — only backward refs |

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

Every numbered deep-dive file (01–25) follows this structure:

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

Use `02-when-to-build-what.md` as the authoritative source for mapping scenarios to ADK components. When describing a new use case, follow its decision tree format:

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
- Additional Python guides (e.g., `python-generators-deep-dive.md`, `python-context-managers-deep-dive.md`)
- Real-world scenario walkthroughs following the `01-request-lifecycle.md` format
- Java-to-Python comparison tables where helpful
- Deep dives on any ADK component not yet covered (most core components are now documented in files 00–25)

**Avoid:**
- Adding runnable code or build artifacts — this is a docs-only repo
- Creating configuration files (no `pyproject.toml`, `requirements.txt`, etc. needed)
- Duplicating content already covered in existing files
- Referencing ADK internals that differ from the `google.adk.*` module structure

---

## Git Workflow

```bash
# Stage and commit new documentation
git add <file>.md
git commit -m "docs: <short description>"

# Push to the current working branch
git push -u origin <current-branch>
```

**Commit message conventions:**
- `docs: add <topic> deep dive` — new documentation file
- `docs: update <file> — <what changed>` — update existing file
- `docs: fix <file> — <correction>` — factual correction
- `feat: add <feature>` — non-doc additions (rare in this repo)

---

## CI Checks

CI runs on push/PR to `main` via `.github/workflows/ci.yml`. It checks:

1. **Broken relative links** — scans all markdown for `](path)` and verifies targets exist
2. **Heading checkboxes** — rejects `## [ ] Title` patterns (agents reintroduce these)
3. **Header format** — `adk/*.md` line 3 must contain `Official docs:` if it starts with `>`
4. **File length limits** — warnings (non-blocking) for files over limits

File length violations are warnings, not failures. But they signal a file should be split.

---

## Reading Order for New Contributors

1. `README.md` — big picture architecture
2. `01-request-lifecycle.md` — full traced request through every layer
3. `03-runners.md` through `09-tools.md` — core layers in execution order
4. `02-when-to-build-what.md` — practical decision guide
5. `python-for-adk-learning-plan.md` — if you need Python fundamentals
6. Python deep dives as needed (asyncio, Pydantic, decorators, testing)
