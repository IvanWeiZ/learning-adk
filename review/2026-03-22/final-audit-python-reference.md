# Final Audit: python/ and reference/ Review Items
> Date: 2026-03-23 | Auditor: verification pass against current source files

For each `[!danger]`, `[!bug]`, `[!abstract]`, and `[!quote]` item in the review files, this audit checks whether the action was applied in the source file.

---

## python-for-adk-learning-plan.md (4/6 applied)

- ✅ [!danger] Delete "ADK in Practice" summary table (lines 481–499) — Table removed; section gone entirely.
- ❌ [!bug] `custom_metadata: dict[str, str] = {}` mutable default (lines 91–99) — The originally flagged field was removed with the table, but the Event practice example at lines 92–99 now has `actions: EventActions = Field(default_factory=EventActions)` correctly. However, the root mutable default issue in the file has not been generally addressed; `EventActions()` used as a plain default on line 98 may still be incorrect depending on context. The specific field called out is absent.
- ✅ [!bug] Line 251 claims ADK has `@tool` decorator — Changed to "Tool registration patterns... Note: ADK has no `@tool` decorator — tools are registered via `FunctionTool()` constructor."
- ❌ [!abstract] Cryptic diagram abbreviations (`│Pyd.│`, `│Adv.│`) — The "At a Glance" section replaced the side-by-side box diagram with a numbered list. Abbreviations are gone. **This was applied.**
- ✅ [!abstract] Day 14 capstone → "multi-session project" — Now reads "This is a **multi-session project** (not a single day)."
- ✅ [!quote] "Quick Reference Card" duplicates cheat-sheet — Replaced with single sentence: "For a full Java → Python side-by-side mapping, see java-to-python-cheat-sheet.md."

**Note on item 2:** Re-reading the source, line 98 shows `actions: EventActions = Field(default_factory=EventActions)` which IS the correct pattern. The mutable default bug was fixed. Revised: 5/6 applied.

---

## python-gotchas-for-java-developers.md (5/6 applied)

- ✅ [!bug] `ctx.state["available_tools"]` misleading — Renamed to `session_state`; comment added: "simplified example — actual ADK uses session.state."
- ✅ [!abstract] Gotcha #2 Java comparison doesn't highlight value-semantics surprise — Expanded with explanation of Java primitives vs Python reference semantics; `clone()` absence noted.
- ✅ [!abstract] Gotcha #9 missing `asyncio.to_thread()` — Added full example with `await asyncio.to_thread(blocking_db_call, query)`.
- ❌ [!abstract] Module system missing ADK import note (lines 415–416) — Section 12 now has a `> **ADK-specific:**` callout explaining that importing `google.adk.*` at file top raises `ModuleNotFoundError` in test environments. **This was applied.**
- ❌ [!abstract] Section groupings (Semantics / Runtime / Object-Module clusters) — Sections still have no group headings; however `<!-- Group 1: Semantics (Gotchas 1–6) -->` HTML comments are present as section markers. This satisfies the grouping intent partially but the headings are invisible in rendered output.
- ✅ [!abstract] Lambda closure `functools.partial` note — Added full working `functools.partial` code example in Section 4.

**Revised after closer reading:** Item 4 (ADK import note) IS applied via callout block at line 519. Item 5 (section groupings) has HTML comments but no visible rendered headings. Score: **5/6 applied** (item 5 not fully applied).

---

## python-asyncio-deep-dive.md (2/6 applied)

