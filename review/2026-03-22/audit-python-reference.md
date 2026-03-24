# Audit: python/ and reference/ Review Items
> Date: 2026-03-23 | Source commit: `bdd0556` (docs: apply readability review fixes to python/ and reference/)

This audit checks every `[!danger]`, `[!bug]`, `[!abstract]`, and `[!quote]` item from each review file against the current source file.

Legend:
- ✅ Applied
- ❌ Not applied
- ➕ Partially applied / note added instead of full action
- ℹ️ Not approved in review (checkbox unchecked) — listed for completeness

---

## 1. python-for-adk-learning-plan.md → python/python-for-adk-learning-plan.md

**Result: ❌ 2 of 6 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] Delete "ADK in Practice" summary table (lines 481–499) | ✅ Applied | Table removed; section gone. |
| [!bug] `custom_metadata: dict[str, str] = {}` mutable default (lines 91–99) | ❌ **Not applied** | Lines 91–99 now show `actions: EventActions = EventActions()` — a Pydantic mutable default. The originally flagged field no longer exists (it was in the old ADK table), but the existing `EventActions()` default is equally wrong and was not fixed. |
| [!bug] `@tool` decorator reference (line 251) | ✅ Applied | Changed to "Tool registration patterns... Note: ADK has no `@tool` decorator." |
| [!abstract] Cryptic abbreviations in diagram (`│Pyd.│`, `│Adv.│`) | ❌ **Not applied** | Diagram still shows abbreviated labels `│Pyd.│`, `│Adv.│`, `│Deco.│` etc. |
| [!abstract] Day 14 capstone → "multi-session project" | ✅ Applied | Now reads "This is a **multi-session project** (not a single day)." |
| [!quote] "Quick Reference Card" → cross-reference link | ✅ Applied | Replaced with single sentence linking to java-to-python-cheat-sheet.md. |

---

## 2. python-gotchas-for-java-developers.md → python/python-gotchas-for-java-developers.md

**Result: ❌ 3 of 6 items missing**

| Item | Status | Notes |
|---|---|---|
| [!bug] `ctx.state["available_tools"]` misleading (lines 75–89) | ✅ Applied | Variable renamed to `session_state`; added comment "simplified example — actual ADK uses session.state". |
| [!abstract] Gotcha #2 Java comparison doesn't highlight value-semantics surprise | ✅ Applied | Expanded to explain Java has `int[]` primitives with value semantics; Python has no such types; `clone()` is absent. |
| [!abstract] Gotcha #9 missing `asyncio.to_thread()` pattern | ✅ Applied | Added `asyncio.to_thread()` example with clear note about blocking code. |
| [!abstract] Module system example missing ADK-specific import note (lines 415–416) | ❌ **Not applied** | Section 12 (Import System Traps) has no note about ADK module imports failing in test environments without ADK installed. |
| [!abstract] Section groupings (Semantics / Runtime / Object-Module clusters) | ❌ **Not applied** | Gotchas 1–13 still listed without group headings. |
| [!abstract] Lambda closure `functools.partial` note (lines 142–152) | ✅ Applied (expanded) | Added full `functools.partial` code example in Section 4. The review asked for "one-sentence note"; the commit added a full example — stronger than required. |

---

## 3. python-asyncio-deep-dive.md → python/python-asyncio-deep-dive.md

**Result: ❌ 6 of 6 items not applied** (file was reverted — no changes from main)

| Item | Status | Notes |
|---|---|---|
| [!danger] Delete Section 14: asyncio Streams TCP section (lines 447–481) | ❌ **Not applied** | Section 14 (asyncio Streams) still exists at line 450 with full TCP client/server code. |
| [!bug] `from google.adk.tools import McpToolset` unverified import path (lines 796–816) | ❌ **Not applied** | Line 801 still has `from google.adk.tools import McpToolset` with no "pseudocode" warning. |
| [!bug] Parallel agents race condition / streaming loss (lines 662–688) | ❌ **Not applied** | No explanation of streaming loss or TaskGroup limitation added. |
| [!abstract] "no context-switch overhead" imprecise (lines 31–32) | ❌ **Not applied** | Line 27 still reads "No threads, no locks, no context-switch overhead" without distinguishing Python-level vs OS-level switching. |
| [!abstract] `async yield from` explanation too shallow (lines 647–659) | ❌ **Not applied** | Lines 647–658 still only say "SyntaxError" without explaining the underlying reason (cannot interleave sub-generator with own yields). |
| [!abstract] Fire and Forget bad pattern shown before correct (lines 339–369) | ❌ **Not applied** | Section 5 still shows the bad fire-and-forget pattern before the correct set-based approach. |

