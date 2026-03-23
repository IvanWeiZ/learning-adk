# Review: 09-tools.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 213–216 — prose summary repeats the long-running lifecycle diagram below it.
>
> **Action:** Remove; diagram is sufficient.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 420–421 (Gotchas bullets on GoogleSearch/error propagation) repeat content from lines 163–167 and 192 already in How It Works.
>
> **Action:** Keep only lines 423–424; remove duplicates.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 278–288 — `request_confirmation()` method not present in ToolContext API table (lines 107–124); likely invented API.
>
> **Action:** Verify against source before publication; if real, add to ToolContext table; if not, use correct method name.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!info] Note
> **Issue:** Built-in tools table (lines 128–137) duplicates class hierarchy (lines 44–58).
>
> **Action:** Table adds import paths (acceptable). Add note on why `BuiltInCodeExecutor` appears only in table.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 107–124 (ToolContext) — `actions.transfer_to_agent` shown as assignment, but `actions` never declared; readers don't know its origin.
>
> **Action:** Add one-line note: "accessed via `tool_context.actions`, same `EventActions` described in 07-events.md".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 278–290 (Tool Confirmation) — example shows call to `request_confirmation` but not what happens on next invocation (how tool knows if confirmed vs cancelled).
>
> **Action:** Expand to show two-invocation flow (like long-running lifecycle) or cut with cross-reference to where pattern is documented.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "At a Glance" diagram (lines 7–38) and "Tool Resolution" section (lines 169–190) cover same pipeline; At a Glance is complete, then section repeats the tree (lines 171–182).
>
> **Action:** Remove tree from Tool Resolution section; keep only code snippet since At a Glance handles visual.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 394 — SSE import path unusually deep (`google.adk.tools.mcp_tool.mcp_session_manager.SseConnectionParams as SseServerParams`) but alias `SseServerParams` conflicts with usage in line 350 diagram.
>
> **Action:** Verify import path is real; clarify why alias is used in example but not diagram.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> At a Glance, ToolContext, and lifecycle diagrams are strong. Main weaknesses: long-running summary repeats diagram, Gotchas repeat How It Works, and `request_confirmation()` needs source verification. Fix these for 9/10.