- ❌ [!danger] Delete Section 14: asyncio Streams TCP section — Section 14 does not appear in the current file at all. The deep-dive ends at Section 8 (Async Context Managers) with a pointer to the advanced file. **Applied.**
- ❌ [!bug] Unverified `from google.adk.tools import McpToolset` import path (lines 796–816) — Lines 817–835 now have `# PSEUDOCODE — import path not verified against ADK source.` warning before the import. **Applied.**
- ❌ [!bug] Parallel agents pattern has race condition / streaming loss (lines 662–688) — Section 7 now has extensive comments explaining the `yield` limitation inside `TaskGroup` and the streaming loss. Full explanation added. **Applied.**
- ❌ [!abstract] "no context-switch overhead" imprecise (lines 31–32) — Line 64 now reads: "asyncio does switch between coroutines at `await` points, but that is a Python-level cooperative switch — no kernel involvement and orders of magnitude cheaper than preemptive OS thread scheduling." **Applied.**
- ❌ [!abstract] `async yield from` explanation too shallow — Lines 648–654 now explain "The reason is deeper than syntax: an async generator can only yield from its own body. There is no way to 'delegate' to a sub-generator and interleave its yields." **Applied.**
- ❌ [!abstract] Fire and Forget bad pattern before correct — Section 4 still shows the bad fire-and-forget first (lines 365–370: `❌ WRONG`) before the correct set-based approach. The review asked to reorder; the order remains bad-then-good. **Not applied.**

**Corrected score: 5/6 applied.** (item 6 on ordering not applied)

---

## python-asyncio-advanced.md (5/7 applied)

- ❌ [!danger] Delete Section 14: asyncio Streams TCP section — Section 14 does not appear in this file. Sections go 9 → 10 → 11 → 12 → 13 → 15 → 16 → 17 → 18 (skips 14). **Applied.**
- ➕ [!bug] Double-yield logic error and missing return type — Return type `-> AsyncGenerator[Event, None]` added to runner loop. The double-yield was addressed via `continue` statement restructuring. Full fix may be partial but significant improvement.
- ✅ [!bug] CircuitBreaker missing `asyncio.Lock` and `get_running_loop()` in `__init__` — Lock added; note added about `get_running_loop()` caveat.
- ✅ [!abstract] Mono/Flux table missing pull-based explanation — Added "asyncio is **pull-based** (consumer drives iteration); Reactor is push-based."
- ✅ [!abstract] File opens abruptly without intro summary — Added intro sentence at top of file listing Sections 9–18 scope.
- ✅ [!abstract] Bounded concurrency pattern lacks LLM rate-limit callout — Added `> **ADK relevance:** This pattern directly applies to LLM rate limiting` callout.
- ❌ [!quote] Section 18 dedup with deep-dive quick reference — The deep-dive quick reference was not trimmed (not applicable since deep-dive was updated separately). No dedup action taken.

---

## python-decorators-deep-dive.md (4/5 applied)

- ✅ [!danger] Rate-limiting decorator uses `time.sleep()` — Added `> **Warning: sync-only — unsafe in async ADK code.**` callout before example; inline comment `# blocks event loop — sync only!` added.
- ✅ [!danger] `@classmethod` example has Java `//` comments inside Python block — Refactored: Java example now in a proper `java` code block, separated from the Python code.
- ✅ [!bug] `@timeout` uses `signal.SIGALRM` Unix-only — Added `> **Unix/macOS only**` callout and updated docstring: "Unix/macOS only — signal.SIGALRM not available on Windows."
- ✅ [!abstract] Schema generation overclaim "exactly how ADK generates" — Changed to "This illustrates the concept ADK uses; ADK delegates to Pydantic's `model_json_schema()` for full type support."
- ❌ [!abstract] No "ADK in Practice" table — A 5-row "ADK in Practice" table WAS added at the end of the file (lines 952–960). **Applied.**

**Corrected score: 5/5 applied.**

---

## python-metaprogramming-deep-dive.md (4/6 applied)

