# Review: 01-request-lifecycle.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Line 37 contains a prose paragraph immediately after the At-a-Glance ASCII box that duplicates what the diagram already shows, word-for-word.
>
> **Action:** Delete the entire paragraph; the diagram stands alone.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 584 and 590 repeat "See 18-session-lifecycle.md" twice in four lines, adding no value; line 582 already makes the reference.
>
> **Action:** Keep line 582, delete lines 584 and 590.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** File is 626 lines, 4% over the 600-line limit, but the content is genuinely unified around one trace.
>
> **Action:** Deleting line 37 (~7 lines) and compressing the callback signatures block (lines 527-563) to a summary table with a link (~20-line reduction) brings it under 600 without a split.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 302-305 show `partial=True` and `partial=False` without explaining that function-call streaming yields incomplete JSON, not text substrings.
>
> **Action:** Add one sentence clarifying the difference between partial JSON chunks and partial text.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 401 notes partial events aren't persisted but doesn't reference Step 8's session snapshot, leaving the connection implicit.
>
> **Action:** Add a forward reference to Step 8 explaining why `evt-004a/b/c` don't persist to the session.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Key Concepts" (lines 39-54) interrupts flow between At-a-Glance and Layer Diagram, forcing readers to skip it to reach the trace.
>
> **Action:** Move "Key Concepts" after "How It Works".
>
> - [ ] Approved
> - [ ] Denied
> - [x] Comment:  actually move key concept before  At a Glance

> [!abstract] Examples
> **Issue:** Lines 429-440 use informal shorthand (e.g., `content="What's the weather?"`) that doesn't match the Event model in Step 1.
>
> **Action:** Add a comment signaling pseudocode, or use real field names and values.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 527-563 (callback signatures) duplicate `04-agents.md`; lines 586-590 (state key scopes) duplicate `08-sessions.md`. The callback block is long enough to create a real maintenance burden.
>
> **Action:** Replace callback signatures block (lines 527-563) with a compact summary table and link to `04-agents.md`; keep the one-sentence state-scope summary inline.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> This is one of the strongest files in the repo. The step-by-step trace through a concrete example with actual field values on every Event object gives readers a rare ground-truth view of ADK at runtime. The sequence diagram and layer diagram complement each other well. Main weaknesses are minor: a redundant prose paragraph (line 37) that duplicates the ASCII summary, a callback signatures block already owned by `04-agents.md`, and two padding sentences in the Session Service subsection. Fixing those brings it under 600 lines and improves signal-to-noise noticeably.
