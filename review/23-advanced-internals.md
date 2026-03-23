# Review: 23-advanced-internals.md

> [!info] Score: 8/10

## Issues & Actions

> [!bug] Bug
> **Issue:** Lines 91–103 — `transfer_to_agent` JSON shows generic structure, not actual `FunctionDeclaration` ADK constructs.
>
> **Action:** Show real Python-constructed declaration or label as "conceptual illustration".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 160–175 — `_execute_tools_parallel` is fabricated pseudocode; learner grepping source won't find it.
>
> **Action:** Add first-line comment: `# Pseudocode — simplified from handle_function_calls_async()`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 198–239 — diagram shows asymmetric plugin ordering (before_* first, after_* last) but asymmetry is invisible; only explained later in Gotchas.
>
> **Action:** Annotate diagram: `← plugins FIRST for before_*, LAST for after_*`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 5–7 duplicate "Source:" and "Related:" already in standard line-3 header.
>
> **Action:** Remove freestanding block for consistency.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 31–74 — processor ⑦ "contents" description "filter events, handle branches" is vague.
>
> **Action:** Add one sentence: "only events on the current agent's branch are included in the message array".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** File has no "Examples" section; `MetricsPlugin` code (lines 244–288) is buried in "How It Works".
>
> **Action:** Move to new "Examples" section with heading.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** `MetricsPlugin` (lines 244–288) silently assumes `callback_context.state["temp:..."]` available in `before_run_callback`; context type differs from `tool_context`.
>
> **Action:** Clarify which context type is available in plugin callbacks vs agent callbacks.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Plugin callback order diagram (lines 198–239) overlaps with `10-apps.md` plugin lifecycle; detail level here (asymmetric ordering) justifies duplication but cross-reference would help.
>
> **Action:** Add cross-reference to `10-apps.md` for plugin API basics.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

## Summary

> [!tip] Summary
> Well-structured internals reference covering processor pipeline, reason-act loop, and plugin lifecycle. ASCII diagrams are the strongest in the series, especially the reason-act flowchart (lines 111–158). Main issues: two code blocks present pseudocode as source (violating repo's verify-against-source rule), and callback asymmetry is noted in text but not visually obvious in diagram. Fixing pseudocode labels and diagram clarity would make this genuinely reliable as a reference.
