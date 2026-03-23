# Review: 20-best-practices.md

> [!info] Score: 7/10

## Issues & Actions

> [!bug] Bug
> **Issue:** "How It Works" heading (line 13) incorrectly implies internal mechanics; section contains rule list, not system explanation.
>
> **Action:** Rename to "Common Mistakes & Rules".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** "Anti-Pattern 3: Global Mutable State" (line 262) duplicates section 8 (lines 157–178) and line 294 Gotcha; same concept in three places.
>
> **Action:** Delete Anti-Patterns 1–3 block (lines 257–263) entirely.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** "Summary: Top 10 Rules" table (lines 268–282) appears under "Examples" heading but is a summary, not an example.
>
> **Action:** Move table to follow "At a Glance" section to function as navigation index.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 110 — `template.clone()` used without documentation of source or signature.
>
> **Action:** Add one-line note: `clone()` is a deep-copy method on `LlmAgent`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 117–133 — callback parameter tree diagram shows names but not types; readers cannot write type-annotated callbacks.
>
> **Action:** Add type annotations in parentheses after each parameter (e.g., `(CallbackContext)`; also show `return: None` for each).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Examples" section (line 266) contains only a summary table, not examples.
>
> **Action:** Rename to "Quick Reference".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Section 9 "Model Inheritance" (lines 181–193) lacks explanation of actual failure mode.
>
> **Action:** Explain how child override causes unexpected behavior, or delete the rule.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** State management section (lines 157–178) repeats `temp:` lifecycle and JSON-serializable requirement from `08-sessions.md`.
>
> **Action:** Keep only the parallel `output_key` race condition example and cross-reference `08-sessions.md` for full lifecycle.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

## Summary

> [!tip] Summary
> Solid practical reference with strong wrong/correct code patterns consistently applied. Main weaknesses are structural: "How It Works" misnames the section, "Examples" contains no examples, anti-patterns block is underdeveloped, and summary table should appear earlier as navigation. The content itself is highly useful for scanning common pitfalls.
