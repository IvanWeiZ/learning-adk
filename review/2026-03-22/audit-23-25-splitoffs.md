# Audit: Files 23–25 and Split-offs
**Date:** 2026-03-22
**Scope:** 11 files — current live versions vs. approved review items

---

## 1. `23-advanced-internals.md`

Review score: 8/10. All 8 items approved.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Bug** — Label `transfer_to_agent` JSON as conceptual illustration | ❌ | Block at lines 91–103 still shows the generic JSON dict with no label. No comment indicating it is pseudocode or a conceptual illustration. |
| 2 | **Bug** — Add `# Pseudocode — simplified from handle_function_calls_async()` to `_execute_tools_parallel` | ❌ | Lines 163–175: function is present with `# Inside handle_function_calls_async():` comment but the required pseudocode disclaimer is not there. |
| 3 | **Bug** — Annotate diagram with `← plugins FIRST for before_*, LAST for after_*` | ❌ | Diagram at lines 200–239 has no such annotation. The asymmetry is only mentioned in the Gotchas text below. |
| 4 | **Delete** — Remove freestanding `Source:` / `Related:` block (lines 5–7 of original) | ✅ | No freestanding block exists; file goes straight from line-3 header to `## At a Glance`. |
| 5 | **Clarity** — Add sentence to processor ⑦ contents: "only events on the current agent's branch are included" | ❌ | Line 48: description still reads `Filter events, handle branches` — the clarifying sentence was not added. |
| 6 | **Structure** — Move `MetricsPlugin` code to a new `## Examples` section | ❌ | `MetricsPlugin` (lines 244–288) is still under `## How It Works → 3. The Plugin System`. No `## Examples` section exists. |
| 7 | **Examples** — Clarify which context type is available in plugin vs. agent callbacks | ❌ | No clarification added to `MetricsPlugin` block or anywhere in the plugin section. |
| 8 | **Dedup** — Add cross-reference to `10-apps.md` for plugin API basics | ❌ | The `## Related` section at the bottom links to `10-apps.md` but does not specifically say "for plugin API basics". Marginal — the link is present; the specific label is absent. |

**Summary for file 1:** 1 of 8 approved items applied.

---

## 2. `24-faq.md`

Review score: 6/10. 5 items approved, 2 denied.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Delete** — Q2 "Testing" stub: provide real answer or remove | ❌ | Lines 182–185: Q2 is still a one-liner cross-reference with zero content: "For MockModel, InMemoryRunner… see [22-testing.md] and [22c-testing-examples.md]." No substantive answer added. |
| 2 | **Delete** — Six redundant ASCII diagrams | DENIED | Not applied (correctly, per denial). |
| 3 | **Split** — Extract Q4 "Message Passing" to `message-passing-patterns.md` | ❌ | Q4 (lines 389–609) remains in the file. No `message-passing-patterns.md` exists. File is 629 lines. |
| 4 | **Bug** — `callback_context.state._session` private attribute access: replace or document | ❌ | Lines 204–206 and 298: `_session` is used twice without any warning comment. Neither replacement nor documentation was added. |
| 5 | **Clarity** — Pattern C: explain how to implement `find_tool(new_name)` | ❌ | Lines 149–157: `find_tool(new_name)` is called without explanation. No implementation or explanation added. |
| 6 | **Structure** — Q5 "State Scopes" is two sentences; fill with 15–20 lines or remove | ❌ | Lines 612–614: Q5 is still two sentences and a cross-ref. No content was added. |
| 7 | **Dedup** — Q5 / Q3 cross-ref dedup | DENIED | Not applied (correctly, per denial). |

**Summary for file 2:** 0 of 5 approved items applied.

---

## 3. `25-adk-2.0-preview.md`

