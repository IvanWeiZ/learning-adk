# Audit: Files 14–22 — Applied vs Approved Changes

**Date:** 2026-03-22
**Method:** Read current `adk/` file and compare against every `[x] Approved` / `[x] Comment:` item in the corresponding archive review.

---

## 14-planners.md

**Review score:** 8/10. All 6 items had **no checkboxes marked** (`[ ] Approved`, `[ ] Denied`, `[ ] Comment` — all blank). No approved changes to apply.

**Result: N/A — nothing was approved in this review.**

---

## 15-evaluation.md

All 6 items were `[x] Approved`.

### Item 1 — Rename `## Gotchas` → `## When to Use Evals`
✅ Applied. Line 313: `## When to Use Evals` is present.

### Item 2 — Replace confusing "✓ extra ✓" annotation (lines 193–209) with clear prose or numbered callout boxes
✅ Applied. The current scoring example uses a plain ASCII diagram (`Step 1:`, `Step 2:`, `Extra:`) — no "✓ extra ✓" annotation present.

### Item 3 — Delete three stub JSON blocks (lines 305–328) with only field names and `...` placeholders
✅ Applied. The "Writing Good Eval Cases" section contains no stub JSON blocks; it now has prose guidance and one concrete `{ "name": "search_web", "args": {} }` example.

### Item 4 — Delete either prose list or ASCII tree at lines 148–163 (duplicate content)
✅ Applied. Current file has a single ASCII tree (lines 148–156) followed by one prose sentence — the duplicated list is gone.

### Item 5 — Delete duplicate "Asserts internally — raises AssertionError" sentence (lines 176–177)
✅ Applied. The comment appears only once (line 163/163 in the code comment context).

### Item 6 — Add one sentence clarifying LLM judge default model: "Defaults to Gemini or is configurable via `EvalMetric.criterion`."
✅ Applied. Line 213: "The LLM judge defaults to Gemini; configurable via `EvalMetric.criterion`."

### Item 7 — Promote "Writing Good Eval Cases" from `###` subsection under Examples to its own `##` section
✅ Applied. Line 298: `## Writing Good Eval Cases` is a top-level `##` section, no longer nested under Examples.

---

## 16-error-reference.md

All 6 items were `[x] Approved`.

### Item 1 — Delete entire "Gotchas" section (lines 225–232) — repeats How It Works verbatim
✅ Applied. No "Gotchas" section exists in the current file.

### Item 2 — Fix "Recommended Pattern" (lines 207–213): implement at least one recovery branch for 429s instead of sleep-and-re-raise
✅ Applied. The current `handle_model_error` function returns a fallback `LlmResponse` with user-facing text for 429/ResourceExhausted errors, with `return None` for all others.

### Item 3 — Remove duplicate "Minimum Error Handling" code — keep one copy in Examples only
✅ Applied. The Key API section contains only the error flow diagram; the code example appears once in Examples.

### Item 4 — Add missing imports (`Content`, `Part`) to the lambda at lines 70–75 or simplify to named function
✅ Applied. The current examples use named async functions (`handle_model_error`, `handle_tool_error`) with explicit imports at the top of the block.

### Item 5 — Promote "Also handles tool-not-found" (line 122) to sub-bullet or give it a heading
✅ Applied. Line 96: `> **Tool-not-found:**` is a blockquote callout under the Tier 1 table, clearly separated.

### Item 6 — Move code example from Key API to Examples; keep only diagram in Key API
✅ Applied. Key API contains only the error flow diagram and the Common Errors table. The code example is in Examples.

---

## 17-concurrency.md

All 6 items were `[x] Approved`.

### Item 1 — Delete entire "Gotchas" section (lines 198–206) — repeats How It Works verbatim
✅ Applied. No "Gotchas" section exists in the current file. (A "Related" section follows Examples directly.)

### Item 2 — Delete prose bullets (lines 160–164) that duplicate the ASCII thread-pool diagram above
✅ Applied. The ToolThreadPoolConfig diagram is present; no separate prose bullet list follows it.

