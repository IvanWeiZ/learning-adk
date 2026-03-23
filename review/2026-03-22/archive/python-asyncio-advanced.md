# Review: python-asyncio-advanced.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 448–481 (Section 14: asyncio Streams) repeats TCP networking section from deep-dive file; zero ADK relevance.
>
> **Action:** Remove ~35 lines; if included in deep-dive, it's not needed here.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 652–688 runner loop example yields same event twice (lines 682 and 684); lacks return type annotation.
>
> **Action:** Fix double-yield logic error and add `-> AsyncGenerator[Event, None]` return type.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 596–631 CircuitBreaker class uses `asyncio.get_running_loop().time()` in `__init__` (fails outside coroutine) and lacks `asyncio.Lock` for concurrent access.
>
> **Action:** Add lock protection or mark as "simplified, not production-safe."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 789–814 Java→Python table maps `Mono<T>`/`Flux<T>` to "Coroutine/AsyncGenerator" without explaining pull-based vs push-based difference.
>
> **Action:** Add sentence explaining asyncio is pull-based (unlike Reactor).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** File opens abruptly at "### 9. Synchronization Primitives" without summary of what Sections 9–18 cover.
>
> **Action:** Add introductory sentence listing file scope to help readers scan.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 555–568 bounded concurrency pattern (Session 16) is most practically useful for ADK rate limits but lacks emphasis.
>
> **Action:** Add callout noting this pattern directly applies to LLM rate limiting.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Section 18 (Java→Python mapping) partially duplicates quick reference table in deep-dive file.
>
> **Action:** Keep Section 18 (more complete); trim quick reference in deep-dive file.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Contains most practically useful ADK patterns (session locking, concurrent tools, callbacks, bounded concurrency) but quality is uneven. CircuitBreaker has concurrency bug, runner loop has double-yield error, TCP streams adds no value. Java comparison table in Section 18 is excellent. File reads as two merged files: strong ADK patterns (Sections 16–17) and broad synchronization reference (Sections 9–12). Tightening Sections 9–12 to just Lock, Semaphore, Queue (the three actually used in ADK) would improve signal-to-noise significantly.
