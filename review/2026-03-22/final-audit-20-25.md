# Final Quality Audit — Files 20–25 (Split-offs Included)

Date: 2026-03-22

---

## 20-best-practices.md
**Ready:** NO
**Issues:**
- **Empty section:** `### 14. Common Architecture Anti-Patterns` has no content — it goes directly to `---` then `## Quick Reference`. This is a visible structural gap.
- **Empty section:** `## Quick Reference` heading immediately before `## Gotchas` with no content between them. Should be removed or populated.
- Minor: `Agent(name=...)` is used throughout but the import is never shown; fine for a reference doc, but the first code block uses `Agent` without establishing it's an alias for `LlmAgent`.

---

## 20b-debugging-guide.md
**Ready:** YES
**Issues:**
- None. Checklist structure is clean, all scenarios are well-formed, cross-references are valid, model IDs (`gemini-2.5-flash`, `gemini-2.5-pro`) are correct.

---

## 21-advanced-patterns.md
**Ready:** YES
**Issues:**
- None. All class names, import paths, and API calls verified against source (`ReflectAndRetryToolPlugin`, `TrackingScope`, `FunctionTool`, `ResumabilityConfig`, `App`). Code examples are copy-paste safe. Diagrams are readable.

---

## 22-testing.md
**Ready:** YES
**Issues:**
- The comment `# From google.adk.runners (production code, line 1596)` is a specific line number that may become stale as the source evolves. Low severity — it's a navigational hint, not a correctness claim.
- The package availability warning is accurate and appropriately prominent.

---

## 22b-testing-context-setup.md
**Ready:** YES
**Issues:**
- None. All context-creation patterns (`create_invocation_context`, `ToolContext` via `MagicMock`, `ReadonlyContext`, manual `InvocationContext`) are structurally correct and match the source.

---

## 22c-testing-examples.md
**Ready:** NO
**Issues:**
- **Code bug — broken code block:** The `_TestingAgent` class definition at line 267 is **not inside a code fence**. It renders as raw indented text, not syntax-highlighted Python. The surrounding prose correctly says "the following helper class", but the class definition has no opening ` ```python ` and no closing ` ``` `. Anyone copy-pasting this section will get broken indentation.
- **Invented API — `initial_state` parameter:** Line 44 passes `initial_state={'user_name': 'Alice'}` to `InMemoryRunner(agent, initial_state=...)`. The test `InMemoryRunner.__init__` signature (verified against source) accepts `root_agent`, `response_modalities`, `plugins`, `app` — **no `initial_state` parameter**. This example would raise `TypeError` if run. The state must be set on a `Session` via `session_service.create_session(..., state=...)` separately.

---

## 23-advanced-internals.md
**Ready:** YES
**Issues:**
- None. Processor pipeline table, reason-act loop diagram, and plugin callback order are accurate. The `MetricsPlugin` example is well-formed. Cross-references to `23b-plugins-and-a2a.md` are valid.

---

## 23b-plugins-and-a2a.md
**Ready:** YES
**Issues:**
- **Minor structural artifact:** Lines 197–200 contain a double `---` separator with a blank line between them (an empty section remnant from a previous split). Renders as two horizontal rules — cosmetically odd but not broken.
- `BaseTool` subclass example uses `types.Schema(type="OBJECT", ...)` string form with a note that the enum form `types.Type.OBJECT` may be needed — this is an honest caveat, not an error.

---

## 24-faq.md
**Ready:** NO
**Issues:**
- **Broken cross-reference in Q4:** The answer to Q4 ("What Is the Best Way to Pass Messages Between Agents?") says "See [message-passing-patterns.md](message-passing-patterns.md) for full code examples" — and that file *does* exist. However, `message-passing-patterns.md` is **not in the mkdocs nav** and **not listed in the CLAUDE.md repository structure table**. It is an undiscoverable orphan file from the reader's perspective. Either add it to the nav/structure, or inline a summary in Q4 rather than delegating to it with no context.
- **Abrupt Q4 body:** The Q4 section ends with only the cross-reference line — there is no summary, comparison table, or any description of the four mechanisms before pointing elsewhere. Every other question gives a standalone answer; Q4 is the only one that delegates entirely. A first-time reader hitting Q4 gets no value without clicking the link.
- `_session` private attribute access is clearly warned (twice, in both Pattern A and Pattern B), which is appropriate.

---

## 24b-custom-use-cases.md
**Ready:** NO
**Issues:**
- **Invented/private API — `callback_context._invocation_context`:** Line 117 in Option A uses `callback_context._invocation_context.user_content` to read the raw user message. `_invocation_context` is a private attribute (underscore prefix). There is no warning comment here (unlike the `_session` usage in `24-faq.md`). This should either be flagged as a private API with a stability warning, or replaced with the documented approach.
- **Structural gap:** Lines 339–342 contain a double blank line before `## Related` (empty section remnant from a split). Not harmful but visually inconsistent.
- The `asyncio.gather(*tasks.values())` pattern in Option A (line 132) is functionally correct but the dict-zip approach for recombining results is subtle and could silently produce wrong output if `tasks` dict insertion order is not preserved (it is in Python 3.7+ so this is safe, but worth a comment).

---

## 25-adk-2.0-preview.md
**Ready:** YES
**Issues:**
- **Minor structural artifact:** Lines 81–83 contain two consecutive `---` separators with no content between them (double blank rule). Cosmetically odd.
- The 2.0 `Event` type name conflict with the 1.x `Event` is clearly noted inline — this is good.
- All ADK 2.0 import paths are marked as beta/subject to change, which is appropriate given alpha status.

---

## 25b-adk-2.0-patterns.md
**Ready:** YES
**Issues:**
- None. The alpha warning is prominent. Mode comparison table is clear. Dynamic workflow patterns (`@node`, `ctx.run_node()`, `RequestInput`, `asyncio.gather`) are self-consistent. Migration notes cover all known breaking changes.

---

## Summary

| File | Ready | Severity |
|---|---|---|
| 20-best-practices.md | NO | Empty sections (§14 and Quick Reference) |
| 20b-debugging-guide.md | YES | — |
| 21-advanced-patterns.md | YES | — |
| 22-testing.md | YES | Minor: stale line number comment |
| 22b-testing-context-setup.md | YES | — |
| 22c-testing-examples.md | **NO** | Bug: missing code fence; invented API (`initial_state`) |
| 23-advanced-internals.md | YES | — |
| 23b-plugins-and-a2a.md | YES | Minor: double `---` artifact |
| 24-faq.md | NO | Q4 delegates entirely to orphan file with no summary |
| 24b-custom-use-cases.md | NO | Private API used without warning; structural gap |
| 25-adk-2.0-preview.md | YES | Minor: double `---` artifact |
| 25b-adk-2.0-patterns.md | YES | — |

**Files needing fixes before public sharing: 4**
- `20-best-practices.md` — fill or remove §14 and Quick Reference stubs
- `22c-testing-examples.md` — wrap `_TestingAgent` in a code fence; remove or fix `initial_state` example
- `24-faq.md` — add Q4 summary inline; register `message-passing-patterns.md` in nav
- `24b-custom-use-cases.md` — add private-API warning on `_invocation_context` usage
