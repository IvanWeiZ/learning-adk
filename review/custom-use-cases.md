# Review: custom-use-cases.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 342–375 (Data Flow diagram) duplicates per-option diagrams at lines 65–77 and 165–177.
>
> **Action:** Delete entirely.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** Lines 116, 295–296: `asyncio.gather(*tasks.values())` doesn't await coroutines; Option C is sequential not parallel.
>
> **Action:** Fix line 116 with proper `await asyncio.gather()` or `asyncio.create_task()` wrapping; verify parallelism in Option C.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** Lines 40–51 (`include_contents`) and line 284 (`before_model_callback`) duplicate existing docs.
>
> **Action:** Replace with one-sentence summary + cross-reference (e.g., "See 08-sessions.md for details").
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** Line 101 accesses private field `_invocation_context`; breaks on ADK refactors.
>
> **Action:** Add inline warning: "Private field; subject to change without notice."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** Comparison table (lines 327–338) appears after all options; readers need tradeoffs *before* code.
>
> **Action:** Move table before "Option A", then reference it per option.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Examples
> **Issue:** Option A uses module-level imports; Option B uses in-function imports — inconsistent.
>
> **Action:** Standardize on module-level imports.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> Practical three-option structure. Main issues: concurrent-HTTP bug (gather/await), private-field warning, inconsistent imports, and redundant diagram. Move comparison table before options. After fixes, strong reference.
