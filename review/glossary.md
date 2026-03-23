# Review: glossary.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Four redirect-only stubs (Flow, Plugin, SessionService, Toolset) add clutter without defining terms.
>
> **Action:** Fold redirects into parent entries as notes or remove entirely.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** `ReadonlyContext` says it prevents mutations but omits how to actually mutate state.
>
> **Action:** Add one sentence: "State writes via `EventActions.state_delta`, not direct assignment."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** `ExecutorService` maps to deprecated `asyncio.get_event_loop()`; causes RuntimeError in running loop.
>
> **Action:** Add note: "In ADK, never call `get_event_loop()` — just `await` or use `asyncio.create_task()`."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** `Escalate` refers to "parent agent" with no cross-ref to `Transfer`; distinction unclear.
>
> **Action:** Add `→ contrast: Transfer` pointer to Escalate definition.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** `Event` vaguely names fields without types; `EventActions` lists sub-fields properly.
>
> **Action:** Replace prose with field list: `author`, `branch`, `content`, `actions`, `id`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** `LlmResponse` describes "usage metadata" without explaining token counts.
>
> **Action:** Change to "token usage metadata (input/output counts)."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** `Output schema` says "structured format" but omits what that means (Pydantic? JSON schema string? dict?).
>
> **Action:** Add one-line example: "e.g., Pydantic `model_json_schema()` or JSON schema dict."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** `Callback` lists six hooks but omits when to use them vs. tools vs. sub-agents.
>
> **Action:** Add: "Use to intercept execution without stopping (log, validate, modify state)."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** `Output key` and `Output schema` grouped alphabetically but conceptually unrelated; easily conflated.
>
> **Action:** Add note in `Output schema`: "→ different from Output key (processor-specific)."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** Glossary is missing important aliases from CLAUDE.md lesson 7: `CallbackContext` / `ToolContext` alias, plus `InvocationContext` / `Context` alias, and terms like `McpToolset`, `SQLiteSessionService`.
>
> **Action:** Add cross-ref entries under C: "CallbackContext — See ToolContext" and "Context — See InvocationContext."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** All letters J, K, N, Q, U, W, X, Z are absent with no note, making file feel incomplete.
>
> **Action:** Add one-line header note: "Terms added as documentation grows."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Examples
> **Issue:** No code examples in entire glossary; terms like `StateDelta`, `Output schema`, `YAML agent config` remain abstract.
>
> **Action:** Add 2-line snippet for `Output schema` (Pydantic pattern) and `State (scoped)` (scope prefix examples: `"key"`, `"user:key"`, `"app:key"`).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** `State (scoped)` at line 133 and `StateDelta` at line 135 both list the three scope prefixes, duplicating content from `08-sessions.md`.
>
> **Action:** Remove scope prefix list from `StateDelta` and add `→ see: State (scoped)` pointer instead.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> The glossary is well-structured and consistently formatted but weakened by four redirect stubs that add clutter, sparse definitions for high-confusion terms (`Callback`, `ReadonlyContext`, `Output schema`), and missing aliases crucial to learners (`ToolContext`/`CallbackContext`). Removing stubs, enriching three entries with one sentence each, and adding the alias entry would reach 9/10 with minimal work.
