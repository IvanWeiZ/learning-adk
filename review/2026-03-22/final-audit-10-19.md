# Final Quality Audit — adk/10 through adk/19b

Audited: 2026-03-22
Files: 12 (10-apps.md, 11-memory.md, 12-artifacts.md, 13-auth.md, 14-planners.md, 15-evaluation.md, 16-error-reference.md, 17-concurrency.md, 18-session-lifecycle.md, 18b-session-latency-optimization.md, 19-session-security.md, 19b-security-checklist.md)

---

## 10-apps.md
**Ready:** YES
**Issues:** None — class names, method signatures, and config field names all look correct. `BasePlugin` interface matches 11 callbacks + `close()`. Examples are copy-paste clean. Structure complete.

---

## 11-memory.md
**Ready:** YES
**Issues:**
- Minor: `MemoryEntry.custom_metadata` is typed as `Optional[dict] = None` in the file but the actual ADK source uses `dict[str, Any] = Field(default_factory=dict)`. Low severity for a docs repo but inconsistent with how the project documents other fields (e.g., `ArtifactVersion.custom_metadata` in 12-artifacts.md is correctly typed). Acceptable for now; flag for a follow-up pass.
- Pattern 1 (automatic memory on session end) accesses `callback_context._invocation_context` — a private attribute. The code comment above it correctly warns this is internal. Readability is fine.

---

## 12-artifacts.md
**Ready:** YES
**Issues:** None — `ArtifactVersion` fields, versioning semantics (0-based), `save_artifact`/`load_artifact`/`list_artifacts` signatures, and the `user:` prefix scoping are all accurate. `file_data` unsupported note is correct. Examples compile cleanly.

---

## 13-auth.md
**Ready:** YES
**Issues:**
- Minor readability: Two example functions (`call_external_api`, `list_calendar_events`) declare `ctx: CallbackContext` as the parameter type but the file itself says at line 221 that "Tools receive this as `ToolContext`." The examples are functionally correct but the parameter type annotation inconsistency could confuse readers. The `call_bearer_api` example correctly uses `tool_context: ToolContext`, so there are mixed conventions.
- `fastapi.openapi.models` import path — FastAPI restructures its internal modules occasionally; readers should be aware this may need `from fastapi.openapi.models import ...` vs `from openapi_models import ...` depending on FastAPI version. Not wrong for the stated dependency.

---

## 14-planners.md
**Ready:** YES
**Issues:**
- Duplicate paragraph: lines 168 and 170 say essentially the same thing ("Everything before `/*FINAL_ANSWER*/` is thought/hidden" and then the same sentence rephrased). One should be removed.
- Minor: `from google.adk import Agent` in examples — the canonical import is `from google.adk.agents import LlmAgent`. If `Agent` is an alias exported from `google.adk`, this works; if not, it is a broken import. Other files in the repo consistently use `LlmAgent`. Low confidence without source verification — flag for check.

---

