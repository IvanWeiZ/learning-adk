# Review: python-gotchas-for-java-developers.md

> [!info] Score: 9/10

## Issues & Actions

> [!bug] Bug
> **Issue:** Lines 75–89 shows `ctx.state["available_tools"]` implying direct dict access; actual ADK has `session.state`.
>
> **Action:** Change variable name to `session_state` or add comment "simplified example."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 59–65 Java comparison for gotcha #2 doesn't highlight surprise for Java developers who know `clone()` is shallow.
>
> **Action:** Reframe to emphasize Python has no value-semantics types (no primitives like Java int[]).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Gotcha #9 (GIL) missing `asyncio.to_thread()` pattern for calling blocking code from async ADK tools.
>
> **Action:** Add code example showing `await asyncio.to_thread(blocking_func)` for blocking calls in async tools.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 415–416 module system example missing ADK-specific case: `import google.adk.*` fails in test environments without ADK.
>
> **Action:** Add note that importing ADK modules at file top may fail in test environments.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** 13 gotchas have no section grouping; gotchas 1–6 are semantics, 7–9 runtime, 10–13 object/module system.
>
> **Action:** Add one-line group headings above each cluster to improve scannability.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 142–152 show lambda closure fix with default-argument trick but omit `functools.partial` alternative.
>
> **Action:** Add one-sentence note that `partial()` is the production alternative.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> The strongest file in the series. Every gotcha is real, well-tied to ADK context, and the Java mental-model diagram is highly effective. Missing `asyncio.to_thread()` pattern and slightly misleading `ctx.state` accessor are minor gaps. Light section grouping would improve scannability. A Java developer reading this will recognize the traps described and be motivated to read all 13.
