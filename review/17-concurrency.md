# Review: 17-concurrency.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 198-206 ("Gotchas" section) repeat every point already covered in "How It Works" (lines 105-164) with nearly identical wording.
>
> **Action:** Delete the entire section; add critical warnings as inline callouts where concepts are first explained.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 160-164 (bullet list) duplicate the ASCII thread-pool diagram immediately above (lines 138-158) showing the same four execution paths.
>
> **Action:** Delete the prose bullets; the diagram conveys the information more clearly.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "At a Glance" (lines 9-32, 24 lines) exceeds the recommended 5-10 line limit and embeds a "Parallel Tool Execution" subsection that belongs in "How It Works."
>
> **Action:** Trim to the top half only (lines 10-17, Runner/session safety); move parallel-tool execution diagram to How It Works.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 108 phrase "keep running in the background" may mislead readers into thinking coroutines run independently after `gather` returns.
>
> **Action:** Clarify: "the exception propagates from `gather`; other coroutines continue to the next `await` point."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 133 states "Events serialize via `asyncio.Queue` + resume-signal" without explaining what a "resume-signal" is.
>
> **Action:** Add one sentence: "A resume-signal is [brief definition or source reference]."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 185-194 show the fix (distinct state keys) but lack a contrasting "bad" example for comparison.
>
> **Action:** Add inline comment showing what not to do, e.g., `# Bad: both tools writing ctx.state["result"]`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Well-structured, accurate file with clear ASCII diagrams. The thread-pool execution tree and collision scenario are genuinely useful. Main weakness: redundancy — the Gotchas section is dead-weight repeat of How It Works, and the bullet list duplicates the diagram above it. Cutting those two blocks would tighten the file without losing information. No split needed.
