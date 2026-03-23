# Review: 22-testing.md

> [!info] Score: 9/10

## Issues & Actions

> [!bug] Bug
> **Issue:** Critical warning (lines 6–7) — `MockModel`, `InMemoryRunner`, `simplify_events` are NOT in pip package, buried below diagram where learners miss it.
>
> **Action:** Move to very top of file body before any code.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 193–225 — constructor inconsistency: line 206 uses positional `InMemoryRunner(agent)`, but lines 214–220 use keyword `root_agent=agent`.
>
> **Action:** Verify source signature and standardize one calling convention throughout.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 99–115 — `InMemoryRunner` and `TestInMemoryRunner` names are similar; distinction (sync reuse vs async per-call) is crucial but easily missed.
>
> **Action:** Add picker before table: "For most tests, use `InMemoryRunner` (multi-turn) or `TestInMemoryRunner` (isolated). Use `create_invocation_context` only for low-level unit tests."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** "Creating Dependencies" section (lines 297–418) covers infrastructure-level content (`create_invocation_context`, three `ToolContext` options) most learners won't need until integration tests.
>
> **Action:** Move to separate `testing-context-setup.md`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "What It Is" section (lines 44–48) arrives after diagram and example; redundant.
>
> **Action:** Fold into opening paragraph.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Line 164 — `MockModel.create(..., error=SystemError(...))` mentioned but never used in assertion.
>
> **Action:** Show short test using `pytest.raises` to catch the error.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

## Summary

> [!tip] Summary
> Strongest testing reference in the series. Production vs test stack diagram excellently orients learners, `MockModel.create()` is thoroughly documented, and three context creation options serve different experience levels. Main issues: buried package warning, confusing `InMemoryRunner` variant naming, and dense "Creating Dependencies" section. Fixing warning placement and adding a quick picker would make this immediately more usable.