Review score: 7/10. 6 items approved, 1 denied, 1 comment ("keep but fix").

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Bug** — Fix `Prereqs: none` to `Prereqs: 04-agents.md, 05-flows.md` | ❌ | Line 3: header still reads `Prereqs: none`. |
| 2 | **Bug** — Document `output_schema=str` as 2.0-only addition | ❌ | Lines 64–96: `output_schema=str` is used but not flagged as 2.0-only. No contrast with 1.x `BaseModel` requirement. |
| 3 | **Bug** — Clarify whether 2.0 `Event` is same class as 1.x | ❌ | Lines 86–88: `Event(message=...)` used without any note. |
| 4 | **Comment** — Keep ASCII tree (lines 32–47) but fix it | ❌ | Lines 32–48: tree is present but appears unchanged. The review noted it should be fixed; no visible correction. |
| 5 | **Delete** — "Execution flow" ASCII (lines 136–143) | DENIED | Kept (correctly, per denial). |
| 6 | **Clarity** — Add "New in ADK 2.0" callout next to `output_schema=str` and `input_schema=` usages | ❌ | Lines 68, 82: no callout added. |
| 7 | **Structure** — Move "When NOT to Use 2.0" before examples | ❌ | "When NOT to Use 2.0" (lines 203–239) still comes after all examples. |
| 8 | **Examples** — Add note: "Production example: handling API timeouts with conditional routing" | ❌ | Error handling section (lines 154–183) has no such label or note. |
| 9 | **Dedup** — Consolidate three overlapping decision trees into one | ❌ | Lines 185–199 ("When to use Graph"), 203–215 ("Stay on 1.x when"), 217–239 ("Should you use 2.0?") all remain as three separate trees. |

**Summary for file 3:** 0 of 7 approved items applied (1 DENIED correctly kept, 1 comment item unchanged).

---

## 4. `23b-plugins-and-a2a.md` (was `plugins-and-a2a.md`)

Review score: 5/10. All 6 items approved.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Delete/Dedup** — Remove sections 6–15 (484 lines duplicating 8 dedicated files); keep only unique content | ❌ | Sections 6–15 are all present: Auth (§6), Artifacts (§7), Code Executors (§8), Planners (§9), A2A (§10), Event Compaction (§11), Content Filtering (§12), Function Call IDs (§13), Streaming (§14), Advanced Patterns (§15). File is 485 lines. |
| 2 | **Dedup** — (same action as above) | ❌ | Same as above. |
| 3 | **Bug** — `types.Schema(type="OBJECT")` string form: verify or add note | ❌ | Lines 36–38: `type="OBJECT"` and `type="STRING"` string forms used with no note about whether string form is valid or to use enum `types.Type.OBJECT`. |
| 4 | **Clarity** — AgentTool: add inline note "Each invocation creates a new session" | ✅ | Line 467 in Gotchas: "AgentTool creates isolated sessions — the child agent gets its own session and conversation history." Present and clear. |
| 5 | **Structure** — After pruning, keep only BaseTool → LongRunning → AgentTool → BaseToolset → A2A | ❌ | File still has 15 numbered sections. Not pruned. |
| 6 | **Examples** — Verify `types.Schema` string form or cite SDK version | ❌ | No verification note added. |

**Summary for file 4:** 1 of 6 approved items applied.

---

## 5. `24b-custom-use-cases.md` (was `custom-use-cases.md`)

Review score: 7/10. All 6 items approved.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Delete** — Data Flow diagram (lines 342–375 of original) duplicates per-option diagrams | ❌ | "Data Flow" section is still present at lines 341–375. Not deleted. |
| 2 | **Bug** — Fix `asyncio.gather(*tasks.values())` to properly await coroutines | ✅ | Line 116: `await asyncio.gather(*tasks.values())` is present but note the pattern `{k: (await v).json() for k, v in zip(tasks.keys(), await asyncio.gather(*tasks.values()))}` — the coroutines ARE awaited via `asyncio.gather`. Bug appears fixed. |
| 3 | **Dedup** — Replace `include_contents` and `before_model_callback` duplicate mentions with cross-references | ❌ | Lines 40–51 cover `include_contents` in detail (no dedup note/cross-ref added). Line 284 uses `before_model_callback` without referencing canonical source. |
| 4 | **Clarity** — Add inline warning to `_invocation_context` private field access | ❌ | Line 101: `callback_context._invocation_context` accessed with no warning. |
| 5 | **Structure** — Move comparison table before "Option A" | ❌ | Comparison table is at lines 327–338 (after all options), not before Option A. |
| 6 | **Examples** — Standardize imports to module-level | ❌ | Options B (lines 205–207) and C (line 284) use in-function `import httpx` while Option A uses module-level import. Inconsistency not fixed. |

**Summary for file 5:** 1 of 6 approved items applied.

---

