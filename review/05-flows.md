# Review: 05-flows.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 65-80 "Two Iterations in Practice" trace duplicates the preceding flowchart (lines 37-63) using the same weather example; the prose trace adds no new information.
>
> **Action:** Delete the section entirely; tightens file by ~16 lines without losing content.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 167-170 "Live Mode" section mentions `run_live(ctx)`, `model.connect()`, and `LiveRequestQueue` without explaining when or why to use it, which models support it, or how the event loop differs; three lines raising questions without answers.
>
> **Action:** Either delete entirely or expand with at least one paragraph explaining trigger, model support, and event loop differences.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 9 mentions `_llm_flow` without explaining what it is or when it's assigned.
>
> **Action:** Add one sentence: `LlmAgent` selects and assigns the flow at construction time based on its configuration.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 29-32 describe `SingleFlow` conditions differently than `23-advanced-internals.md` line 77; could confuse readers switching files.
>
> **Action:** Add a parenthetical note cross-referencing the relationship between `SingleFlow` and `AutoFlow`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 143-158 list cache and Live API fields without explaining when they apply.
>
> **Action:** Add one sentence: cache fields apply only when context caching is enabled; `live_connect_config` applies only to Live API.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 152-163 use arrow syntax (`→`) inconsistently as both label separator and causal connector.
>
> **Action:** Standardize arrow usage throughout the trace.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Lines 173-180 duplicate `13-auth.md` (lines 23-41); adds only that the flow yields the auth event.
>
> **Action:** Delete the section or collapse to one line in "Response Processors"; cross-reference `13-auth.md`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** No Python code examples; traces use pseudo-format, not real ADK syntax.
>
> **Action:** Add one short code example showing a tool-use turn with real `async for event in runner.run_async(...)` syntax.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 124-147 list only 5 of 12 processors in `23-advanced-internals.md` lines 32-88; stale and incomplete.
>
> **Action:** Replace tables with a summary and forward reference, or sync the lists completely.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 173-180 "Auth Flow" duplicates `13-auth.md` lines 17-41 almost exactly; the 13-auth.md version is more detailed and correct.
>
> **Action:** Collapse to single line pointing to `13-auth.md`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> 05-flows.md is a competent, well-structured overview of the reason-act loop. Core content — flow variants, loop diagram, processor pipeline, tool dispatch trace — is accurate and useful. Main weaknesses are internal redundancy (flowchart and "Two Iterations" trace cover the same ground twice), shallow sections that raise questions without answering them ("Live Mode"), and processor tables that are a stale subset of `23-advanced-internals.md`. Fixing these three issues — merging or cutting the duplicate trace, expanding or deleting "Live Mode", and replacing incomplete processor tables with a forward reference — brings this from a solid 7 to a tight, trustworthy 9.