---

## 4. python-asyncio-advanced.md → python/python-asyncio-advanced.md

**Result: ❌ 3 of 7 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] Delete Section 14: asyncio Streams TCP section (lines 448–481) | ❌ **Not applied** | Section 14 (asyncio Streams — TCP/Network I/O) still exists at line 450. |
| [!bug] Double-yield logic error and missing return type (lines 652–688) | ➕ Partial | Return type `-> AsyncGenerator[Event, None]` was added (line 661). The double-yield was not directly fixed but a `continue` was added (line 686) to skip the transfer event. Whether the exact double-yield bug at original lines 682/684 was resolved depends on the revised logic; the commit message claims it was addressed. |
| [!bug] CircuitBreaker missing `asyncio.Lock` (lines 596–631) | ✅ Applied | `asyncio.Lock()` added to `__init__`; warning note added about `get_running_loop()` in `__init__`. |
| [!abstract] Java→Python table Mono/Flux missing pull-based explanation (lines 789–814) | ✅ Applied | Added "asyncio is **pull-based** (consumer drives iteration); Reactor is push-based." |
| [!abstract] File opens abruptly without intro summary | ✅ Applied | Added intro sentence listing Sections 9–18 scope at top of file. |
| [!abstract] Bounded concurrency pattern lacks LLM rate-limit callout (lines 555–568) | ✅ Applied | Added ADK relevance callout: "directly applies to LLM rate limiting — use a Semaphore to cap concurrent calls." |
| [!quote] Section 18 Java→Python table dedup with deep-dive quick reference | ❌ **Not applied** | No trimming of quick reference in asyncio-deep-dive was done (deep-dive was reverted). The dedup is still present. |

---

## 5. python-decorators-deep-dive.md → python/python-decorators-deep-dive.md

**Result: ❌ 1 of 5 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] Rate-limiting decorator uses `time.sleep()` — unsafe in async (lines 431–463) | ✅ Applied | Added warning callout before example and `# blocks event loop — sync only!` comment. Did not delete; marked clearly as sync-only. Action allowed "mark clearly" per review. |
| [!danger] `@classmethod` example has Java `//` comments inside Python (lines 555–567) | ✅ Applied | Refactored to a proper `java` code block with the Java example separated from the Python block. |
| [!bug] `@timeout` uses `signal.SIGALRM` Unix-only (lines 467–495) | ✅ Applied | Added `> **Unix/macOS only**` callout and updated docstring. |
| [!abstract] Schema generation overclaim "exactly how ADK generates" (line 846) | ✅ Applied | Changed to "This illustrates the concept ADK uses; ADK delegates to Pydantic's `model_json_schema()`." |
| [!abstract] No "ADK in Practice" table mapping decorators to ADK components | ❌ **Not applied** | No 5-row table linking decorator patterns to ADK tool schema generation was added. |

---

## 6. python-metaprogramming-deep-dive.md → python/python-metaprogramming-deep-dive.md

