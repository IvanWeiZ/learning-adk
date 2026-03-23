# Review: 16-error-reference.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 225-232 ("Gotchas" section) repeat every point already covered in "How It Works" (lines 130-131, 173, 177-179, 144-146, 163) verbatim.
>
> **Action:** Delete the entire section; absorb any critical warnings as inline callouts where concepts are first explained.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 207-213 show a "Recommended Pattern" that sleeps and re-raises without demonstrating actual recovery.
>
> **Action:** Implement at least one recovery branch (e.g., retry or return fallback `LlmResponse` for 429s).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 64-89 duplicate "Minimum Error Handling" code example later as "Recommended Pattern" (lines 185-221) under Examples.
>
> **Action:** Remove one copy; move remaining code to Examples section and remove duplicate structure.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 70-75 lambda is missing imports for `Content`, `Part` — readers copying it will hit `NameError`.
>
> **Action:** Add required imports or simplify to a named function.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 


> [!abstract] Structure
> **Issue:** Line 122 ("Also handles tool-not-found") appears as an orphaned paragraph with no heading or visual separation.
>
> **Action:** Promote to a sub-bullet under recovery pipeline or give it a `#### Tool-Not-Found` heading.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Key API" section (lines 44-89) mixes diagram with code example that duplicates the Examples section.
>
> **Action:** Move the code example to Examples; keep only the diagram in Key API.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Well-scoped, practical file covering a genuinely tricky part of ADK. The three-tier framing (Recoverable/Fatal/Silent) and ASCII flow diagram are clear. Main structural flaw: the "Gotchas" section duplicates every point from "How It Works" without adding information. Second problem: "Recommended Pattern" example shows a no-op handler (sleep then re-raise) which will actively mislead readers trying to implement 429 recovery. Fix those two issues and this becomes 9/10.
