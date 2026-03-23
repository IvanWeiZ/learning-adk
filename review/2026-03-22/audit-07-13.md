# Audit: Applied Review Changes (07–13)

Audit date: 2026-03-22
Covers: `07-events.md`, `08-sessions.md`, `09-tools.md`, `10-apps.md`, `11-memory.md`, `12-artifacts.md`, `13-auth.md`

---

## 07-events.md

**8 items approved.**

1. **[x] Approved — Delete lines 139–147 (prose body repeating At a Glance)**
   - ✅ Applied. The current file has no redundant prose after the At a Glance box; line 23 is a single clean paragraph.

2. **[x] Approved — Delete "Examples" prose recap (lines 250–255); replace with runnable snippet**
   - ✅ Applied. The Examples section (lines 212–229) now contains a real runnable snippet showing `runner.run_async()` iteration, `event.author`, `event.actions.state_delta`, `event.get_function_calls()`, and `event.is_final_response()`.

3. **[x] Approved — Replace opaque IDs like `"evt-002"` / `"e-inv-9f2a"` with descriptive labels**
   - ❌ NOT fully applied. The "Events in a Single Turn" diagram (lines 142–153) still uses `evt-001`, `evt-002`, `evt-003`, `evt-004` as event labels. The "What's Inside an Event" box (lines 109–132) uses descriptive content (e.g., `"weather_agent"`, `"18°C in Tokyo"`), which is good. But the "Branch Filtering" diagram (lines 172–207) still uses `evt-001` through `evt-008`. The review asked for descriptive labels like "Tool Call" and "weather lookup result" to replace the opaque ID labels in diagrams.

4. **[x] Approved — Keep `is_final_response()` only in Key Methods; remove Gotchas restatement**
   - ✅ Applied. The Gotchas section (lines 231–235) does not restate `is_final_response()` logic — it only mentions two different gotchas about user event not being yielded and branch filtering.

5. **[x] Approved — Move "Carries text, function calls..." into `content` field description**
   - ✅ Applied. Line 35 now reads: `` `Event` extends `LlmResponse`. The `content` field (`Optional[types.Content]`) carries text, function calls, function responses, blobs, or thoughts. `` — the description is attached to the `content` field.

6. **[x] Approved — Move inline `is_final_response()` comment to prose after code block**
   - ✅ Applied. Lines 91–101 show the method signatures without inline spanning comments; the explanation is in prose at line 103.

7. **[x] Approved — Merge "How Events Flow End-to-End" with "Events in a Single Turn"; rename**
   - ✅ Applied. The current file has only one "Events in a Single Turn" section (lines 135–158) — no separate "How Events Flow End-to-End" section exists. The sections were merged.

8. **[x] Approved — Add 10-line snippet showing event consumption, `event.author` check, `state_delta` inspection**
   - ✅ Applied. Examples section (lines 212–229) has exactly this snippet.

**Summary for 07-events.md:** 1 item missed (opaque ID labels in diagrams).

---

## 08-sessions.md

**6 items approved; 1 denied (State Scoping code block dedup).**

1. **[x] Approved — Remove Class Hierarchy section (lines 41–50)**
   - ✅ Applied. The current file has no separate "Class Hierarchy" section — the implementations table is the authoritative source, embedded in the At a Glance diagram and the Implementations table (lines 104–113).

2. **[x] Approved — Add explanation for `_delta` / `_value` private fields**
   - ✅ Applied. Line 141 reads: "State is backed by two internal dicts: `_value` for reads and `_delta` for pending writes that haven't been persisted yet."

3. **[x] Approved — Expand `output_key` comment explaining what key is written and when**
   - ✅ Applied. Lines 190–194 read: `# output_key stores the agent's final text response in state:` ... `# When this agent produces its final response, the text is automatically` / `# saved to session.state['summary'] via state_delta.` / `# Useful in SequentialAgent pipelines where the next agent reads the output.`

4. **[x] Approved — Rephrase line 112 to "Use GetSessionConfig when you only need recent context from a long session."**
   - ✅ Applied. Line 100 reads exactly: "Use `GetSessionConfig` when you only need recent context from a long session."

5. **[x] Approved — Move "Agents access sessions only through InvocationContext" to Gotchas**
   - ✅ Applied. Line 206 in the Gotchas section reads: "Agents access sessions only through `InvocationContext` — never directly via the session service."

