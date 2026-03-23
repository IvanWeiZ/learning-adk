# Review: 19-session-security.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 154-187 show a nested ASCII box diagram for state scopes with visually fragile formatting (inconsistent edge characters like `│   │   │` with mismatched pipes) that won't render well in narrow terminals.
>
> **Action:** Delete the box diagram; the decision tree at lines 191-208 covers the same content and is cleaner.
>
> - [ ] Approved
> - [ ] Denied
> - [x] Comment:  try to merge them

> [!abstract] Structure
> **Issue:** "At a Glance" (lines 5-11) is a single sentence plus cross-reference — no content preview.
>
> **Action:** Add a 3-5 line summary of file contents or remove the section heading.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 68-69 say `user_id` is "optional" on `list_sessions` but the danger is buried in a code comment.
>
> **Action:** State the danger explicitly in the opening sentence.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 253-270 show how to set `branch` on events without defining what branch values mean.
>
> **Action:** Add one sentence: "Branch is a dot-separated ancestor path in the agent tree."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 304-319 ("Callback and Plugin Security") shows a closure statefulness bug, not a session security issue.
>
> **Action:** Move this example to `20-best-practices.md` or `17-concurrency.md`; it doesn't belong in session security.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Tight, practical security reference that does its job well. Concrete wrong/correct patterns for `user_id` handling, session ID generation, and state prefix misuse are genuinely useful and not duplicated elsewhere. Main weaknesses: hollow "At a Glance" section, a fragile nested diagram that should be deleted (cleaner decision tree follows), and one example (callback closure) that belongs in a different file. Otherwise solid.
