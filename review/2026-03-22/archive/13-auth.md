# Review: 13-auth.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 200–218 — "Two-Invocation Sequence" diagram misaligned; violates repo's side-by-side diagram policy ("always vertical tree").
>
> **Action:** Remove; "Detailed Steps" prose (lines 233–248) conveys information more clearly.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 222–231 — "Before/After" snippet; `WITHOUT auth` trivially obvious, `WITH auth` references phantom `AuthenticatedFunctionTool` never defined or linked.
>
> **Action:** Remove; leaves readers chasing non-existent API.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Lines 253, 311, 374 — examples use `CallbackContext` type, but tools use `ToolContext` (established in `09-tools.md`). Alias relationship unexplained.
>
> **Action:** Add note when first using `CallbackContext`: "tools receive it as `ToolContext` — the two are aliases."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 134 — `AuthScheme` from FastAPI's models, but FastAPI is not an obvious ADK dependency.
>
> **Action:** Add: "ADK reuses FastAPI's OpenAPI security scheme models."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** `request_credential` adding to `EventActions.requested_auth_configs` (line 237) and `"temp:{credential_key}"` storage (line 269) repeat internal details in `23-advanced-internals.md`.
>
> **Action:** Label as "internals — you don't normally need this" to prevent readers thinking they must interact with `EventActions` directly.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 265–269 — `get_auth_response` returns `None` for both "not responded yet" and "denied OAuth"; distinction needed for error handling.
>
> **Action:** Add: "Returns `None` on no response or denied flow; tool looping on `None` may retry forever."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 271–286 — `save_credential` and `load_credential` have no example or explanation of when to call manually vs relying on `parse_and_store_auth_response`.
>
> **Action:** Add: explain when each is used and how they differ from automatic session-state storage.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Credential Key" section (lines 438–446) placed after Cross-References; easy to miss but contains action item ("Set explicitly for stability").
>
> **Action:** Move before Code Examples section so readers know to set it before writing first auth config.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Lines 389–407 (HTTP Bearer Token) creates credential object and stops; omits usage pattern (`request_credential` / `get_auth_response`).
>
> **Action:** Complete example with tool function showing flow, or remove; as-is leaves readers guessing.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** No example shows error handling for `get_auth_response` returning `None` repeatedly or detecting denied OAuth grant.
>
> **Action:** Add single guard clause showing safe handling.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Main weaknesses: misaligned diagram violates style guide (delete), `CallbackContext` vs `ToolContext` inconsistency, phantom `AuthenticatedFunctionTool` reference, HTTP Bearer example incomplete. Move Credential Key section earlier and fix for 9/10.