6. **[x] Approved — Collapse Examples to reduce overlap with How It Works diagrams**
   - ✅ Applied. The Examples section (lines 184–200) is now concise — 3 focused code comments covering state write, output_key, and state scoping, with no duplication of the How It Works diagrams.

**Summary for 08-sessions.md:** All 6 approved items applied. ✅

---

## 09-tools.md

**5 items approved; 2 denied.**

1. **[x] Approved — Verify `request_confirmation()` against source; add to ToolContext table if real**
   - ✅ Applied. `request_confirmation` is included in the ToolContext section (line 123) with the correct signature `def request_confirmation(hint: str, payload: dict) -> None`. A note at line 291 confirms the fields: "`ToolConfirmation` uses `hint` and `payload` fields (not `title`/`message`)."

2. **[x] Approved — Add note: why `BuiltInCodeExecutor` appears only in table**
   - ✅ Applied. Line 144: "`BuiltInCodeExecutor` appears only in this table (not in the class hierarchy above) because it's a code executor, not a `BaseTool` subclass — it plugs into `LlmAgent.code_executor`, not `tools`."

3. **[x] Approved — Add note: `actions` is `EventActions` from 07-events.md**
   - ✅ Applied. Line 113 reads: `# Side-effects envelope (same EventActions from 07-events.md):` and an explanatory block note exists at line 129: "`ToolContext vs InvocationContext:` ... `CallbackContext` is the same as `ToolContext` (they are aliases)."

4. **[x] Approved — Expand Tool Confirmation to show two-invocation flow**
   - ✅ Applied. Lines 270–291 show the full two-invocation pattern with comments explaining Invocation 1 (request confirmation, tool pauses) and Invocation 2 (user approval/denial). Reference to `tool_context.py` is included.

5. **[x] Approved — Remove tree from Tool Resolution section; keep only code snippet**
   - ✅ Applied. Lines 176–188 show "Tool Resolution in LlmAgent" with prose + code snippet only, no redundant ASCII tree (the At a Glance handles the visual).

6. **[x] Approved — Verify SSE import path; clarify why alias is used**
   - ✅ Applied. Lines 395–396 read: `from google.adk.tools.mcp_tool.mcp_toolset import McpToolset` / `# Note: deep import path — alias used for readability` / `from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams as SseServerParams`. The alias reason is documented inline.

**Summary for 09-tools.md:** All 5 approved items applied. ✅

---

## 10-apps.md

**12 items approved.**

1. **[x] Approved — Remove "Basic Usage" lines 278–290 (duplicates Examples)**
   - ✅ Applied. No "Basic Usage" section exists in the current file.

2. **[x] Approved — Separate plugin-to-plugin vs lifecycle-stage order in callback chain diagram, or add explanation**
   - ✅ Applied. The diagram (lines 196–244) shows clearly the vertical lifecycle stage ordering with horizontal `Plugin 1 → Plugin 2 → ... → Agent's own callback` showing plugin-to-plugin within each stage.

3. **[x] Approved — Clarify `close()` is a lifecycle hook, not a callback**
   - ✅ Applied. Line 115 reads: "11 event-driven callbacks plus `close()` (a lifecycle hook, not a callback — called when the app shuts down)."

4. **[x] Approved — Trim At a Glance to top-level App fields; note "BasePlugin has 11 callbacks"**
   - ✅ Applied. The At a Glance box (lines 7–27) now shows `plugins: [BasePlugin, ...]` with `└── 11 callbacks (see BasePlugin below)`, not listing all callback names.

5. **[x] Approved (also move the table up) — Keep "App vs Bare Agent" table; trim line 41 enumeration; move table up**
   - ✅ Applied. The comparison table is now at lines 40–45, directly after the two Runner constructor snippets (lines 32–37), before Class Hierarchy. The `At a Glance` prose at line 30 is a single short sentence without feature enumeration.

6. **[x] Approved — Show both Runner constructor signatures side-by-side**
   - ✅ Applied. Lines 32–37 show both `Runner(app=App(...))` and `Runner(agent=..., app_name=...)` side by side with comments.