### Item 3 — Trim "At a Glance" to top half (≤10 lines); move parallel-tool execution diagram to How It Works
✅ Applied. "At a Glance" is now ~12 lines covering Runner/session safety. The parallel tool execution diagram appears under `## How It Works → Parallel Tool Execution`.

### Item 4 — Clarify line 108: "keep running in the background" → "other coroutines continue to the next `await` point"
✅ Applied. Line 97: "Other coroutines continue to the next `await` point before cancellation (potential resource leak)."

### Item 5 — Add one sentence explaining "resume-signal"
✅ Applied. Line 121: "an `asyncio.Event` that notifies the parent when a sub-agent yields."

### Item 6 — Add inline comment showing the bad pattern (both tools writing same key) as contrast to the fix
✅ Applied. Lines 171–178 show the BAD pattern with `ctx.state["result"]` used by both tools, followed by the GOOD pattern with distinct keys.

---

## 18-session-lifecycle.md

1 item was `[x] Comment:`, 6 items were `[x] Approved`.

### Item 1 — Delete lines 354–562 ("Beyond Session Service")
**`[x] Comment:`** "move it session latency optimization md also for `### Optimizing for Latency (When Persistence Is Not Critical)`"

✅ Applied. The large latency section is gone from `18-session-lifecycle.md`. A new file `18b-session-latency-optimization.md` was created (confirmed present on disk). Line 158 cross-references it: "For latency optimization strategies (session service, model selection, streaming, tools), see [18b-session-latency-optimization.md](18b-session-latency-optimization.md)."

### Item 2 — Complete `_flush` placeholder or add "implementation omitted for brevity" note
❌ Not applied. The current file does not contain a `FastSessionService` or `_flush` placeholder — the custom implementation example (lines 214–284 of the original) appears to have been removed entirely along with the latency section. If that code was part of the deleted section, this item was resolved by deletion; if it should have been retained with the note added, it is missing.

> **Note for reviewer:** The `FastSessionService` skeleton (original lines 214–284) no longer appears in the current file. Verify whether it was intentionally removed as part of the latency section move or should have been preserved.

### Item 3 — Move state scoping content here or remove diagram and defer explicitly to `08-sessions.md`
✅ Applied. Line 128: "For state scoping rules, see [08-sessions.md](08-sessions.md)." — explicit defer, no diagram.

### Item 4 — Collapse duplicate "append_event(agent)" steps 4 and 5 into `4+. append_event(agent) — one per non-partial event`
✅ Applied. Line 15: `│ 4+. append_event(agent) — one per non-partial event`.

### Item 5 — Rename "Call 5" and "Call 6" to "Optional: append_event — ..." labels
✅ Applied. Lines 116–120: `**Optional: append_event — plugin early exit**` and `**Optional: append_event — rewind**`.

### Item 6 — Add warning on FastSessionService: "missing edge cases like absent app/user state dicts"
❌ Not applied (same issue as Item 2 — the FastSessionService code block is gone; the caveat was never added).

### Item 7 — Move "Latency Optimization Cheat Sheet" (lines 567–582) before Decision Guide; rename to `## Reference`
❌ Not applied. The cheat sheet is not present in the current file at all; it was apparently moved to `18b-session-latency-optimization.md` along with the rest of the latency content. If it was meant to remain in `18-session-lifecycle.md` as a `## Reference` table (per the approved action), it is missing.

> **Note for reviewer:** Items 2, 6, and 7 are all casualties of the section move. Whether they need to be re-applied in `18-session-lifecycle.md` or were intentionally relocated to `18b` should be confirmed.

---

## 19-session-security.md

1 item was `[x] Comment:`, 4 items were `[x] Approved`.

### Item 1 — Delete nested ASCII box diagram (lines 154–187); decision tree at 191–208 is cleaner
**`[x] Comment:`** "try to merge them"

❌ Not applied. The current file has no merged diagram. The state scoping section (lines 134–173) contains the source code extract (`extract_state_delta`) and a four-scope table, followed by a decision tree starting at line 164. The original nested ASCII box diagram does not appear, but the merge (combining box and decision tree into one cleaner diagram) was not done — the box was simply dropped and the tree retained. The comment asked for a merge, not a deletion.

