# Review: 18-session-lifecycle.md

> [!info] Score: 6/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 354-562 ("Beyond Session Service: Full-Stack Latency Optimization") covers model selection, streaming, and compaction — out of scope for session lifecycle — and duplicates `debugging-guide.md` almost point-for-point, pushing file to 603 lines (3 over limit).
>
> **Action:** Delete the entire section; readers can cross-reference `debugging-guide.md` for latency optimization.
>
> - [ ] Approved
> - [ ] Denied
> - [x] Comment:  move it session latency optimization md also for  ### Optimizing for Latency (When Persistence Is Not Critical)


> [!bug] Bug
> **Issue:** Lines 214-284 show skeleton code with bare `# ... insert event rows ...` placeholder (lines 282-283).
>
> **Action:** Complete the `_flush` method or add explicit note: "implementation omitted for brevity."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 128-149 defer state scoping to `08-sessions.md` then immediately show a delta flow diagram, suggesting completeness.
>
> **Action:** Move state scoping content here or remove the diagram and explicitly defer to `08-sessions.md`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 14-17 label steps 4 and 5 identically as "append_event(agent)" with loop comment, implying sequence.
>
> **Action:** Collapse into: `4+. append_event(agent) — one per non-partial event`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 107-118 label optional paths as "Call 5" and "Call 6," suggesting they're mandatory sequential steps.
>
> **Action:** Rename to "Optional: append_event — plugin early exit" and "Optional: append_event — rewind."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 222-244 (FastSessionService) show code without caveat about missing edge cases.
>
> **Action:** Add one-line warning: "this is illustrative; missing edge cases like absent app/user state dicts."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 


> [!abstract] Structure
> **Issue:** "Latency Optimization Cheat Sheet" (lines 567-582) is a reference table under Examples, not code.
>
> **Action:** Move after "Decision Guide" (line 352) so readers see the summary before strategies; rename to `## Reference`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Excellent core content — `BaseSessionService` interface, `append_event` flow, state delta mechanics, locking, and five optimization strategies for session services themselves. The problem: second half pivots to general LLM latency, duplicates `debugging-guide.md` almost entirely, and pushes file over 600-line limit. Delete lines 354-562 and move the cheat sheet earlier; this becomes a tight, high-quality reference focused on session service internals.
