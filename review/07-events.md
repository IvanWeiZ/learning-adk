# Review: 07-events.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 139–147 repeat the At a Glance summary verbatim.
>
> **Action:** Delete the prose body; keep the box diagram.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 250–255 ("Examples" section) contains no code, only prose recap of the diagram from lines 151–172.
>
> **Action:** Replace with a runnable snippet showing `await runner.run_async()` iteration and `event.is_final_response()` check, or remove the heading.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 113–137 use opaque synthetic IDs like `"evt-002"` and `"e-inv-9f2a"` as labels.
>
> **Action:** Replace with descriptive labels ("Tool Call", "weather lookup result").
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** `is_final_response()` logic explained at lines 92–97 and repeated at line 259 (Gotchas).
>
> **Action:** Keep only in Key Methods block; remove the Gotchas restatement.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 35 — "Carries text, function calls, function responses, blobs, or thoughts" floats without field attachment.
>
> **Action:** Move into `content` field description in the class diagram.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 93–97 — inline `is_final_response()` comment spans three source lines, hard to parse.
>
> **Action:** Move comment to prose sentence after code block.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "How Events Flow End-to-End" (lines 224–246) largely repeats "Events in a Single Turn" (lines 149–172).
>
> **Action:** Merge them; keep the detailed version, rename to clarify streaming/persistence angle.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** "Examples" heading (line 250) delivers prose recap, not code.
>
> **Action:** Add 10-line snippet showing event consumption, `event.author` check, and `event.actions.state_delta` inspection.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> File has internal redundancy: same idea stated three times, two diagrams covering the same sequence, and `is_final_response()` explained twice. Cut duplicate prose, replace prose "Examples" with code, use descriptive labels.