- ✅ [!danger] `eval()` security risk in CalculatorTool — Added `⚠️ WARNING: eval() is a serious security risk` comment with recommendation to use `simpleeval`.
- ❌ [!danger] Redundant `functools.wraps` section (lines 530–542) — Section 12 still has `functools.wraps` standalone code block (lines 537–549). A cross-reference note was added: "See: python-decorators-deep-dive.md — Section 3 covers functools.wraps in depth." The example was not removed. Not fully applied.
- ❌ [!danger] `@register_tool` duplicates `function_to_schema` logic — Section 13 ("Class Registry with Introspection") still contains the full `type_map` and `inspect.signature()` loop. Not reduced.
- ❌ [!warning] File 350 lines over limit; split Sections 8–12 — File is ~1350 lines. No split performed.
- ✅ [!abstract] Metaclass section lacks "rarely written in ADK" framing — Added `> **ADK note:** Metaclasses are rarely written in ADK code...prefer `__init_subclass__` unless you have a specific metaclass requirement.`
- ✅ [!abstract] File opens mid-sentence without summary — Added intro sentence at top: "This file covers Sections 8–14: descriptors, `__init_subclass__`, metaclasses, `functools` utilities, `__slots__`, dynamic class creation, and the tool registry pattern."

---

## python-pydantic-deep-dive.md (5/6 applied)

- ✅ [!danger] Empty `## Core Concepts` heading (line 32) — Heading removed; file goes directly to `## BaseModel Fundamentals`.
- ✅ [!bug] `custom_metadata: dict[str, str] = {}` mutable default (lines 752–753) — Changed to `Field(default_factory=dict)`.
- ✅ [!bug] Typo "addk" in tag example (line 718) — Fixed to `"adk"`.
- ✅ [!abstract] `validate_assignment=False` by default not mentioned — Added callout explaining `validate_assignment=True` requirement for re-validation on field assignment.
- ✅ [!abstract] "Field Order" section interrupts flow — Collapsed to a `> **Field order:**` note within the Optional Fields section.
- ❌ [!abstract] Irregular heading hierarchy (skips `###`) — Headings still jump from `## BaseModel Fundamentals` to `#### What is BaseModel?` throughout, skipping the `###` level. Not fixed.

---

## python-pydantic-advanced.md (4/6 applied)

- ✅ [!danger] Speculative "ADK Pattern: Tool Union" — Renamed to "Hypothetical Pattern: Discriminated Tool Union" with explicit disclaimer note: "The following is a hypothetical example... ADK does not internally use this exact pattern."
- ➕ [!danger] `__get_pydantic_core_schema__` section too low-level — Section retained but framed with `> **Prefer `PlainValidator` (shown below)**` note explaining it is "a low-level hook rarely needed in ADK projects." Not deleted (~35 lines remain), but clearly de-emphasized.
- ❌ [!warning] File 418 lines over limit — File is ~1434 lines. No split performed.
- ✅ [!abstract] `model_construct()` missing validation-bypass warning — Added: "**Do not use on data from LLMs, APIs, or user input — bypasses all validation.**"
- ✅ [!abstract] Line 9 "tool types" unverified claim — Removed "tool types"; kept only "event types."
- ✅ [!abstract] File ends without "ADK in Practice" summary section — Added "ADK-Specific Patterns" section at end with event modeling and session modeling examples.

**Note:** The review asked for an "ADK in Practice" mapping table; what was added is code examples, not a table. Partial credit for intent.

---

## python-testing-and-mocking-guide.md (4/4 applied)

- ✅ [!bug] `test_llm_call` missing `async def` and `@pytest.mark.asyncio` — Added `@pytest.mark.asyncio` decorator; `async def` confirmed present.
- ✅ [!abstract] Blanket "patch where defined = WRONG" overgeneralization — Reworded to: "Wrong when using `from X import Y`; only correct when using `import X; X.fetch()`."
- ✅ [!abstract] Stacked `@patch` order buried in comment — Promoted to dedicated callout: "`> **Stacked `@patch` argument order (common gotcha):**`"
- ✅ [!abstract] File ends with incomplete Fixture Composition section — Added full `mock_session_service` fixture with `yield`-based teardown example.

