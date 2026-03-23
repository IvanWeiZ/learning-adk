# Review: 06-models.md

> [!info] Score: 8/10

## Issues & Actions

> [!abstract] Clarity
> **Issue:** Lines 73-83 ASCII diagram is misaligned; column labels don't line up above boxes.
>
> **Action:** Rewrite using vertical list-based layout per CLAUDE.md lesson 14.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 115 uses `"claude-sonnet-4-5"` as a model ID, which is not a real Anthropic model name.
>
> **Action:** Update to a real ID (e.g., `claude-3-5-sonnet-20241022`).
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!bug] Bug
> **Issue:** Line 28 mixes provider-specific model strings in the abstract `BaseLlm` code block (Gemini and Anthropic).
>
> **Action:** Move the example to subclass sections or remove provider-specific examples from `BaseLlm`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 47-50 say "not all adapters support" `connect()` without naming which ones do.
>
> **Action:** Add a comment: `# Gemini only` to clarify.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 143-158 list cache and Live API fields without explaining when they apply.
>
> **Action:** Add one sentence: cache fields apply when context caching is enabled; `live_connect_config` applies to Live API only.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Clarity
> **Issue:** Lines 185-195 mention "model inheritance" without explaining whether a sub-agent without a model inherits from parent.
>
> **Action:** Add one sentence with an example clarifying inheritance behavior.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!abstract] Structure
> **Issue:** "Default Model" (lines 183-196) feels disconnected after request/response objects; it's more an `LlmAgent` concern.
>
> **Action:** Move before "Adding a Custom Adapter" or add cross-reference to `04-agents.md`.
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!quote] Dedup
> **Issue:** Lines 163-179 overlap with `07-events.md` lines 28-60; same inherited fields, no cross-reference.
>
> **Action:** Add cross-reference at line 179: "See `07-events.md` for how `Event` extends this."
>
> - [x] Approved
> - [ ] Denied
> - [ ] Comment: 

> [!tip] Summary
> This is a well-structured, appropriately scoped file covering the model adapter layer completely — interface, streaming contract, registry dispatch, request/response objects, defaults, extensibility — without padding. Main weaknesses are a misaligned ASCII diagram (lines 73-83) that hurts readability, a potentially stale model ID example (`claude-sonnet-4-5`), and a few fields in `LlmRequest` that are listed without enough context. None are blocking. The registry resolution diagram and custom adapter example are exemplary — concrete, complete, immediately useful.