### Item 2 — Add 3–5 line summary to "At a Glance" or remove the section heading
✅ Applied. Lines 7–14: "At a Glance" now has a 4-bullet summary of file contents.

### Item 3 — State `user_id` danger explicitly in opening sentence (not buried in code comment)
✅ Applied. Lines 71–72: "**Warning: list_sessions Can List ALL Users' Sessions**" with danger stated in the opening sentence of that subsection. The `user_id` optional danger in `list_sessions` is stated explicitly before any code.

### Item 4 — Add one sentence: "Branch is a dot-separated ancestor path in the agent tree."
✅ Applied. Line 220: `# Branch is a dot-separated ancestor path in the agent tree (e.g., "root.search.summarizer")`.

### Item 5 — Move callback closure statefulness bug example to `20-best-practices.md` or `17-concurrency.md`
✅ Applied. Lines 267–269: The section now contains only a single-sentence cross-reference: "Never capture mutable state in callback closures — use `session.state` instead... See [20-best-practices.md](20-best-practices.md) for the full wrong/correct pattern." The full code example is no longer in this file.

---

## 20-best-practices.md

6 items were `[x] Approved`, 1 item was `[x] Denied`.

### Item 1 — Rename "How It Works" → "Common Mistakes & Rules"
✅ Applied. Line 28: `## Common Mistakes & Rules`.

### Item 2 — Delete Anti-Patterns 1–3 block (lines 257–263)
✅ Applied. No "Anti-Pattern 1/2/3" block exists. The file goes from section 13 ("Description Field") directly to `### 14. Common Architecture Anti-Patterns` (which is empty — just a heading and `---`).

> **Note:** Section 14 heading with no content may be a residual artifact of the deletion. Verify if it should be filled or removed.

### Item 3 — Move "Summary: Top 10 Rules" table to follow "At a Glance" (as navigation index)
✅ Applied. Lines 11–24: The "Summary: Top 10 Rules" table immediately follows "At a Glance", before any section content.

### Item 4 — Add note: "`clone()` is a deep-copy method on `LlmAgent`"
✅ Applied. Line 117: "`clone()` is a deep-copy method on `LlmAgent` that creates a new independent instance. The `update` parameter accepts a dict of field overrides applied after copying..."

### Item 5 — Add type annotations to callback parameter tree diagram
✅ Applied. Lines 134–151: Each callback entry shows the full type-annotated signature (e.g., `callback_context: CallbackContext`, `tool: BaseTool, args: dict[str, Any], tool_context: ToolContext`).

### Item 6 — Rename "Examples" section → "Quick Reference"
✅ Applied. Line 285: `## Quick Reference`.

### Item 7 — Explain failure mode for Section 9 "Model Inheritance"
✅ Applied. Lines 200–201: "If **no ancestor** has a model and the child doesn't set one either, ADK raises a `ValueError` at runtime — not at construction time. This means the failure surfaces only when the child agent is actually invoked, which can be hard to debug in large hierarchies."

### Item (Denied) — Dedup state management section
Not applicable (denied).

---

## 21-advanced-patterns.md

All 7 items were `[x] Approved`.

### Item 1 — Add skeleton sections to match series format: "At a Glance", "What It Is", "Gotchas", "Related"
✅ Applied. The file now has `## At a Glance` (line 5), `## Gotchas` (line 489), and `## Related` (line 499). Note: "What It Is" was folded into the At a Glance paragraph rather than a separate section.

### Item 2 — Add ASCII flow diagram showing `ReflectAndRetryToolPlugin` retry loop
✅ Applied. Lines 117–151: A detailed ASCII flow diagram shows the retry loop with both callback paths (`on_tool_error_callback` and `after_tool_callback`), `_handle_tool_error`, counter logic, and success path.

### Item 3 — Add 2–3 sentences explaining the two-call contract for manual confirmation
✅ Applied. Lines 448–450: "The tool is called **twice**: on the first call it pauses execution and returns a pending status; on the second call (after the human responds), `tool_context.tool_confirmation` is populated with the approver's payload and the tool completes normally."

### Item 4 — Remove freestanding "Source:" / "Related:" block (lines 5–7) — duplicates line 3 header
✅ Applied. No freestanding Source block exists after the header. The file goes straight from the line 3 header to `## At a Glance`.