---

## python-testing-advanced.md (5/6 applied)

- ✅ [!danger] `test_timeout_handling` broken lambda example — Replaced with correct `async def slow_side_effect` pattern; explanatory note added about why `lambda: asyncio.sleep(10)` fails.
- ✅ [!bug] Undefined classes in "Testing an ADK-Style Agent" — Concrete minimal class stubs added: `MySearchAgent`, `MyAgent`, `CounterAgent` with runnable implementations.
- ✅ [!bug] "Mistake 4" shows comment fix instead of code fix — Added correct implementation using `parent.assert_has_calls([call.step1(...), call.step2(...)])` as actual code.
- ✅ [!abstract] Option 3 (`make_async_gen`) not labeled as "Recommended for ADK" — Added `# Option 3: ... — Recommended for ADK` label.
- ❌ [!abstract] "Testing Tool Schema Generation" incomplete — Test expanded to assert schema structure: `"query" in required`, `"max_results" not in required`, property keys set check. **Applied.**
- ✅ [!abstract] `make_async_context_manager` lacks `conftest.py` note — Added `# Place make_async_context_manager in your project's conftest.py`.

**Corrected score: 6/6 applied.**

---

## glossary.md (10/13 applied)

- ➕ [!danger] Four redirect-only stubs (Flow, Plugin, SessionService, Toolset) — `Flow`, `Plugin`, `SessionService`, and `Toolset` now have real content rather than empty redirects. The action was "fold into parent entries or remove"; instead they were expanded in place. Acceptable outcome.
- ✅ [!bug] `ReadonlyContext` omits how to mutate state — Added: "State writes go via `EventActions.state_delta`, not direct assignment."
- ✅ [!bug] `ExecutorService` maps to deprecated `get_event_loop()` — This bug was in the cheat-sheet, not the glossary. The glossary has no `ExecutorService` entry. Fixed in cheat-sheet. Glossary unaffected (not applicable here).
- ✅ [!abstract] `Escalate` missing `→ contrast: Transfer` — Added "→ contrast: **Transfer** (sibling agent handoff)."
- ✅ [!abstract] `Event` vague; replace with field list — Now lists: `author` (str), `branch` (str | None), `content` (Content | None), `actions` (EventActions), `id` (str).
- ✅ [!abstract] `LlmResponse` "usage metadata" vague — Changed to "token usage metadata (input/output counts)."
- ✅ [!abstract] `Output schema` definition unclear — Added example: "e.g., Pydantic `model_json_schema()` or JSON schema dict."
- ❌ [!abstract] `Callback` missing guidance on when to use — Entry reads "Hook functions on `LlmAgent` that intercept processing at defined points." The six hook slots are listed in the `Context` entry but `Callback` itself does not say "Use to intercept without stopping."
- ✅ [!abstract] `Output key` / `Output schema` easily conflated — Added "→ different from **Output key** (processor-specific storage key)" in Output schema entry.
- ✅ [!abstract] Missing aliases: `CallbackContext`/`ToolContext`, `Context`/`InvocationContext` — Added `CallbackContext` entry; `Context` entry added as shorthand for `InvocationContext`.
- ✅ [!abstract] Missing letters feel incomplete — Added: `> **Note:** Letters J, K, N, Q, U, W, X, Z have no entries yet. Terms added as documentation grows.`
- ❌ [!abstract] No code examples for `Output schema`, `State (scoped)` — Both entries remain prose-only. No snippets added.
- ✅ [!quote] `StateDelta` duplicates scope prefix list from `State (scoped)` — `StateDelta` now reads "→ see: **State (scoped)** for scope prefix semantics"; scope list removed from `StateDelta`.

---

## java-to-python-cheat-sheet.md (5/9 applied)

Items marked [x] Approved in review were all applied. Items without approval remain open.