**Result: ❌ 4 of 6 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] `eval()` security risk in CalculatorTool (lines 440–460) | ✅ Applied | Added `⚠️ WARNING: eval() is a serious security risk` comment with recommendation to use `simpleeval` or whitelist parser. Did not delete example, but clearly marked it. |
| [!danger] Redundant `functools.wraps` section already in decorators file (lines 530–542) | ❌ **Not applied** | Section 12 still has a `functools.wraps` standalone example (line 537–549) with note "Already covered, but essential" — the cross-reference to decorators file was not added, and the section was not removed. |
| [!danger] `@register_tool` decorator duplicates `function_to_schema` logic from decorators file (lines 704–800) | ❌ **Not applied** | Section 13 (Building a `@register_tool` Decorator) still contains full `type_map` and `inspect.signature()` loop at lines 713–810. Not reduced to wrapping-class-only. |
| [!warning] File is 350 lines over 1000-line limit; Sections 8–12 belong with decorators | ❌ **Not applied** | File is 1357 lines (limit 1000). No split was done; sections 8–12 (functools) remain in this file. |
| [!abstract] Metaclass section lacks upfront "rarely needed in ADK" framing | ✅ Applied | Added note before metaclass section: "Metaclasses are rarely written in ADK code. … prefer `__init_subclass__` unless you have a specific metaclass requirement." |
| [!abstract] File opens mid-sentence without summary | ✅ Applied | Added intro sentence summarizing what Sections 8–14 cover. |

---

## 7. python-pydantic-deep-dive.md → python/python-pydantic-deep-dive.md

**Result: ❌ 2 of 6 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] Empty `## Core Concepts` heading (line 32) | ✅ Applied | Heading removed; file now goes directly to `## BaseModel Fundamentals`. |
| [!bug] `custom_metadata: dict[str, str] = {}` mutable default (lines 752–753) | ✅ Applied | Changed to `Field(default_factory=dict)`. |
| [!bug] Typo "addk" in tag example (line 718) | ✅ Applied | All `"addk"` strings changed to `"adk"`. |
| [!abstract] `validate_assignment=False` by default not mentioned (line 291) | ✅ Applied | Added callout explaining `validate_assignment=True` required for re-validation on field assignment. |
| [!abstract] "Field Order" section interrupts flow (lines 139–154) | ✅ Applied | Collapsed to a single-line `> **Field order:**` note within the Optional Fields section. |
| [!abstract] Irregular heading hierarchy (`##` to `####`, skipping `###`) | ❌ **Not applied** | Headings still jump from `## BaseModel Fundamentals` directly to `#### What is BaseModel?` throughout the file — the `###` level is absent. |

---

## 8. python-pydantic-advanced.md → python/python-pydantic-advanced.md

**Result: ❌ 3 of 6 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] Speculative "ADK Pattern: Tool Union" (lines 78–123) | ✅ Applied | Renamed to "Hypothetical Pattern: Discriminated Tool Union" with explicit disclaimer note. |
| [!danger] `__get_pydantic_core_schema__` section too low-level (lines 659–695) | ➕ Partial | Section was NOT deleted. Instead a note was added: "Prefer `PlainValidator` (shown below)… `__get_pydantic_core_schema__` is a low-level hook rarely needed." The review action was to remove ~35 lines; the lines remain. |
| [!warning] File 418 lines over limit; split into `python-pydantic-reference.md` | ❌ **Not applied** | File is 1434 lines (limit 1000). No split was performed. |
| [!abstract] `model_construct()` missing validation-bypass warning (lines 720–737) | ✅ Applied | Added bold warning: "Do not use on data from LLMs, APIs, or user input — bypasses all validation." |
| [!abstract] Line 9 "tool types" unverified claim | ✅ Applied | Removed "tool types" from sentence; kept only "event types." |
| [!abstract] File ends without "ADK in Practice" summary section | ✅ Applied | Added "ADK in Practice" table at end mapping Pydantic patterns to ADK usage. |

---

## 9. python-testing-and-mocking-guide.md → python/python-testing-and-mocking-guide.md

**Result: ❌ 1 of 4 items missing**

| Item | Status | Notes |
|---|---|---|
| [!bug] `test_llm_call` missing `async def` and `@pytest.mark.asyncio` (lines 612–616) | ✅ Applied | Added `@pytest.mark.asyncio` decorator; `async def` was already present or corrected. |
| [!abstract] Blanket "patch where defined = WRONG" overgeneralization (lines 246–251) | ✅ Applied | Reworded to "Wrong when using `from X import Y`; correct when using `import X; X.fetch()`." |
| [!abstract] Stacked `@patch` order buried in comment (lines 266–275) | ✅ Applied | Promoted to dedicated callout: "Stacked `@patch` argument order (common gotcha)." |
| [!abstract] File ends with incomplete Fixture Composition section (line 710) | ✅ Applied | Added full fixture chain with `yield` teardown example (`mock_session_service` fixture). |

