# Review: security-checklist.md

> [!info] Score: 8/10

## Issues & Actions

> [!bug] Bug
> **Issue:** Line 84: `cleanup_expired_sessions` calls undefined `get_all_user_ids()`; code non-runnable.
>
> **Action:** Show implementation stub or link to session service docs with method signature.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** Lines 313–333 duplicate `19-session-security.md` table; lines 219–261 overlap `08-sessions.md` but add value (deep-copy, branch isolation).
>
> **Action:** Keep Built-In section; for State Prefix, add note: "See 19-session-security.md for full reference."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** Lines 98–118 (GDPR): comment about cleanup buried; readers miss that deletion is incomplete.
>
> **Action:** Replace comment with numbered list of required cleanup steps: artifacts, memory, credential store.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** Lines 130–133 (multi-tenant `app:` state shared across tenants) — critical warning only in code comment.
>
> **Action:** Add `> [!danger]` callout block before the pattern.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Examples
> **Issue:** Line 33 shows inline password string; models insecure practice in security doc.
>
> **Action:** Use environment variable injection: `postgresql+asyncpg://{os.environ['DB_USER']}:...`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> Strongest file in set. Incident scenarios and checklist are uniquely useful and production-ready. Fix undefined `get_all_user_ids()`, surface multi-tenancy warning as callout, improve DB credentials example, spell out GDPR cleanup steps. Near-perfect after these fixes.