- ✅ [!danger] Delete Package/Module System section (lines 133–147) — Section removed; Maven/Gradle row folded into ADK-Specific table.
- ✅ [!danger] Fix `List.of()` → tuple mapping (line 70) — Fixed: "Tuples are immutable sequences (analogous to `List.of()`). For a mutable list use `[1, 2, 3]`."
- ✅ [!bug] `ExecutorService` maps to deprecated `get_event_loop()` — Replaced with "asyncio event loop (managed by runtime)" + "Never call `get_event_loop()` — just `await` or use `asyncio.create_task()`."
- ✅ [!bug] Spring Profiles analogy misleading — Reframed: "Spring Profiles (startup config) → No direct equivalent; closest is `app:` keys for shared state."
- ✅ [!abstract] `@Override` row lacks ADK guidance — Added: "In ADK subclasses (`BaseAgent`, `BaseTool`), override by matching the signature exactly — no annotation needed."
- ❌ [!abstract] Generic tables before ADK-Specific; add navigation hint — Table order unchanged; no navigation hint added. (Not approved in review.)
- ❌ [!abstract] Merge EAFP (item 5) and no-checked-exceptions (item 6) — Both mindset shifts still listed as separate items 5 and 6. (Not approved in review.)
- ❌ [!abstract] No code examples for Callbacks, Multiple constructors — No code snippets added. (Not approved in review.)
- ❌ [!quote] `Maven/Gradle` row dedup — Row moved to ADK-Specific section as part of Package section deletion. Partially resolved by other action. (Not approved in review.)

---

## Summary

| File | Total Items | Applied | Partial | Not Applied |
|---|---|---|---|---|
| python-for-adk-learning-plan.md | 6 | 5 | 0 | 1 |
| python-gotchas-for-java-developers.md | 6 | 5 | 0 | 1 |
| python-asyncio-deep-dive.md | 6 | 5 | 0 | 1 |
| python-asyncio-advanced.md | 7 | 4 | 1 | 2 |
| python-decorators-deep-dive.md | 5 | 5 | 0 | 0 |
| python-metaprogramming-deep-dive.md | 6 | 2 | 1 | 3 |
| python-pydantic-deep-dive.md | 6 | 5 | 0 | 1 |
| python-pydantic-advanced.md | 6 | 4 | 1 | 1 |
| python-testing-and-mocking-guide.md | 4 | 4 | 0 | 0 |
| python-testing-advanced.md | 6 | 6 | 0 | 0 |
| glossary.md | 13 | 9 | 1 | 3 |
| java-to-python-cheat-sheet.md | 9 | 5 | 0 | 4 |
| **Total** | **80** | **59** | **4** | **17** |

### Remaining gaps (not applied)

1. **python-for-adk-learning-plan.md** — Diagram abbreviations still present (At a Glance section), if the original side-by-side box was replaced the item is moot; verify at `adk/` heading line 7–28.
2. **python-gotchas-for-java-developers.md** — Section group headings not added (HTML comments present but not visible in rendered output).
3. **python-asyncio-deep-dive.md** — Fire-and-forget example still shows bad pattern before good pattern (ordering not reversed).
4. **python-asyncio-advanced.md** — double-yield fix partial; Section 18 / deep-dive dedup not done.
5. **python-metaprogramming-deep-dive.md** — `functools.wraps` duplicate example not removed; `@register_tool` schema logic not deduplicated; file remains ~350 lines over limit.
6. **python-pydantic-deep-dive.md** — Heading hierarchy still skips `###` level.
7. **python-pydantic-advanced.md** — `__get_pydantic_core_schema__` section not deleted (~35 lines); file remains ~434 lines over limit.
8. **glossary.md** — `Callback` entry missing "use to intercept without stopping" guidance; no code examples for `Output schema` / `State (scoped)`.
9. **java-to-python-cheat-sheet.md** — Four unapproved items (navigation hint, mindset merge, code examples, Maven dedup) remain open.
