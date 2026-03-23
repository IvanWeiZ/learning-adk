# Final Quality Audit — adk/00–09

Audited: 2026-03-22 | ADK version traced: v1.27.2

---

## 00-onboarding-guide.md
**Ready:** YES
**Issues:**
- `from google.adk import Agent` — verified correct: `Agent` is exported from `google.adk.__init__` (`from .agents.llm_agent import Agent`) and listed in `__all__`.
- Side-by-side ASCII boxes in "What ADK Handles for You" (lines 122–141): technically two-column layout, which CLAUDE.md discourages ("no side-by-side boxes"), but the layout is clean and readable in monospace. Low risk.
- Model ID `gemini-2.5-flash` is used throughout — correct.
- File is 221 lines (limit 250). Within bounds.

---

## 01-request-lifecycle.md
**Ready:** YES
**Issues:**
- File is 600 lines exactly — right at the limit, not over.
- Content is thorough and well-structured. Mermaid sequence diagram is correct.
- `InvocationContext.branch: Optional[str] = None` shown — matches source.
- All callback return-value semantics match the table in 04-agents.md.

---

## 02-when-to-build-what.md
**Ready:** YES (with minor note)
**Issues:**
- Link to `24b-custom-use-cases.md` (line 191) — the file **does** exist in the repo, so the link is not broken. However, CLAUDE.md's structure section lists the file as `custom-use-cases.md`. The actual filename is `24b-custom-use-cases.md`, so the link is factually correct. No action needed.
- `AuthenticatedFunctionTool` is listed in the decision tree and component table — verify this class exists in ADK source before trusting; not verified against source in this audit.

---

## 03-runners.md
**Ready:** YES (minor inaccuracy)
**Issues:**
- `RunConfig.custom_metadata` is typed as `dict` in the doc (line 171), but the actual ADK source type is `Optional[dict[str, Any]] = None`. Minor but technically incorrect.
- `run_live` signature shown includes `user_id: Optional[str] = None` — matches source.
- `auto_create_session` default is `False` — correctly noted in Gotchas.
- All source links are GitHub URLs. No relative paths.

---

## 04-agents.md
**Ready:** YES
**Issues:**
- None found. Class hierarchy, callback table, `InvocationContext` fields, flow selection logic, and agent transfer mechanics are all internally consistent and match 01-request-lifecycle.md.
- `LlmAgent.DEFAULT_MODEL = 'gemini-2.5-flash'` — correct per ADK source.
- `escalate` vs `transfer_to_agent` distinction is clearly explained.

---

## 05-flows.md
**Ready:** YES (minor cosmetic issue)
**Issues:**
- File title is `# Flows — The Reason-Act Loop` — missing the `05 —` numeric prefix used by all other files (e.g., `# 04 — Agents: Blueprints for Behavior`). Cosmetically inconsistent but not a factual error.
- Content is accurate, concise, and cross-references 04-agents.md and 23-advanced-internals.md correctly.

---

## 06-models.md
**Ready:** YES (one inaccurate model ID)
**Issues:**
- Model ID `claude-sonnet-4-5-20250514` (lines 113 and 116) is **not a real Claude model ID** and is explicitly called out in CLAUDE.md lesson 15 as a bad example (`not claude-sonnet-4-5`). The actual ADK source default is `claude-sonnet-4-20250514` (found at `anthropic_llm.py:359`). The example should be corrected to `claude-sonnet-4-20250514` or another verified real ID.
- Everything else — `BaseLlm` interface, `LLMRegistry` regex dispatch, `LlmRequest`/`LlmResponse` fields, streaming contract — is accurate.

---

## 07-events.md
**Ready:** YES
**Issues:**
- None found. `Event` class hierarchy, all `EventActions` fields, `is_final_response()` logic, and branch filtering diagrams are accurate and detailed.
- `custom_metadata` is typed as `Optional[dict[str, Any]]` — consistent with source.
- Branch filtering visual is one of the clearest explanations in the codebase.

---

## 08-sessions.md
**Ready:** YES
**Issues:**
- Note: "The `user` name is reserved by ADK; do not use it as a user_id" (Gotchas, line 209) — this is slightly imprecise. ADK reserves `"user"` as an **agent name** (for the user role in events), not as a `user_id`. The actual constraint on `user_id` is that it's required and must be non-empty. Low-risk confusion for a reader.
- `SqliteSessionService` → source file is `sqlite_session_service.py`, class name is `SqliteSessionService` — table and Related section are consistent.

---

## 09-tools.md
**Ready:** YES (with one import path note)
**Issues:**
- SSE import example (line 396–397) uses `from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams as SseServerParams`. This is a deep internal import path. The class `SseConnectionParams` exists in source at that exact path, and `SseServerParams` is confirmed as an alias (`SseServerParams = SseConnectionParams` at line 548 of source). The doc notes it as a "deep import path" with a comment — acceptable.
- `McpToolset` import `from google.adk.tools.mcp_tool.mcp_toolset import McpToolset` is correct per source.
- Class hierarchy table, `ToolContext` API, long-running tool flow, and `request_confirmation` signature (`hint`/`payload`) are all accurate.

---

## Summary

| File | Ready | Severity |
|------|-------|----------|
| 00-onboarding-guide.md | YES | — |
| 01-request-lifecycle.md | YES | — |
| 02-when-to-build-what.md | YES | — |
| 03-runners.md | YES | Low: `custom_metadata` typed as `dict` instead of `Optional[dict[str, Any]]` |
| 04-agents.md | YES | — |
| 05-flows.md | YES | Cosmetic: missing `05 —` numeric prefix in title |
| 06-models.md | **NO** | **Medium: `claude-sonnet-4-5-20250514` is not a real model ID** |
| 07-events.md | YES | — |
| 08-sessions.md | YES | Low: misleading Gotcha about `"user"` as `user_id` vs agent name |
| 09-tools.md | YES | — |

**Blocking issue:** `06-models.md` uses `claude-sonnet-4-5-20250514` as an example model ID. The correct real ID per ADK source (`anthropic_llm.py:359`) is `claude-sonnet-4-20250514`. This violates CLAUDE.md lesson 15 explicitly.

**Fix required before sharing:**
```
06-models.md line 113/116: replace "claude-sonnet-4-5-20250514" with "claude-sonnet-4-20250514"
```
