# Review: 14-planners.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 192-213 show a redundant ASCII box diagram ("RAW MODEL OUTPUT" vs "WHAT THE USER SEES") that duplicates the plain-text example above it (lines 171-190).
>
> **Action:** Delete the box diagram; the plain-text example already shows the structure clearly.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 149-165 ("Planner Integration with Flows" diagram) nearly duplicates "At a Glance" (lines 9-24) before readers have learned anything new.
>
> **Action:** Merge or remove one diagram; the second should only appear after the reader understands the first.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 96-101 contain a single-row `ThinkingConfig` table that adds formality without benefit.
>
> **Action:** Replace the table with a single sentence describing the `thinking_budget` field.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 105-106 state `build_planning_instruction` returns `None` for `BuiltInPlanner` without explaining why.
>
> **Action:** Add one sentence: "BuiltInPlanner skips instruction injection — it configures the model directly via `apply_thinking_config` instead."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** "At a Glance" diagram (lines 9-24) references internal class names (`_NlPlanningRequestProcessor`, `_NlPlanningResponse`) without explanation.
>
> **Action:** Add "(internal processor)" labels to the diagram.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 250-264 show inconsistent indentation on line 261 (`thinking_config=...` indented one extra level).
>
> **Action:** Align indentation to match the `BuiltInPlanner(` call above it.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Well-structured, accurate file covering planners completely. Main weakness: minor redundancy (two nearly identical diagrams, single-row table). Removing the box diagram and replacing the table with a sentence would noticeably tighten the file. The decision tree and custom planner example are the right level of detail.
