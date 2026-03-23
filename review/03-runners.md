# Review: 03-runners.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 42-49 titled "Class Hierarchy" shows no inheritance, only a comparison of three unrelated concepts.
>
> **Action:** Delete the section; the insight is already in the At-a-Glance prose at line 36.
>
> - [ ] Approved
> - [ ] Denied
> - [x] Comment:   change the name to comparison between runner, agent, session

> [!abstract] Clarity
> **Issue:** Line 36 is a dense run-on listing seven things Runner does; hard to scan.
>
> **Action:** Break into two sentences: what Runner does per-request, then the stateless property.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 179-183 name two callbacks without explaining what a plugin is or when to use it.
>
> **Action:** Add one-line example of passing a plugin via `App`, or reference `10-apps.md` with context.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 219-242 don't show the `types` import; copy-paste readers will hit import errors.
>
> **Action:** Add the import line: `from google.adk import types`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 250 says Runner is "not thread-safe for a single invocation," which is contradictory; the real constraint is Sessions, not Runner.
>
> **Action:** Reword: "Each concurrent invocation must use a different `session_id`; sharing a session_id across concurrent calls causes undefined behavior because `Session` is stateful."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Lines 157-161 (Session Auto-Creation) and lines 246-248 (gotcha about auto-creation) repeat the same information; Gotchas version is sharper.
>
> **Action:** Trim the "How It Works" paragraph to one sentence and cross-reference the Gotchas section.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Lines 185-213 show a compaction diagram followed by prose repeating the same three points; also overlaps with `10-apps.md`.
>
> **Action:** Cut or tighten the prose (lines 207-213) after the diagram.
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 

> [!tip] Summary
> This is a solid, well-structured reference file. The internal flow trace (lines 133-155) is particularly clear and gives readers the mental model they need. Main weaknesses are a mislabeled "Class Hierarchy" section showing no inheritance, a Plugins subsection too sparse to be useful, and a self-contradictory gotcha that will confuse readers about thread safety. No split needed. With targeted edits to these three issues, this file would be a 9/10.
