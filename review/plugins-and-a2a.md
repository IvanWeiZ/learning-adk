# Review: plugins-and-a2a.md

> [!info] Score: 5/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Sections 6–15 (484 lines) duplicate eight dedicated files (Auth, Artifacts, Planners, Compaction, Content Filtering, Function Call IDs, Streaming, Advanced Patterns).
>
> **Action:** Replace each with one-sentence summary + GitHub link; keep only unique content (BaseTool subclassing, LongRunningFunctionTool, AgentTool, BaseToolset, A2A).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** Sections 6–15 are wholesale copies or near-copies of content in seven dedicated numbered files.
>
> **Action:** See Delete action above.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** Line 18–75: `types.Schema(type="OBJECT")` uses string; should be `types.Type.OBJECT` enum.
>
> **Action:** Verify against SDK or add note: "If string form fails, use enum value."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** Lines 124–148 say AgentTool creates isolated session but don't explain why (new session per call) until line 468.
>
> **Action:** Add inline note: "Each invocation creates a new session, isolating state from parent agent."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** Title says "Custom Tools, A2A, Code Executors" but 60% is duplicates of unrelated topics (Auth, Artifacts, Planners).
>
> **Action:** After pruning, keep only: BaseTool → LongRunningFunctionTool → AgentTool → BaseToolset → A2A (coherent "advanced tools").
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Examples
> **Issue:** `types.Schema` — unclear if string form is valid or deprecated.
>
> **Action:** Test both forms or cite SDK version.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> 60% duplicates seven dedicated files (484 lines of bloat). Only ~200 lines unique (BaseTool subclassing, LongRunningFunctionTool, AgentTool, BaseToolset, A2A). Delete duplicates, verify `types.Schema` form, add inline AgentTool explanation. Becomes tight advanced-tools reference.
