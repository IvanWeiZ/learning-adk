# Review: 02-when-to-build-what.md

> [!info] Score: 6/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 50-88 contain a "Quick Decision Tree" that is a near-duplicate of the "At a Glance" tree (lines 7-40) with only minor additions (BasePlanner, BaseCodeExecutor, A2A); two trees at the top create immediate reader confusion.
>
> **Action:** Merge the three unique entries (BasePlanner, BaseCodeExecutor, A2A) into "At a Glance" and delete the duplicate tree entirely.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 176-182 ("Examples" section) contain only one sentence pointing to `custom-use-cases.md`; a section that is a single forward reference wastes a heading and signals incompleteness.
>
> **Action:** Delete the heading and move the cross-reference into "Related" section.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** At 224 lines the file is well within the 600-line limit and cohesive in purpose.
>
> **Action:** No split needed; focus on deletions to improve clarity.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 91 heading "How It Works (diagram before prose)" is confusing; there is no diagram in this section and the parenthetical reads like an internal note left by mistake.
>
> **Action:** Rename to "Scenario Reference" or simply "Reference".
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 110 lists six executor class names inline without context for choosing between them.
>
> **Action:** Replace with a reference to the detailed guide or add inline context for each class.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 116 embeds a parenthetical warning in the table that breaks scanning rhythm.
>
> **Action:** Move the warning to a separate callout before the table.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Gotchas" section (lines 184-214) contains no gotchas, only a summary table that duplicates earlier trees.
>
> **Action:** Rename to "Component Quick Reference" or merge with "Summary Table".
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Five named sections (At a Glance, Key API, How It Works, Examples, Gotchas) create unclear mental model; dead Examples section and mislabeled Gotchas section weaken the flow.
>
> **Action:** Restructure to three sections: At a Glance tree → Scenario-to-component reference tables → Summary decision table → Related; eliminates dead section and clarifies purpose.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** No inline Python code grounds the abstract decision trees; readers must navigate to another file to see examples.
>
> **Action:** Add one 6-line example comparing FunctionTool vs. BaseTool.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 184-213 (Summary Table) partially duplicate the "At a Glance" tree (lines 7-40) and "Quick Decision Tree" (lines 50-87); all three map the same components to the same use cases.
>
> **Action:** Keep the Summary Table (it adds "When" and "Key base class" columns) and delete at least one of the two trees above.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> The core purpose — a decision guide mapping scenarios to ADK components — is clear and genuinely useful. The scenario reference tables (lines 97-173) are the strongest part: specific, concrete, well-categorized, and easy to scan. The weakness is structural redundancy: two nearly identical decision trees precede those tables, and a summary table follows them, meaning components are enumerated three times. The "Examples" section is a placeholder; "Gotchas" header is a mislabel. Fixing this is mostly deletion: cut the second decision tree, cut the Examples section, rename Gotchas to Summary Table, add one inline code example. Those changes bring this from 6 to an 8-9.