### Item 5 — Add comment to hardcoded city data in `output_schema` example: "simplified proof-of-concept"
✅ Applied. Lines 373–374: `# Simplified proof-of-concept: data is hardcoded in the instruction.` and `# In production, inject real data via a callable instruction or tool.`

### Item 6 — Move "Why not just return the data?" explanation before code block (Pattern 3)
✅ Applied. Lines 170–175: The "Why not just return the data?" explanation appears before the `QueryLargeDataTool` code block.

### Item 7 — Add cross-reference note to `10-apps.md` for `ResumabilityConfig`
✅ Applied. Line 473: "`ResumabilityConfig` is part of the `App` container layer — see [10-apps.md](10-apps.md) for full `App` configuration options including plugins and compaction."

---

## 22-testing.md

All 6 items were `[x] Approved`.

### Item 1 — Move package availability warning to very top of file before any code
✅ Applied. Lines 5–6: The warning appears as the second line of the file body (immediately after the header on line 3), before the production vs test stack diagram.

### Item 2 — Standardize `InMemoryRunner` constructor calling convention (positional vs keyword)
✅ Applied. Lines 217–218 and 226–227 both use `root_agent=agent` (keyword argument). The positional form is gone.

### Item 3 — Add quick picker before the runner variant table
✅ Applied. Lines 47–48: "**Quick picker:** For most tests, use `InMemoryRunner` (multi-turn, session reuse) or `TestInMemoryRunner` (isolated, new session per call). Use `create_invocation_context` only for low-level unit tests..."

### Item 4 — Move "Creating Dependencies" section (lines 297–418) to separate `testing-context-setup.md`
✅ Applied. File `22b-testing-context-setup.md` exists on disk. Line 307: "*Context setup patterns (`create_invocation_context`, `ToolContext`, `ReadonlyContext`, manual `InvocationContext`) have been moved to [22b-testing-context-setup.md](22b-testing-context-setup.md).*"

### Item 5 — Fold "What It Is" section (lines 44–48) into opening paragraph
✅ Applied. No standalone `## What It Is` section exists. The description is integrated into the opening paragraph starting at line 7.

### Item 6 — Show `pytest.raises` test for `MockModel.create(error=SystemError(...))`
✅ Applied. Lines 166–178: A complete `test_model_error_propagates` function using `pytest.raises(SystemError, match='API down')`.

---

## Summary

| File | Approved Items | ✅ Applied | ❌ Missing | N/A / Denied |
|------|---------------|-----------|-----------|--------------|
| 14-planners.md | 0 (nothing approved) | — | — | 6 items unapproved |
| 15-evaluation.md | 6 | 6 | 0 | 0 |
| 16-error-reference.md | 6 | 6 | 0 | 0 |
| 17-concurrency.md | 6 | 6 | 0 | 0 |
| 18-session-lifecycle.md | 6 + 1 comment | 4 | 3* | 0 |
| 19-session-security.md | 4 + 1 comment | 4 | 1* | 0 |
| 20-best-practices.md | 6 | 6 | 0 | 1 denied |
| 21-advanced-patterns.md | 7 | 7 | 0 | 0 |
| 22-testing.md | 6 | 6 | 0 | 0 |

### Items Requiring Follow-Up

**18-session-lifecycle.md (3 items):**
- ❌ `FastSessionService._flush` placeholder note ("implementation omitted for brevity") — code block removed, note never added. Verify if `FastSessionService` should be restored in the main file or lives in `18b`.
- ❌ FastSessionService caveat warning about missing edge cases — same situation.
- ❌ "Latency Optimization Cheat Sheet" was supposed to be promoted to `## Reference` in `18-session-lifecycle.md`. It is absent from the current file (likely moved to `18b`). If it was meant to stay as a `## Reference` section in `18`, it needs to be added back.

**19-session-security.md (1 item):**
- ❌ Comment said "try to merge them" (merge the nested ASCII box diagram with the decision tree). The box was dropped and only the decision tree retained — no merge was attempted. A merged diagram showing both scope structure and decision logic should be created.
