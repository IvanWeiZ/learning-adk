# Review: 24-faq.md

> [!info] Score: 6/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Q2 "Testing" (lines 183–185) answered entirely with cross-reference; zero value as FAQ entry.
>
> **Action:** Provide a real 5–10 line answer or remove from file.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Six of 8 ASCII diagrams (lines 241–273, 363–385, 421–445, 510–531, 556–579, 582–608) restate code logic already visible in adjacent blocks.
>
> **Action:** Keep pattern comparison (lines 363–385); delete redundant state-passing diagram (lines 421–445) and others.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** Q4 "Message Passing" (lines 389–609) is 220 lines; file exceeds 600-line limit by 48 lines.
>
> **Action:** Extract to dedicated `message-passing-patterns.md`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 196–227 — `callback_context.state._session` accesses private attribute without warning.
>
> **Action:** Replace with public API or document that no public API exists for this use case.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Q1 Pattern C (lines 143–163) calls `find_tool(new_name)` without explaining how to implement it.
>
> **Action:** Explain implementation approach or provide helper function.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Q5 "Explain All State Scopes" (lines 612–614) is two sentences and a cross-ref; empty.
>
> **Action:** Answer in 15–20 lines (state scopes table from `08-sessions.md` fits) or remove.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Q5 state scopes duplicates `08-sessions.md` and `19-session-security.md`; Q3 Pattern B overlaps with `23-advanced-internals.md` plugin patterns.
>
> **Action:** Keep message-passing table (lines 582–608) which doesn't appear elsewhere; cross-ref others.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

## Summary

> [!tip] Summary
> The FAQ concept is sound and best content (Q1 tool versioning, Q4 message passing) is genuinely unique and valuable. File has grown unwieldy: 48 lines over limit, Q2 and Q5 are hollow redirects, private `_session` access is an anti-pattern, and redundant diagrams add bulk without clarity. Focused editing (cut redundant diagrams, fill or remove stub questions, fix API safety) would bring this to 9/10.
