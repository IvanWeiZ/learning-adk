# Review: testing-examples.md

> [!info] Score: 6/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 27–48 call undefined private helpers; non-runnable and teach anti-pattern.
>
> **Action:** Delete; replace with note: "Test instruction indirectly via `InMemoryRunner` and assert output."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!danger] Delete
> **Issue:** Lines 153–188 call name-mangled private method `_LlmAgent__maybe_save_output_to_state`; anti-pattern that breaks on refactor.
>
> **Action:** Delete; reference integration-level tests at lines 192–234 which cover same behavior properly.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!warning] Split
> **Issue:** File is 633 lines, 33 over 600-line limit.
>
> **Action:** After deletions, split at "Testing LlmAgent" vs "Testing Callbacks/Plugins" if still over; otherwise compress.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** Lines 554–577, 519–524, 526–551 all duplicate `22-testing.md`; Quick Reference (616–634) overlaps.
>
> **Action:** Reduce Best Practices to three bullets + reference; remove In-Memory Service Summary table.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** Line 137 uses invalid model ID `'gemini-pro'`.
>
> **Action:** Replace with real ID like `'gemini-2.5-flash'`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** Line 380 references `TestInMemoryRunner` without explanation; distinction only at line 623.
>
> **Action:** Add inline note: "TestInMemoryRunner creates fresh session per call (vs InMemoryRunner's single-call)."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** Lines 291–343 use `_TestingAgent` before it's defined (line 495); undefined reference.
>
> **Action:** Move `_TestingAgent` definition and `create_invocation_context` to top, before use.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** Quick Reference (616–634) and Best Practices (554–577) most useful but buried at end.
>
> **Action:** Move Quick Reference to top as navigation guide; readers jump to specific patterns.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> Comprehensive patterns undercut by 60 lines testing private/name-mangled methods (anti-pattern). `_TestingAgent` used before defined. Delete private-API tests, fix model ID, move helper to top, compress duplication. Becomes excellent reference.
