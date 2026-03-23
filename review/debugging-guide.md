# Review: debugging-guide.md

> [!info] Score: 6/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 219–244 (Testing Agents Effectively) duplicates `22-testing.md` content entirely.
>
> **Action:** Delete section; replace with one-line cross-reference.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!warning] Split
> **Issue:** Lines 80–98 and lines 48–73 repeat same content: `include_contents`, `max_llm_calls`, `EventsCompactionConfig`.
>
> **Action:** Collapse into one "Performance" section or keep Checklist as reference only.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** Lines 219–244 duplicate testing docs; lines 100–120 duplicate model selection; lines 48–73 and 80–98 repeat.
>
> **Action:** Delete testing section; compress model advice to one sentence + reference.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** Line 229 uses `Agent` and `InMemoryRunner` without imports; non-runnable.
>
> **Action:** Add imports or replace with reference to `22-testing.md` runnable version.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** Lines 48–73 uses forbidden ASCII box borders (`┌─┐ └─┘`); harder to scan than bullets.
>
> **Action:** Convert to bullet list or tree diagram.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** Debugging (quick checklists, symptoms) and performance sections interleaved; unclear structure.
>
> **Action:** Reorganize: move Debugging Checklist + Common Scenarios before performance sections.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Examples
> **Issue:** Heading `# 20b — Debugging Guide` is stale; file renamed to `debugging-guide.md`.
>
> **Action:** Change title to `# Debugging Guide`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> Useful debugging trees undercut by misplaced testing section, internal duplication, forbidden box formatting, and stale title. Delete testing section, collapse perf duplication, convert boxes to bullets, fix title. Becomes much tighter.
