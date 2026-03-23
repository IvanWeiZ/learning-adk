# Review: python-decorators-deep-dive.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 431–463 rate-limiting decorator uses `time.sleep()` blocking event loop; unsafe for async ADK code.
>
> **Action:** Delete the example or mark clearly as "sync-only, unsafe in async ADK code."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 555–567 `@classmethod` example has Java `//` comments inside Python code block, creating syntax error.
>
> **Action:** Remove Java comments from Python code block or delete example entirely.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 467–495 `@timeout` decorator uses `signal.SIGALRM` (Unix/macOS only); raises AttributeError on Windows.
>
> **Action:** Add `# Unix/macOS only — signal.SIGALRM not available on Windows` comment to example.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment:

> [!abstract] Clarity
> **Issue:** Line 846 claims schema generation is "**exactly** how ADK generates tool schemas" but ADK uses Pydantic, not manual type mapping.
>
> **Action:** Change to "This illustrates the concept ADK uses; ADK delegates to Pydantic's `model_json_schema()` for full type support."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** File has no "ADK in Practice" section mapping decorator concepts to ADK component names.
>
> **Action:** Add brief 5-row table linking decorator patterns to ADK tool schema generation.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Solid file covering functions-as-objects through closures to decorators correctly with appropriate Java comparisons. Inspect module section (Section 7) is the payoff and well executed, aside from overclaim about ADK schema generation. Main weaknesses: Unix-only timeout example, sync rate limiter that will cause problems in async ADK code, and inaccuracy about ADK's schema mechanism. File ends appropriately with pointer to metaprogramming file. A Java developer will understand Python decorators well by the end.
