# Review: python-pydantic-advanced.md

> [!info] Score: 7/10

## Issues & Actions

> [!danger] Delete
> **Issue:** Lines 78–123 "ADK Pattern: Tool Union" speculates how ADK defines tool types; violates CLAUDE.md Lesson 4 against inventing APIs.
>
> **Action:** Rewrite as explicitly "hypothetical discriminated union pattern" or delete; never teach speculative internal pattern as fact.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!danger] Delete
> **Issue:** Lines 659–695 `__get_pydantic_core_schema__` section too low-level and rarely needed; `PlainValidator` below covers practical need.
>
> **Action:** Remove ~35 lines; `PlainValidator` example (lines 699–716) uses public API and is sufficient.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!warning] Split
> **Issue:** At 1418 lines, file is 418 lines over 1000-line limit; mixing tutorial and reference dictionary.
>
> **Action:** Keep Sections 1–7 through "Generic Models"; move "JSON Schema" through "ADK-Specific Patterns" to new `python-pydantic-reference.md`.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 720–737 `model_construct()` section frames as "performance optimization" without warning against using on LLM/API data.
>
> **Action:** Add bold warning: "Do not use on data from LLMs, APIs, or user input — bypasses all validation."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Line 9 claims ADK uses unions "for tool types" — unverified per Issue 1 above.
>
> **Action:** Remove "tool types" from sentence; keep only "event types."
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** File ends abruptly without "ADK in Practice" or "Common Mistakes" section like other deep-dive files.
>
> **Action:** Add summary section mapping Pydantic patterns to ADK usage.
>
> - [ ] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> Covers important features (discriminated unions, generics, JSON schema, ConfigDict) that ADK learners need, but badly over limit at 1418 lines. Contains speculative claim about ADK's tool model, dangerous `model_construct()` example without warning, and TypeAdapter duplication in two sections. JSON schema section is clearest payoff. Immediate priorities: fix speculative ADK claim, add validation-bypass warning, create split plan to get under 1000-line limit.
