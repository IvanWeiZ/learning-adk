# Review: 00-onboarding-guide.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 119-139 show side-by-side "What you write / What ADK handles" boxes, violating CLAUDE.md lesson 10 (no side-by-side layout). Fragile in fixed-width rendering.
>
> **Action:** Delete entire section; line 111 ("Three pieces: Agent + Runner + Session") already conveys the idea.
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 145-198 contain a 54-line full architecture diagram with internal module paths (`cli/`, `flows/llm_flows/`, etc.) that overwhelms the onboarding file's stated purpose (motivation, under 250 lines, "agent = prompt + model + tools").
>
> **Action:** Replace with a minimal 4-5 line sketch showing only Agent → Runner → Session → LLM, with pointer to `01-request-lifecycle.md` for full picture.
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 89-109 introduce six new imports with zero explanation; the code block jumps from 5 lines to 20 without bridge prose.
>
> **Action:** Add comments on lines 103 and 105 explaining the user message and stream termination condition.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Section 3 introduces Runner and SessionService with no prior definition.
>
> **Action:** Add one sentence before the code block: "To run an agent, you need a Runner (orchestrates requests) and a SessionService (stores conversation history)."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> The file excels at its core job: getting readers to a working agent in three short sections with concrete examples and no unnecessary abstraction. The tool-call trace (lines 64-83) is precise and accurate. The back half weakens it: Section 4's side-by-side ASCII violates policy and is redundant; Section 5's full architecture diagram front-loads complexity that belongs elsewhere. Trimming both sections and replacing with a minimal 4-line sketch would bring the file under 180 lines and sharpen the "three pieces" message.
