# Review: 11-memory.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 286–294 (Java Comparison table) — mappings strained; `BaseMemoryService` is not analogous to ORM `EntityManager`. Misleads Java devs more than helps.
>
> **Action:** Remove; Java comparisons belong in dedicated `java-to-python-cheat-sheet.md` reference file.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 237–244 (Pattern 1) calls `callback_context.add_session_to_memory()`, but `add_session_to_memory` is a `BaseMemoryService` method, not on callback context. Likely invented API.
>
> **Action:** Verify against source; if method is on service not context, show correct call pattern.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 252–259 (Pattern 2) mutates `system_instruction` with `+=`, but field is `str | list[Part]` or None; `+=` fails on list/None.
>
> **Action:** Show safe pattern (build new string, guard for None) or explain when `+=` is safe.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 132–147 — "Cross-Session Timeline" diagram severely misaligned; Session A/B labels on same line but content columns don't line up; `add_session_to_memory()` floats mid-frame.
>
> **Action:** Redraw with proper alignment or convert to vertical timeline format per repo diagram policy.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 13–20 (Session State vs Memory table) partially duplicates state-scoping in `08-sessions.md` (specifically `user:` prefix).
>
> **Action:** Keep table for "why" framing; link to `08-sessions.md` for full scoping rules.
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 212–225 (Decision Guide tree) partially duplicates session state branches in `08-sessions.md`.
>
> **Action:** Add note: "for full session state scoping rules, see 08-sessions.md" to prevent future drift.
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 9–10 — "memory stores searchable entries that persist across conversations" doesn't say *what* triggers storage; readers assume it's passive.
>
> **Action:** Add: "Storage is not automatic — requires explicit `add_session_to_memory()` call or callback."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 95–96 — "search is substring matching" doesn't specify case-sensitivity or exactness (vs fuzzy).
>
> **Action:** Add: "case-insensitive exact substring matching (not fuzzy)."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 190 — "Some apps do this automatically in an `after_agent_callback`..." vague and duplicates next section; either promote or delete.
>
> **Action:** Delete; Pattern 1 shows the callback approach clearly.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 208 — "ADK automatically injects `tool_context` when parameter named `tool_context`" applies to all tools, not memory-specific.
>
> **Action:** Move to `09-tools.md` or replace with single forward reference to it.
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Memory vs Session State — Decision Guide" (lines 212–225) appears *after* implementation details; conceptually answers "when do I need this?" — should come *before*.
>
> **Action:** Move to directly after "What It Is" (after line 21) to improve flow.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 183–188 (Saving a Session) fetches session by ID then saves; not the common pattern (readers already have Session from runner loop).
>
> **Action:** Show callback-based pattern first or add comment clarifying why refetch is needed.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 267–281 (Pattern 3) — f-string `f"{m.content.parts[0].text}"` has no format expression; equivalent to plain access.
>
> **Action:** Remove f-string wrapper or explain why it's used.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> State vs memory table is strong. Main weaknesses: likely invented API in Pattern 1, fragile code in Pattern 2, misaligned timeline diagram, weak Java comparison. Move decision guide earlier and fix these four issues.