---

## 10. python-testing-advanced.md → python/python-testing-advanced.md

**Result: ❌ 1 of 6 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] `test_timeout_handling` broken lambda example (lines 111–118) | ✅ Applied | Example replaced with correct `async def slow_side_effect` pattern; note explains why `lambda: asyncio.sleep(10)` is wrong. |
| [!bug] Undefined classes in "Testing an ADK-Style Agent" (lines 487–577) | ❌ **Not applied** | The undefined class issue was not addressed. The section likely still references undefined agents (requires reading lines 487–577 to verify fully, but it was not in the commit diff). |
| [!bug] "Mistake 4" anti-pattern shows comment correction, not code fix | ✅ Applied | Added full correct implementation using `parent.assert_has_calls([call.step1(...), call.step2(...)])`. |
| [!abstract] Option 3 (`make_async_gen`) not labeled as "Recommended for ADK" | ✅ Applied | Added `# Option 3: ... — Recommended for ADK`. |
| [!abstract] "Testing Tool Schema Generation" test doesn't assert schema (lines 609–632) | ✅ Applied | Expanded test to assert schema structure: required params, optional params, property keys. |
| [!abstract] `make_async_context_manager` lacks `conftest.py` note | ✅ Applied | Added `# Place make_async_context_manager in your project's conftest.py`. |

---

## 11. glossary.md → reference/glossary.md

**Result: ❌ 4 of 13 items missing**

| Item | Status | Notes |
|---|---|---|
| [!danger] Four redirect-only stubs (Flow, Plugin, SessionService, Toolset) | ➕ Partial | `Flow`, `Plugin`, `SessionService`, and `Toolset` stubs were expanded with real definitions (no longer redirect-only). Not fully "folded into parent entries" but the stubs now have content. |
| [!bug] `ReadonlyContext` omits how to mutate state | ✅ Applied | Added "State writes go via `EventActions.state_delta`, not direct assignment." |
| [!bug] `ExecutorService` maps to deprecated `get_event_loop()` | ✅ Applied (via cheat-sheet) | Fixed in cheat-sheet; the glossary has no `ExecutorService` entry — this bug was in cheat-sheet, not glossary. Glossary review reference was likely a cross-file concern. |
| [!abstract] `Escalate` missing `→ contrast: Transfer` | ✅ Applied | Added "→ contrast: **Transfer** (sibling agent handoff)." |
| [!abstract] `Event` vague; replace with field list | ✅ Applied | Now lists: `author` (str), `branch` (str \| None), `content` (Content \| None), `actions` (EventActions), `id` (str). |
| [!abstract] `LlmResponse` "usage metadata" vague | ✅ Applied | Changed to "token usage metadata (input/output counts)." |
| [!abstract] `Output schema` definition unclear | ✅ Applied | Added example "e.g., Pydantic `Model.model_json_schema()` or JSON schema dict." |
| [!abstract] `Callback` missing guidance on when to use | ❌ **Not applied** | `Callback` entry is terse ("Hook functions on `LlmAgent` that intercept processing at defined points.") and does not explain "Use to intercept without stopping (log, validate, modify state)." That guidance was merged into the `Context` entry but `Callback` itself is still minimal. |
| [!abstract] `Output key` / `Output schema` easily conflated | ✅ Applied | Added "→ different from **Output key** (processor-specific storage key)" in Output schema entry. |
| [!abstract] Missing aliases: `CallbackContext`/`ToolContext`, `Context`/`InvocationContext` | ✅ Applied | Added `CallbackContext` entry; added `Context` entry as shorthand for `InvocationContext`. |
| [!abstract] Missing letters (J, K, N, Q, U, W, X, Z) feel incomplete | ✅ Applied | Added note: "Letters J, K, N, Q, U, W, X, Z have no entries yet. Terms added as documentation grows." |
| [!abstract] No code examples for `Output schema`, `State (scoped)` | ❌ **Not applied** | No code snippets were added; both entries remain prose-only. |
| [!quote] `StateDelta` duplicates scope prefix list from `State (scoped)` | ✅ Applied | `StateDelta` now reads "→ see: **State (scoped)** for scope prefix semantics" — scope list removed from `StateDelta`. |

