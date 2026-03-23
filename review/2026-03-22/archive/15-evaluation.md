# Review: 15-evaluation.md

> [!info] Score: 8/10

## Issues & Actions

> [!bug] Bug
> **Issue:** Line 332 titles a section "Gotchas" but it contains a testing pyramid, decision table, and Java comparison — none are unexpected behaviors or traps.
>
> **Action:** Rename `## Gotchas` to `## When to Use Evals`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 193-209 use confusing inline annotation "✓ extra ✓" on line 198.
>
> **Action:** Replace with clear prose or numbered callout boxes.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 305-328 include three fragment JSON snippets with only field names and `...` placeholders that teach nothing.
>
> **Action:** Delete the three stub JSON blocks; the surrounding prose (lines 306, 317-328) stands on its own.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 158-163 duplicate the ASCII tree on lines 148-156 verbatim using different wording.
>
> **Action:** Delete either the prose list or the ASCII tree; keeping both adds length without clarity.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 176-177 repeats "Asserts internally — raises AssertionError" already stated on line 163.
>
> **Action:** Delete the duplicate sentence on line 176-177.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 211-220 mention "LLM judge" without specifying the default model or how to configure it.
>
> **Action:** Add one sentence: "Defaults to Gemini or is configurable via `EvalMetric.criterion`."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Writing Good Eval Cases" (lines 305-328) is a `###` subsection within Examples but contains general guidance, not example code.
>
> **Action:** Promote to its own `##` section between Examples and Gotchas, or fold into the context section.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Well-structured, immediately useful file. API reference section is the clearest in the repo (inline field comments vs. separate table). The `.test.json` example and pytest integration snippet are practical and complete. Main weaknesses: minor redundancy (ASCII tree + prose duplication, repeated AssertionError note) and weak placeholder examples that should be deleted. Rename the Gotchas section and make the clarity fixes; this becomes a 9/10 file.