7. **[x] Approved — Bold note for `static_instruction` dependency; add link to 04-agents.md**
   - ✅ Applied. Line 271 reads: "Context caching stores `static_instruction` tokens server-side... **Requires** `static_instruction` on `LlmAgent` (see [04-agents.md](04-agents.md)); no effect without it."

8. **[x] Approved — Make short-circuit rule a bold note / callout**
   - ✅ Applied. Lines 117–118 have a blockquote: "> **Short-circuit rule:** A non-`None` return from any plugin callback short-circuits remaining plugins AND the agent's own callbacks for that stage."

9. **[x] Approved — Add explanation for "Requires idempotent tool calls"**
   - ✅ Applied. Line 326 reads: "**Requires idempotent tool calls.** Resuming a paused agent re-invokes previous tools; non-idempotent tools may double-execute or corrupt state."

10. **[x] Approved — Add "How It Works" subsection for Context Cache**
    - ✅ Applied. Lines 259–271 contain the ContextCacheConfig API block followed by a prose paragraph explaining what context caching does and its requirement.

11. **[x] Approved — Keep Key API minimal for compaction; move full wiring to Examples**
    - ✅ Applied. The Key API section (lines 249–256) is a compact one-block config example. The full wiring is in Examples (lines 344–358).

12. **[x] Approved — Add second code block showing how caller invokes resume**
    - ✅ Applied. Lines 387–397 show the full two-invocation resume pattern with Invocation 1 (pause detection) and Invocation 2 (resume).

13. **[x] Approved — Verify `gemini-2.5-flash` model ID**
    - ✅ Applied. `gemini-2.5-flash` is used consistently throughout the file (lines 379, 406). This is a current valid model ID.

**Summary for 10-apps.md:** All 12 approved items applied. ✅

---

## 11-memory.md

**8 items approved; 4 denied.**

1. **[x] Approved — Remove Java Comparison table (lines 286–294)**
   - ✅ Applied. No Java comparison table exists in the current file.

2. **[x] Approved — Verify `callback_context.add_session_to_memory()` — fix if invented API**
   - ✅ Applied. Pattern 1 (lines 235–250) now shows the correct pattern: accessing memory service via `callback_context._invocation_context.memory_service` and calling `memory_service.add_session_to_memory(session)`. A comment at lines 238–239 explains: "Note: `add_session_to_memory()` lives on `BaseMemoryService`, not on `CallbackContext`."

3. **[x] Approved — Fix fragile `system_instruction +=` pattern (guard for None, handle list)**
   - ✅ Applied. Pattern 2 (lines 258–268) now has: `existing = llm_request.config.system_instruction or ""` / `llm_request.config.system_instruction = existing + memory_block` — a safe guard for None.

4. **[x] Approved — Redraw "Cross-Session Timeline" diagram with proper alignment**
   - ✅ Applied. Lines 147–167 show a vertical timeline format: Session A at top, arrow down showing time passing, Session B below — no misaligned side-by-side boxes.

5. **[x] Approved — Add "Storage is not automatic" note to What It Is**
   - ✅ Applied. Line 9 reads: "Storage is not automatic — requires explicit `add_session_to_memory()` call or a callback wired to trigger it."

6. **[x] Approved — Clarify search is "case-insensitive exact substring matching (not fuzzy)"**
   - ✅ Applied. Line 110 reads: "Stores event text in a list; search is case-insensitive exact substring matching (not fuzzy/semantic)."

7. **[x] Approved — Delete line 190 vague "Some apps do this automatically..." prose**
   - ✅ Applied. No such vague prose exists in the current file before the Practical Patterns section.

8. **[x] Approved — Move "Memory vs Session State — Decision Guide" to after "What It Is"**
   - ✅ Applied. Lines 23–36 show the Decision Guide ("When to Use Memory vs Session State") directly after the Session State vs Memory comparison table, which itself follows "What It Is".

9. **[x] Approved — Show callback-based pattern first for Saving a Session; add comment about refetch**
   - ✅ Applied. Lines 203–209 show the refetch pattern with a comment: "# Refetch session to get complete event history (the runner loop may have ended)".

10. **[x] Approved — Remove f-string wrapper in Pattern 3**
    - ✅ Applied. Pattern 3 (lines 276–290) no longer uses `f"{m.content.parts[0].text}"` — it uses direct access `m.content.parts[0].text`.