## 6. `25b-adk-2.0-patterns.md` (was `adk-2.0-patterns.md`)

Review score: 5/10. 5 items approved, 1 denied.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Delete** — Migration Checklist (lines 248–305): replace with concrete breaking changes | ❌ | Migration Checklist (lines 248–305) is still present and unchanged. It still reads as venv hygiene guidance rather than breaking-change enumeration. |
| 2 | **Split** — Add paragraph explaining `@node` / `BaseNode` / `ctx.run_node()` relationship to parent file's `Workflow` graph API | ❌ | Dynamic Workflows section (lines 129–244) introduces `@node`, `BaseNode`, `ctx.run_node()` with no bridging paragraph. |
| 3 | **Dedup** — Replace mode comparison with cross-reference | DENIED | Mode comparison still present (correctly, per denial). |
| 4 | **Bug** — Add warning: "Import paths are beta; subject to change" to line 41 imports | ❌ | Line 40: `from google.adk.workflow.agents.llm_agent import Agent` has no beta/instability warning. |
| 5 | **Clarity** — Explain 2.0 transfer semantics before examples | ❌ | "Key difference from 1.x transfer" section (lines 111–125) appears AFTER the mode examples (lines 37–109), not before. |
| 6 | **Structure** — Move "Key difference from 1.x transfer" to before mode examples | ❌ | Section is still after the examples (line 111 vs examples starting line 37). |
| 7 | **Examples** — Show how coordinator receives and combines results from 3 agents | ❌ | Lines 88–109 (single_turn example): three agents defined, no code showing result collection from coordinator. |

**Summary for file 6:** 0 of 6 approved items applied.

---

## 7. `18b-session-latency-optimization.md`

No review — newly created file. No audit items.

---

## 8. `19b-security-checklist.md` (was `security-checklist.md`)

Review score: 8/10. All 5 items approved.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Bug** — `cleanup_expired_sessions` calls undefined `get_all_user_ids()` | ❌ | Line 84: `for user_id in await get_all_user_ids():` — still calls undefined function. No stub implementation or doc link added. |
| 2 | **Dedup** — Keep Built-In section; add note "See 19-session-security.md" for State Prefix | ❌ | State Prefix Quick Reference (lines 313–333) has no cross-reference note. |
| 3 | **Clarity** — GDPR: replace comment with numbered list of cleanup steps (artifacts, memory, credential store) | ❌ | Lines 117–118: `# Also clean up: artifacts, memory service entries, credential store` — still a single comment, not a numbered list. |
| 4 | **Structure** — Add `> [!danger]` callout before multi-tenant `app:` state pattern | ❌ | Lines 140–143: the warning about `app:` state being shared across tenants is in a plain code comment (`# DANGEROUS:`) and inline prose. No callout block added. |
| 5 | **Examples** — Replace inline password string with env var injection | ❌ | Lines 32–35: `db_url="postgresql+asyncpg://user:pass@db-host/adk_sessions"` — hardcoded credentials still present. No env var pattern used. |

**Summary for file 8:** 0 of 5 approved items applied.

---

## 9. `20b-debugging-guide.md` (was `debugging-guide.md`)

Review score: 6/10. All 7 items approved.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Delete** — "Testing Agents Effectively" section (lines 219–244): delete; replace with one-line cross-ref | ❌ | Section is still present at lines 219–244, including the non-runnable code with `Agent` and `InMemoryRunner` used without imports. |
| 2 | **Split** — Collapse repeated `include_contents` / `max_llm_calls` / `EventsCompactionConfig` into one "Performance" section | ❌ | Performance Checklist (lines 46–73) and Latency Optimization (lines 77–136) both cover the same content. Not collapsed. |
| 3 | **Dedup** — Delete testing section; compress model advice to one sentence | ❌ | Both duplication issues remain. |
| 4 | **Bug** — Line 229: `Agent` and `InMemoryRunner` used without imports | ❌ | Lines 229–237: `Agent` and `InMemoryRunner` used without import statements. |
| 5 | **Clarity** — Convert ASCII box borders (`┌─┐ └─┘`) to bullet list or tree | ❌ | "Performance Checklist" (lines 48–73) uses `┌─` box borders. Not converted. |
| 6 | **Structure** — Move Debugging Checklist + Common Scenarios before performance sections | ❌ | File order: Debugging Checklist (lines 9–41) → Performance Checklist (lines 45–73) → Latency Optimization (lines 77–136) → Common Debugging Scenarios (lines 140–216). Scenarios still come after performance content. |
| 7 | **Examples** — Change title from `# 20b — Debugging Guide` to `# Debugging Guide` | ❌ | Line 1: `# 20b — Debugging Guide: Checklist & Performance Optimization` — stale prefix not removed. |

