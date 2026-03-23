# Review: 21-advanced-patterns.md

> [!info] Score: 8/10

## Issues & Actions

> [!bug] Bug
> **Issue:** File lacks standard sections found in other numbered files: "At a Glance", "What It Is", "Gotchas", "Related".
>
> **Action:** Add skeleton sections to match series format.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** `ReflectAndRetryToolPlugin` section (lines 99–128) uses implementation names (`_handle_tool_error`, `ToolFailureResponse`) without explanation.
>
> **Action:** Add ASCII flow diagram showing retry loop and which callbacks fire when.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Manual confirmation flow (lines 409–431) accesses `tool_context.tool_confirmation` without explaining the two-call contract.
>
> **Action:** Add 2–3 sentences before code: first call sets up request and agent suspends, second call arrives with confirmation attached.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 5–7 duplicate "Source:" and "Related:" already in line 3 header.
>
> **Action:** Remove freestanding "Source:" block for consistency with rest of repo.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 360–368 — hardcoded city data in `output_schema` example is unusual practice that may confuse learners.
>
> **Action:** Add comment explaining this is simplified proof-of-concept, not production pattern.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** Pattern 3 (`process_llm_request` override, lines 133–188) — key insight "Why not just return data?" is buried after code.
>
> **Action:** Move explanation before code block.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Line 437 references `ResumabilityConfig` without prior explanation; it's documented in `10-apps.md`.
>
> **Action:** Add cross-reference note to `10-apps.md` for context.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

## Summary

> [!tip] Summary
> Well-chosen patterns pulled directly from ADK samples with good source citations. Code quality is high and patterns are genuinely useful for intermediate learners. Main weakness is missing standard structure and insufficient scaffolding around harder patterns (confirmation flows, process_llm_request override). Adding skeleton sections and explanatory context would match the quality of the best files in the series.