**Summary for 11-memory.md:** All 8 approved items applied. ✅

---

## 12-artifacts.md

**9 items approved.**

1. **[x] Approved — Remove `get_artifact_version` from BaseArtifactService Interface or move to note; keep CallbackContext version primary**
   - ✅ Applied. The BaseArtifactService section (lines 47–56) is a table showing 6 methods — `get_artifact_version` is not listed there. It appears only in the CallbackContext section (lines 155–161) where it belongs.

2. **[x] Approved — Add comparison/note distinguishing `list_versions` vs `list_artifact_versions`**
   - ✅ Applied. Line 56 reads: "`list_versions` returns just ints (lightweight check); `list_artifact_versions` returns full `ArtifactVersion` objects with URIs, timestamps, and custom metadata."

3. **[x] Approved — Standardize error wording; clarify "artifact refs"**
   - ✅ Applied. The implementations table (lines 96–103) uses consistent wording: "`file_data` support" column shows "Not supported (`NotImplementedError`)" for both `FileArtifactService` and `GcsArtifactService`.

4. **[x] Approved — Collapse three separate code blocks into one for wiring artifact_service to Runner**
   - ✅ Applied. Lines 179–191 show a single code block with commented alternatives for all three backends.

5. **[x] Approved — Add note: `file_data` is unsupported in FileArtifactService and GcsArtifactService**
   - ✅ Applied. Line 17 reads: "Note: `file_data` is unsupported in `FileArtifactService` and `GcsArtifactService`."

6. **[x] Approved — Add callout linking to scoping section**
   - ✅ Applied. Line 45 reads: "All methods are `async` with keyword-only arguments, scoped by `app_name`, `user_id`, and optional `session_id` (see Scoping section below)."

7. **[x] Approved — Add parenthetical "(see 07-events.md)" for `artifact_delta` on EventActions**
   - ✅ Applied. Line 126 reads: "The `artifact_delta` on `EventActions` (see [07-events.md](07-events.md)) records which artifacts were created/updated during a tool call..."

8. **[x] Approved — Add sentence about InMemoryArtifactService being serializable (snapshots)**
   - ✅ Applied. Line 105 reads: "`InMemoryArtifactService` extends `BaseModel` (Pydantic), making its state serializable — useful for snapshotting or persisting in-memory artifacts between sessions."

9. **[x] Approved — Move `ArtifactVersion` metadata block to just before versioning semantics section**
   - ✅ Applied. `ArtifactVersion` class definition is at lines 113–120, in the "Versioning Semantics" section — not between Class Hierarchy and BaseArtifactService.

10. **[x] Approved — Add guard clause example for unconfigured artifact service**
    - ✅ Applied. Lines 163–170 show a `try/except ValueError` pattern.

**Summary for 12-artifacts.md:** All 9 approved items (plus one bonus guard clause item) applied. ✅

---

## 13-auth.md

**0 items approved** (all review items left unchecked — no approved or denied markings). No changes were required or expected from the review.

However, note that the current `13-auth.md` shows significant improvements (full examples, `CallbackContext`/`ToolContext` alias note, guard clause, `credential_key` section moved before examples, `AuthScheme`/FastAPI note). These changes were applied independently of the review, or the review represents a pre-edit snapshot.

**Summary for 13-auth.md:** No approved items to audit. All review items were left unchecked (neither approved nor denied).

---

## Overall Summary

| File | Approved Items | Applied | Missed |
|------|---------------|---------|--------|
| 07-events.md | 8 | 7 | 1 |
| 08-sessions.md | 6 | 6 | 0 |
| 09-tools.md | 5 | 5 (+ 1 extra) | 0 |
| 10-apps.md | 12 | 12 | 0 |
| 11-memory.md | 8 | 8 | 0 |
| 12-artifacts.md | 9 | 9 (+ 1 extra) | 0 |
| 13-auth.md | 0 | — | — |

### Missed Items

**07-events.md — Replace opaque IDs with descriptive labels**

The review approved replacing `"evt-002"` and `"e-inv-9f2a"` style labels with descriptive labels like "Tool Call" and "weather lookup result". The "Events in a Single Turn" diagram still uses `evt-001` through `evt-004`, and the "Branch Filtering" diagram uses `evt-001` through `evt-008`. These opaque IDs were not replaced with descriptive labels.
