# Review: 04-agents.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 37-47 duplicate the At-a-Glance diagram; adds only that `Agent` is a type alias.
>
> **Action:** Delete the section; move the type alias note to the At-a-Glance prose.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 380-393 are a third pass over transfer mechanics already covered in prior sections; the unique fact (branch behavior) is in the diagram at line 317.
>
> **Action:** Delete the section.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** Three of four agent types (`LoopAgent`, `ParallelAgent`, `SequentialAgent`) receive no substantive treatment; `17-concurrency.md` covers `ParallelAgent` better.
>
> **Action:** Add dedicated sections for composition agents with fields, examples, and gotchas, or split to a companion file.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 138-151 present a condition tree with the default case (`AutoFlow`) at the bottom, making interpretation unclear; prose comes after, not before.
>
> **Action:** Move the prose explanation before the diagram.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 173-177 embed a 3-line workaround block mid-field-list, breaking scanning rhythm.
>
> **Action:** Move the workaround to the Gotchas section where `output_schema` is already mentioned.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** `InvocationContext` (lines 229-268) is front-loaded before `LlmAgent` depth coverage; it's infrastructure needed only for callbacks.
>
> **Action:** Move it to just before "Agent Trees and Transfer" where it becomes relevant.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Examples section covers only `LlmAgent` routing; composition agents are entirely absent.
>
> **Action:** Add construction examples for each composition agent type.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** The "Minimal Multi-Agent Example" (lines 399-413) is too thin; no explanation of what `search_flights` and `get_weather` do.
>
> **Action:** Replace with a composition agent example or expand inline.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 229-268 partly duplicate `03-runners.md` (context construction and service injection).
>
> **Action:** Keep the field reference table; cut the narrative and cross-reference `03-runners.md`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> `04-agents.md` is a solid, well-structured reference for `LlmAgent` specifically — transfer mechanics, flow selection, shared-vs-isolated context diagram, and the 3-layer transfer example are genuinely useful and clearly written. The main weakness is that three of the four advertised agent types receive no substantive treatment: they appear once in the class hierarchy and then nowhere else, leaving learners to piece together behavior from `02-when-to-build-what.md` and `17-concurrency.md`. Targeted expansion on composition agents, removal of the duplicate class hierarchy diagram, and trimming of the redundant "Branch in Events" section would raise this to a 9/10.
