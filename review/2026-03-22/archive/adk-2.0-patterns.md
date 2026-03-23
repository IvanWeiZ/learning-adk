# Review: adk-2.0-patterns.md

> [!info] Score: 5/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 248–305 (Migration Checklist) — reads as placeholder venv hygiene rather than concrete 2.0 breaking-change guidance (line 293 says "just run it and hope").
>
> **Action:** Delete entirely or replace with enumerated breaking changes (import path shifts, removed APIs, renamed classes).
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!warning] Split
> **Issue:** Lines 136–244 (Dynamic Workflows) introduces `@node`, `BaseNode`, `ctx.run_node()` with zero bridging to parent file's `Workflow` graph API.
>
> **Action:** Add one paragraph: explain whether `@node` is ADK 2.0 syntax or a separate pattern, and how it relates to graph workflows.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!quote] Dedup
> **Issue:** Lines 17–35 (mode comparison) and lines 291–293 (1.x migration notes) already in parent file.
>
> **Action:** Replace with one-sentence cross-reference: "See 25-adk-2.0-preview.md for mode comparison baseline."
>
> - [ ] Approved
> - [x] Denied
> - [ ] Comment: 
> 

> [!bug] Bug
> **Issue:** Line 41 import unverified against actual `google-adk --pre` package; readers will hit `ModuleNotFoundError`.
>
> **Action:** Test against pre-release or add warning: "Import paths are beta; subject to change."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Clarity
> **Issue:** Lines 39–57 instruction says "Route to support_agent" but 2.0 transfer semantics differ; unclear if active routing or delegation.
>
> **Action:** Explain 2.0 transfer semantics once before examples, then show code patterns only.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Structure
> **Issue:** "Key difference from 1.x transfer" (lines 113–125) appears *after* mode examples; readers need framing *before* code.
>
> **Action:** Move section to line 17, before mode examples.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!abstract] Examples
> **Issue:** Lines 90–109 shows three agents but not how coordinator receives and combines results.
>
> **Action:** Add inline code showing result collection (e.g., `event.response` structure or output schema).
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 
> 

> [!tip] Summary
> Unverified imports, unfocused migration section, and missing result-collection patterns weaken this file. Reorder sections (move 1.x framing before examples), verify imports, simplify or delete migration checklist, and add result-collection code. Would improve to 7+ after fixes.
