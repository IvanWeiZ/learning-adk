# Review: python-for-adk-learning-plan.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 481–499 duplicate Day 1–14 mappings already stated inline.
>
> **Action:** Remove "ADK in Practice" summary table entirely.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 91–99 shows `custom_metadata: dict[str, str] = {}` mutable default contradicting gotchas file.
>
> **Action:** Change to `Field(default_factory=dict)`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 251 claims ADK has `@tool` decorator; CLAUDE.md Lesson 4 confirms ADK has no decorator.
>
> **Action:** Change "ADK's `@tool`" to "tool registration patterns" and clarify ADK uses `FunctionTool()` constructor.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 7–28 diagram uses cryptic abbreviations (`│Pyd.│`, `│Adv.│`) violating CLAUDE.md lesson 10.
>
> **Action:** Replace side-by-side box diagram with plain numbered list.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Day 14 capstone targets 300–500 lines for someone finishing Day 13, unrealistic for single session.
>
> **Action:** Reframe as "multi-session project" rather than "single day."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 511–531 "Quick Reference Card" duplicates content in `reference/java-to-python-cheat-sheet.md`.
>
> **Action:** Replace with cross-reference link to cheat sheet.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Well-structured 14-day curriculum with correct topic order and Java mental-model framing. Main weaknesses: one factual error about ADK's decorator API, a mutable default in example code, a duplicated summary table, and unrealistic single-day capstone framing. The day-by-day flow and "Why ADK needs this" headers are exactly right for the target audience.
