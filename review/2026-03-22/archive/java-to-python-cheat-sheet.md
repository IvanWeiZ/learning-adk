# Review: java-to-python-cheat-sheet.md

> [!info] Score: 8/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 133–147 (Package/Module System) generic Python basics with zero ADK relevance.
>
> **Action:** Remove section; fold Maven/Gradle → pip/uv row into ADK-Specific section.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Line 70 maps `List.of()` → tuple (wrong mental model); `List.of()` is immutable list, not sequence type.
>
> **Action:** Fix: `List` → `list`; `List.of()` → `tuple()` (immutable).
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 102: `ExecutorService` maps to deprecated `get_event_loop()`; causes RuntimeError in running loop.
>
> **Action:** Replace with: "asyncio event loop (managed by runtime)." Add: "Never call `get_event_loop()` — just `await` or `asyncio.create_task()`."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 161: `Spring Profiles` → state scoping misleading; they're unrelated (startup config vs runtime visibility).
>
> **Action:** Reframe: "Spring Profiles (startup config)" → "No equivalent; closest is `app:` keys for shared state."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** `@Override` row mentions duck typing but omits what readers should do differently.
>
> **Action:** Add: "In ADK subclasses (BaseAgent, BaseTool), override by matching signature—no annotation needed."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Generic Python tables come before ADK-Specific; experienced devs need ADK mapping first.
>
> **Action:** Move "ADK-Specific Mappings" to after intro, or add navigation hint to jump there.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** Lines 174–183: items 5 (EAFP) and 6 (no checked exceptions) redundant; 6 is consequence of 5.
>
> **Action:** Merge items 5–6; replace freed slot with: "State mutations are data, not method calls—use EventActions."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Examples
> **Issue:** No code examples; OOP row on "Multiple constructors" and ADK row on "Callbacks" remain abstract.
>
> **Action:** Add 3-line callback pattern snippet and classmethod factory pattern; link to 21-advanced-patterns.md.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** `Maven/Gradle` → `pip/uv` row duplicates python-for-adk-learning-plan.md.
>
> **Action:** Keep only if Package/Module section retained; otherwise remove.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** "Key Mindset Shifts" overlaps python-gotchas-for-java-developers.md (EAFP, duck typing, async).
>
> **Action:** Add note: "See also python-gotchas-for-java-developers.md for runtime traps."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> ADK-Specific section useful and well-chosen; tables scan fast. Main issues: wrong ExecutorService mapping (deprecated get_event_loop), misleading Spring Profiles analogy, wrong List.of mapping, redundant mindset shifts. Remove Package table, fix three bad mappings, merge mindset items, add navigation hint, add code snippets.
