# Review: 12-artifacts.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 145–159 (`get_artifact_version` in BaseArtifactService Interface) duplicates the CallbackContext convenience wrapper (lines 275–280) which is what developers actually use.
>
> **Action:** Remove base-service signature or move to collapsed note; keep CallbackContext version as primary.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** Lines 130–143 — `list_versions` and `list_artifact_versions` have nearly identical signatures and purpose but lack clear explanation of when to choose one (list of ints vs full metadata).
>
> **Action:** Add comparison table or note making the distinction memorable.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 197–207 — comparison table uses inconsistent wording ("raises error" vs "raises `NotImplementedError`") for same behavior across backends; unclear what "artifact refs" means.
>
> **Action:** Standardize error wording; clarify "artifact refs" term.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 287–329 (Wiring artifact_service to Runner) partially overlaps with `03-runners.md` but provides necessary local context.
>
> **Action:** Collapse three separate code blocks into one with comments marking alternative service lines; save ~20 lines.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 17 — Introduces `file_data` storage mode but it's unsupported in two key backends (lines 205+).
>
> **Action:** Add note: "`file_data` is unsupported in FileArtifactService and GcsArtifactService."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 51 — "scoped by `app_name`, `user_id`, and optional `session_id`" precedes scoping section by 100+ lines; forward-reference without context.
>
> **Action:** Add one-line callout linking to scoping section.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 246 — "`artifact_delta` on `EventActions`..." drops in with no context; readers unfamiliar with `07-events.md` won't understand.
>
> **Action:** Add parenthetical: "(see 07-events.md)".
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 208–210 — "Extends `BaseModel` (Pydantic), so its state is serializable" implies you can snapshot/persist the service; implication non-obvious.
>
> **Action:** Add one sentence: "This enables snapshots or persistence of in-memory artifacts between sessions."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** `ArtifactVersion` metadata block (line 32) sits between Class Hierarchy and BaseArtifactService Interface; awkwardly placed for reading flow.
>
> **Action:** Move to just before versioning semantics section (line 240) where version numbers and metadata are discussed.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Code Examples section covers four cases well but lacks handling of unconfigured artifact service; `ValueError` mentioned at line 283 but no try/except pattern shown.
>
> **Action:** Add guard clause example: "if artifact_service is None: raise ValueError(...)" or complete try/except skeleton.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Comparison table and scoping diagram are strong. Main weaknesses: `ArtifactVersion` placement, `list_versions` distinction underexplained, and concepts (`file_data`, `artifact_delta`) lack context. Reorder and add clarifications.