## 15-evaluation.md
**Ready:** YES
**Issues:**
- Terminology inconsistency: Line 180 refers to "each expected `ToolUse`" but the actual type (shown at line 89) is `FunctionCall` — `ToolUse` is not an ADK class (CLAUDE.md lesson #1 explicitly lists `ToolUse` as non-existent). The prose should read "each expected `FunctionCall`."
- `AgentEvaluator.evaluate()` is documented as async (`await AgentEvaluator.evaluate(...)` in the pytest example) but the non-pytest example at line 165 calls it without `await`. This inconsistency means one of the two call sites is wrong. CLAUDE.md lesson #6 confirms `evaluate()` is async — the bare call at line 165 is a bug.
- Minor: `reference_answer` is mentioned in the "Eval vs Unit Test" table and the "Writing Good Eval Cases" section, but the `Invocation` model has `final_response` not `reference_answer`. Using the wrong field name would silently be ignored in evaluation. Verify against source.

---

## 16-error-reference.md
**Ready:** YES
**Issues:** None — error class names (`LlmCallsLimitExceededError`, `SessionNotFoundError`, `AlreadyExistsError`, `ToolExecutionError`, `_ResourceExhaustedError`) and import paths match source. Three-tier model is accurate and well-illustrated. Copy-paste examples are clean.

---

## 17-concurrency.md
**Ready:** YES
**Issues:** None — `asyncio.gather` without `return_exceptions=True` behavior, `deep_merge_dicts` last-write-wins, `DatabaseSessionService` two-layer locking, `ToolThreadPoolConfig` thread-safety warning — all accurate and sourced. Examples clearly illustrate the bad/good pattern.

---

## 18-session-lifecycle.md
**Ready:** YES
**Issues:** None — `BaseSessionService` 5-method interface, `append_event` base implementation steps (partial skip → temp state write → trim → state update → append), Runner call sequence (get → optional create → user event append → agent event appends), and `InMemorySessionService` vs `DatabaseSessionService` comparison are all accurate. Cross-references are valid.

---

## 18b-session-latency-optimization.md
**Ready:** NO
**Issues:**
- Broken cross-reference at line 417: links to `[20b-debugging-guide.md](20b-debugging-guide.md)` — the file exists at `adk/20b-debugging-guide.md`, but the relative link from `adk/18b-session-latency-optimization.md` should resolve correctly. This needs CI verification.
- Questionable model IDs in the latency table (lines 222-223): `claude-haiku-4-5-20251001` and `claude-sonnet-4-5-20250514` — these do not follow Anthropic's published model ID format (e.g., `claude-haiku-4-5` or `claude-3-5-haiku-20241022`). CLAUDE.md lesson #15 says "Use real model IDs." These look invented/incorrect. Should be verified and corrected before public sharing.
- `BatchingDatabaseSessionService._engine` is accessed directly (line 107) but `DatabaseSessionService` may not expose `_engine` as a public attribute — this is an illustrative pattern but could fail if the internal attribute name differs. The comment "WARNING: illustrative only" partially mitigates this, but readers may copy it.

---

## 19-session-security.md
**Ready:** YES
**Issues:** None — user_id enforcement, state prefix scoping (`extract_state_delta` source code included verbatim), session ID guessability, `list_sessions(user_id=None)` danger, and event persistence list are all accurate. Examples clearly show dangerous vs correct patterns. Well-structured.

---

## 19b-security-checklist.md
**Ready:** YES
**Issues:** None — `cleanup_expired_sessions` and `delete_all_user_data` patterns are sound. Multi-tenant pattern table is accurate. The "ADK's Built-In Safety Mechanisms" vs "What ADK Does NOT Protect" split is clear and source-verified. Checklist is comprehensive and well-organized.

---

## Summary

| File | Ready | Key Issues |
|------|-------|------------|
| 10-apps.md | YES | — |
| 11-memory.md | YES | Minor: `MemoryEntry.custom_metadata` type mismatch |
| 12-artifacts.md | YES | — |
| 13-auth.md | YES | Minor: mixed `CallbackContext`/`ToolContext` in examples |
| 14-planners.md | YES | Duplicate paragraph (lines 168/170); verify `from google.adk import Agent` |
| 15-evaluation.md | YES | `ToolUse` should be `FunctionCall` (line 180); `evaluate()` missing `await` (line 165); `reference_answer` vs `final_response` field name |
| 16-error-reference.md | YES | — |
| 17-concurrency.md | YES | — |
| 18-session-lifecycle.md | YES | — |
| 18b-session-latency-optimization.md | NO | Likely-wrong Anthropic model IDs; broken `_engine` access in illustrative code |
| 19-session-security.md | YES | — |
| 19b-security-checklist.md | YES | — |

**Blocking issues before public sharing:**
1. `18b-session-latency-optimization.md` — model IDs `claude-haiku-4-5-20251001` and `claude-sonnet-4-5-20250514` need verification/correction.
2. `15-evaluation.md` — `evaluate()` called without `await` at line 165 is a code bug.

**Non-blocking (fix in follow-up):**
- `14-planners.md`: remove duplicate paragraph at lines 168-170.
- `15-evaluation.md`: replace `ToolUse` with `FunctionCall` in prose; verify `reference_answer` field name.
- `13-auth.md`: standardize to `ToolContext` in all auth tool examples.