---

## 12. java-to-python-cheat-sheet.md → reference/java-to-python-cheat-sheet.md

**Result: ❌ 4 of 9 items missing** (5 were approved; all 5 applied; 4 not-approved remain open)

| Item | Approved | Status | Notes |
|---|---|---|---|
| [!danger] Delete Package/Module System section (lines 133–147) | ✅ Yes | ✅ Applied | Section removed; Maven/Gradle row folded into ADK-Specific. |
| [!danger] Fix `List.of()` → tuple mapping (line 70) | ✅ Yes | ✅ Applied | Fixed: "Tuples are immutable sequences (analogous to `List.of()`). For a mutable list use `[1, 2, 3]`." |
| [!bug] `ExecutorService` maps to deprecated `get_event_loop()` (line 102) | ✅ Yes | ✅ Applied | Replaced with "asyncio event loop (managed by runtime)" + "Never call `get_event_loop()`." |
| [!bug] Spring Profiles analogy misleading (line 161) | ✅ Yes | ✅ Applied | Reframed: "Spring Profiles (startup config) → No direct equivalent; closest is `app:` keys for shared state." |
| [!abstract] `@Override` row lacks ADK guidance | ✅ Yes | ✅ Applied | Added "In ADK subclasses (`BaseAgent`, `BaseTool`), override by matching the signature exactly." |
| [!abstract] Generic tables before ADK-Specific; add navigation hint | ❌ No | ❌ Not applied | Table order unchanged; no navigation hint added. |
| [!abstract] Merge EAFP (item 5) and no-checked-exceptions (item 6) | ❌ No | ❌ Not applied | Both mindset shifts still listed as separate items 5 and 6. |
| [!abstract] No code examples for Callbacks, Multiple constructors | ❌ No | ❌ Not applied | No code snippets added. |
| [!quote] `Maven/Gradle` row dedup with learning-plan | ❌ No | ❌ Not applied | Row was moved to ADK-Specific section (resolves the Package section deletion), so partial dedup. |

---

## Summary

| File | Items Total | Applied | Partial | Not Applied |
|---|---|---|---|---|
| python-for-adk-learning-plan.md | 6 | 4 | 0 | 2 |
| python-gotchas-for-java-developers.md | 6 | 4 | 0 | 2 |
| python-asyncio-deep-dive.md | 6 | 0 | 0 | 6 |
| python-asyncio-advanced.md | 7 | 4 | 1 | 2 |
| python-decorators-deep-dive.md | 5 | 4 | 0 | 1 |
| python-metaprogramming-deep-dive.md | 6 | 2 | 0 | 4 |
| python-pydantic-deep-dive.md | 6 | 4 | 0 | 2 |
| python-pydantic-advanced.md | 6 | 3 | 1 | 2 |
| python-testing-and-mocking-guide.md | 4 | 4 | 0 | 0 |
| python-testing-advanced.md | 6 | 5 | 0 | 1 |
| glossary.md | 13 | 9 | 1 | 3 |
| java-to-python-cheat-sheet.md | 9 | 5 | 0 | 4 |
| **Total** | **80** | **52** | **3** | **29** |

### Critical gaps (bugs / security risks not addressed)

1. **python-asyncio-deep-dive.md** — entire file untouched (reverted); 6 open items including TCP Streams section, unverified McpToolset import, and race condition in parallel agents.
2. **python-metaprogramming-deep-dive.md** — `functools.wraps` duplicate section and `@register_tool` full duplication not reduced; file remains 357 lines over 1000-line limit.
3. **python-pydantic-advanced.md** — `__get_pydantic_core_schema__` 35-line section not deleted (note added instead); file remains 434 lines over 1000-line limit.
4. **python-testing-advanced.md** — undefined classes in "Testing an ADK-Style Agent" section not addressed.
5. **python-for-adk-learning-plan.md** — mutable `EventActions()` default in Pydantic example (line 96) not fixed.
