# Review: 10-apps.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 278–290 ("Basic Usage") duplicates the Examples section code snippet.
>
> **Action:** Remove; Examples section is sufficient.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** Plugin Callback Execution Chain diagram (lines 189–239) conflates plugin-to-plugin execution order (horizontal) with lifecycle stage order (vertical) at same nesting level.
>
> **Action:** Separate the two orderings or add one sentence explaining why agent's own callback trails plugins (the precedence rule).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 111 — "All 11 callbacks" conflates lifecycle methods like `close()` with actual callbacks; unclear when `close()` fires vs others.
>
> **Action:** Clarify that `close()` is a lifecycle hook, not a callback; separate from the 11 event-driven callbacks.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Callback names in At a Glance box (lines 14–24), Class Hierarchy (lines 57–76), and BasePlugin Interface (lines 113–187) all list the same callbacks.
>
> **Action:** Trim At a Glance to just top-level App fields and note "BasePlugin has 11 callbacks (see class hierarchy below)".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** "App vs Bare Agent" table (lines 401–409) partially repeats At a Glance prose (line 41).
>
> **Action:** Keep table (more useful); trim line 41 feature enumeration.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 41 — "Without App: pass agent=; With App: pass app=" omits the footgun (easy mistake).
>
> **Action:** Show both Runner constructor signatures side-by-side.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 265 — "Requires `static_instruction` on `LlmAgent`" buried inline; dependency non-obvious.
>
> **Action:** Bold as note or callout; add link to `04-agents.md` explaining `static_instruction`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 111 — "A non-`None` return short-circuits remaining plugins" important invariant buried in prose; skimmable readers miss it.
>
> **Action:** Make this a bold note or callout box separate from API signature.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 330–335 — "Requires idempotent tool calls" stated with no explanation of why or what breaks if not idempotent.
>
> **Action:** Add: "Resuming a paused agent re-invokes previous tools; non-idempotent tools may double-execute or corrupt state."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Context cache has config section (lines 253–265) but no corresponding "How It Works" subsection, unlike other three features.
>
> **Action:** Either add brief conceptual paragraph or fold explanation into config block for consistency.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 353–367 (App with Compaction) duplicate EventsCompactionConfig example from lines 254–251 (Key API); one is redundant.
>
> **Action:** Keep Key API minimal (one-liner); move full wiring to Examples section.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 385–395 (App with Resumability) shows only config; no example of calling `run_async` a second time to resume.
>
> **Action:** Add second code block showing how caller invokes resume (e.g., loop with pause event check).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Line 285 — `gemini-2.5-flash` should be verified as real, current model ID per CLAUDE.md lesson.
>
> **Action:** Verify model name against Google's current model list before publication.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Main weaknesses: redundant callback listings, Resumability section lacks resume example, callback execution-chain diagram conflates two concerns. Fix these for stronger reference.
