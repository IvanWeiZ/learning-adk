# Review: python-testing-and-mocking-guide.md

> [!info] Score: 9/10

## Issues & Actions

> [!bug] Bug
> **Issue:** Lines 612–616 `test_llm_call(mock_llm)` lacks `async def` and `@pytest.mark.asyncio` decorator; will not await correctly.
>
> **Action:** Change `def` to `async def` and add `@pytest.mark.asyncio` or note `asyncio_mode = "auto"` requirement.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 246–251 blanket statement "`patch('my_agents.http_client.fetch') ← WRONG`" ignores case where you import module itself.
>
> **Action:** Replace with "Wrong when using `from X import Y`; only correct when using `import X; X.fetch()`."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 266–275 stacked `@patch` decorator order ("bottom = first argument") buried in inline comment; common confusion source.
>
> **Action:** Promote to dedicated one-paragraph callout or warning box.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** File ends at line 710 with pointer to advanced file; last section (Fixture Composition) is least complete.
>
> **Action:** Add one more example showing fixture chain with teardown (yield) before split.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> One of the strongest files in the series. Mock type selection table, import graph ASCII diagram, and `side_effect` section are each individually worth reading. One broken async fixture example (missing `async def`) is a meaningful bug that will confuse readers who copy it. Decorator stacking order is a real gotcha deserving more prominence. Both issues are easy to fix. A Java developer will leave with practical command of pytest and mock directly applicable to ADK testing.