**Summary for file 9:** 0 of 7 approved items applied.

---

## 10. `22b-testing-context-setup.md`

No review — newly created file (split from 22-testing review). No audit items.

---

## 11. `22c-testing-examples.md` (was `testing-examples.md`)

Review score: 6/10. 6 items approved, 1 denied.

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Delete** — Lines 27–48 call undefined private helpers; replace with note | ❌ | Lines 27–48 (Instruction Static/Callable/Async tests) use `_create_readonly_context` — this helper is referenced but not defined in the file. Still present without the replacement note. |
| 2 | **Delete** — Lines 153–188 call name-mangled `_LlmAgent__maybe_save_output_to_state` | ❌ | Lines 153–155 and 184–186: `agent._LlmAgent__maybe_save_output_to_state(event)` is called twice. Anti-pattern not removed. |
| 3 | **Split** — Split file if still over 600 lines after deletions | DENIED | Not applied (correctly, per denial). File is ~634 lines. |
| 4 | **Dedup** — Best Practices and Quick Reference: reduce to 3 bullets + reference | ❌ | Best Practices (lines 554–613) is full-length; Quick Reference (lines 616–634) is a complete table. Not reduced. |
| 5 | **Bug** — Line 137: invalid model ID `'gemini-pro'` | ❌ | Line 136: `parent = LlmAgent(name='parent', model='gemini-pro', ...)` — stale model ID still present. |
| 6 | **Bug** — Line 380: `TestInMemoryRunner` used without explanation; distinction only at line 623 | ❌ | Line 381: `runner = TestInMemoryRunner(agent)` used without inline note. Explanation still only at the Quick Reference table. |
| 7 | **Clarity** — Move `_TestingAgent` definition and `create_invocation_context` to top, before first use | ❌ | `_TestingAgent` class is defined at lines 495–511. First use is at lines 295–303 (callback tests). Not moved to top. |
| 8 | **Structure** — Move Quick Reference to top as navigation guide | ❌ | Quick Reference is at lines 616–634 (bottom of file). Not moved. |

**Summary for file 11:** 0 of 8 approved items applied.

---

## Overall Summary

| File | Approved Items | Applied | Missed |
|------|---------------|---------|--------|
| 23-advanced-internals.md | 8 | 1 | 7 |
| 24-faq.md | 5 | 0 | 5 |
| 25-adk-2.0-preview.md | 7 | 0 | 7 |
| 23b-plugins-and-a2a.md | 6 | 1 | 5 |
| 24b-custom-use-cases.md | 6 | 1 | 5 |
| 25b-adk-2.0-patterns.md | 6 | 0 | 6 |
| 18b-session-latency-optimization.md | — | — | No review |
| 19b-security-checklist.md | 5 | 0 | 5 |
| 20b-debugging-guide.md | 7 | 0 | 7 |
| 22b-testing-context-setup.md | — | — | No review |
| 22c-testing-examples.md | 8 | 0 | 8 |
| **Total** | **58** | **3** | **55** |

**3 of 58 approved items were applied. 55 items remain unaddressed.**

### High-priority missed items (bugs that produce wrong/misleading output)

1. `23-advanced-internals.md` — pseudocode not labeled (readers will grep source and fail)
2. `24-faq.md` — `_session` private attribute used twice without warning
3. `24-faq.md` — `find_tool()` called without implementation guidance
4. `25-adk-2.0-preview.md` — `Prereqs: none` is wrong; file assumes agents/flows knowledge
5. `23b-plugins-and-a2a.md` — `types.Schema(type="OBJECT")` string form unverified
6. `19b-security-checklist.md` — `get_all_user_ids()` undefined; hardcoded DB password in security doc
7. `20b-debugging-guide.md` — Testing section has missing imports (non-runnable code)
8. `22c-testing-examples.md` — `gemini-pro` is not a valid model ID; name-mangled method calls are anti-patterns
