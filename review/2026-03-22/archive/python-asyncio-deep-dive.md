# Review: python-asyncio-deep-dive.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 447–481 (Section 14: asyncio Streams) covers TCP client/server not used in ADK.
>
> **Action:** Remove ~35 lines; section itself says "rarely needed directly in ADK."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 796–816 reference `from google.adk.tools import McpToolset` without verifying import path against actual ADK source.
>
> **Action:** Verify import path against google/adk source or mark as pseudocode.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 662–688 parallel agents pattern has race condition and loses streaming benefit (buffers all events until tasks finish).
>
> **Action:** Explain streaming loss and add comment about why TaskGroup prevents true streaming.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 31–32 say "no locks, no context-switch overhead" but asyncio does context-switch at `await` points; lacks OS-level thread switching.
>
> **Action:** Add sentence distinguishing Python-level from OS-level context switching.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 647–659 label `async yield from` as "SyntaxError" but root issue is deeper; sequential agent cannot yield while awaiting sub-generator.
>
> **Action:** Explain that Python requires you to consume the full sub-generator before yielding again (no interleaving).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 339–369 show "Fire and Forget" bad pattern before correct pattern; reader may stop early.
>
> **Action:** Reorder to show correct pattern first.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> One of the two best files alongside the gotchas guide. Mental model diagrams are genuinely clarifying for Java developers; ADK streaming pattern (Section 7) is the most important section in the entire Python series. Weaknesses: TCP streams section adds no ADK value (delete), parallel agents pattern has race condition, one import path unverified. Organization is logical and progression from coroutines through tasks through generators is well paced.
