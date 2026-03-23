# Audit Report: Files 00–06
Generated: 2026-03-22

---

## 00-onboarding-guide.md

### [x] Denied — Delete lines 119-139 (side-by-side layout)
> Decision: Denied. No action required.
> **Status:** N/A (Denied — not expected to be applied)
> **Note:** The side-by-side section (lines 119-141 in current file) is still present. This was denied, so that is correct.

### [x] Denied — Delete lines 145-198 (full architecture diagram)
> Decision: Denied. No action required.
> **Status:** N/A (Denied — not expected to be applied)
> **Note:** The full architecture diagram (lines 147-203 in current file) is still present. This was denied, so that is correct.

### [x] Approved — Add comments on lines 103 and 105 (user message and stream termination)
> **Status:** ✅ Applied
> Line 105: `types.Content(role="user", parts=[types.Part(text="What's the weather in Tokyo?")]),  # the user's message`
> Line 107: `if event.is_final_response():  # stream ends when final_response is True`

### [x] Approved — Add one sentence before the code block: "To run an agent, you need a Runner (orchestrates requests) and a SessionService (stores conversation history)."
> **Status:** ✅ Applied
> Line 89: `To run an agent, you need a Runner (orchestrates requests) and a SessionService (stores conversation history).`

---

## 01-request-lifecycle.md

### [x] Approved — Delete duplicate prose paragraph after At-a-Glance diagram (line 37)
> **Status:** ✅ Applied
> The paragraph that previously duplicated the ASCII summary is gone. The At-a-Glance section flows directly into "How It Works".

### [x] Approved — Keep line 582, delete lines 584 and 590 (duplicate "See 18-session-lifecycle.md" references)
> **Status:** ✅ Applied
> The Related section contains a single mention of `18-session-lifecycle.md` in the Gotchas → Session Service section (line 560), and the Related section links are clean. No duplicate references to `18-session-lifecycle.md` appear within a few lines of each other.

### [x] Approved — Compress callback signatures block (lines 527-563) to summary table + link, targeting under 600 lines
> **Status:** ✅ Applied
> Lines 530-541 now contain a compact summary table ("Signatures and Return Effects") with a link to `04-agents.md` for full signatures. The verbose callback signatures block has been replaced. File is 600 lines.

### [x] Approved — Add one sentence clarifying partial JSON chunks vs partial text at lines 302-305
> **Status:** ✅ Applied
> Line 305: `> Unlike text streaming (where partial chunks are substrings), function-call streaming yields incomplete JSON objects — the partial chunk may have missing fields until partial=False.`

### [x] Approved — Add forward reference to Step 8 at line 401 explaining why partial events don't persist
> **Status:** ✅ Applied
> Line 401: `Partial events are yielded but not persisted (no session I/O). This is why the Step 8 session snapshot contains only 4 events — the partial chunks (evt-004a/b/c) are not stored.`

### [x] Comment — Move "Key Concepts" before At a Glance
> User comment: `actually move key concept before At a Glance`
> **Status:** ✅ Applied
> "Key Concepts" (lines 7-22) now appears before "At a Glance" (line 24).

### [x] Approved — Add comment signaling pseudocode or use real field names at lines 429-440
> **Status:** ✅ Applied
> Line 430: `# Pseudocode — field names abbreviated for readability`

### [x] Approved — Replace callback signatures block (lines 527-563) with compact summary table + link to 04-agents.md; keep one-sentence state-scope summary inline
> **Status:** ✅ Applied (same as the "Split/compress" item above — both refer to the same block)

---

## 02-when-to-build-what.md

### [x] Approved — Delete duplicate "Quick Decision Tree" (lines 50-88), merge BasePlanner/BaseCodeExecutor/A2A into At a Glance
> **Status:** ✅ Applied
> There is only one decision tree ("At a Glance", lines 7-47). It includes `BasePlanner`, `BaseCodeExecutor`, and A2A entries. The second "Quick Decision Tree" is gone.

### [x] Approved — Delete "Examples" section heading + move cross-reference into Related
> **Status:** ✅ Applied
> No standalone "Examples" section exists. The `custom-use-cases.md` reference appears in the Related section (line 190). Note: the link still reads `24b-custom-use-cases.md` — if this filename is wrong it should be verified separately.

### [x] Approved — No split needed
> **Status:** ✅ Acknowledged (no split was done; file is 195 lines)

### [x] Approved — Rename "How It Works (diagram before prose)" heading to "Scenario Reference" or "Reference"
> **Status:** ✅ Applied
> Line 53: `## Scenario Reference`

### [x] Approved — Replace six executor class names inline (line 110) with context or reference to detailed guide
> **Status:** ✅ Applied
> Line 72 now lists executor options inline with descriptions: `BuiltInCodeExecutor (model-native, simplest), ContainerCodeExecutor (Docker, isolated), UnsafeLocalCodeExecutor (no isolation — dev only). Cloud: VertexAiCodeExecutor, GkeCodeExecutor, AgentEngineSandboxCodeExecutor.`

### [x] Approved — Move parenthetical warning (line 116) to a separate callout before the table
> **Status:** ✅ Applied
> Line 80: `> **Note:** Parallel tool calls (automatic, within one turn) are different from ParallelAgent (concurrent sub-agents across invocations).` — appears as a callout, separate from the table rows.

### [x] Approved — Rename "Gotchas" section to "Component Quick Reference" or merge with Summary Table
> **Status:** ✅ Applied
> Line 157: `## Component Quick Reference`

### [x] Approved — Restructure to three sections: At a Glance → Scenario reference tables → Summary decision table → Related
> **Status:** ✅ Applied
> Structure is: At a Glance → Scenario Reference (tables) → Component Quick Reference (summary table) → Related.

### [x] Approved — Add one 6-line example comparing FunctionTool vs BaseTool
> **Status:** ✅ Applied
> Lines 138-153: "Quick Example: FunctionTool vs BaseTool" section with a side-by-side code block.

### [x] Approved — Keep Summary Table (adds When/Key base class columns), delete at least one of the two trees
> **Status:** ✅ Applied (second tree deleted, Summary Table / Component Quick Reference retained with expanded columns)

---

## 03-runners.md

### [x] Comment — Change "Class Hierarchy" section name to "comparison between runner, agent, session"
> User comment: `change the name to comparison between runner, agent, session`
> **Status:** ✅ Applied
> Line 40: `## Runner vs Agent vs Session`

### [x] Approved — Break line 36 run-on into two sentences
> **Status:** ✅ Applied
> Line 36: `Runner owns the lifecycle of a single user request: fetch or create a session, build an invocation context, call the root agent, stream events back to the caller, and persist them. Runner is stateless — all state lives in Session — so one Runner instance serves many concurrent users.`

### [x] Approved — Add one-line example of passing a plugin via App, or reference 10-apps.md with context (lines 179-183)
> **Status:** ✅ Applied
> Lines 183-186: `app = App(root_agent=agent, plugins=[MyPlugin()])` + `runner = app.create_runner(session_service=InMemorySessionService())` and a reference to `10-apps.md`.

### [x] Approved — Add `from google.genai import types` import line (lines 219-242)
> **Status:** ✅ Applied
> Line 223: `from google.genai import types`

### [x] Approved — Reword thread-safety gotcha (line 250)
> **Status:** ✅ Applied
> Line 255: `Each concurrent invocation must use a different session_id — sharing a session_id across concurrent calls causes undefined behavior because Session is stateful.`

### [x] Approved — Trim "Session Auto-Creation" paragraph to one sentence, cross-reference Gotchas
> **Status:** ✅ Applied
> Line 157-159: `### Session Auto-Creation` reduced to: `Set auto_create_session=True for demos/scripts; defaults to False (see Gotchas).`

### [x] Denied — Cut/tighten prose after compaction diagram (lines 207-213)
> Decision: Denied. No action required.
> **Status:** N/A (Denied — not expected to be applied)
> **Note:** The prose after the compaction diagram (lines 210-216) is still present. This was denied, so that is correct.

---

## 04-agents.md

### [x] Approved — Delete duplicate Class Hierarchy section (lines 37-47), move type alias note to At-a-Glance prose
> **Status:** ✅ Applied
> There is no duplicate class hierarchy section after the At-a-Glance box. The type alias note (`Agent is a type alias for LlmAgent`) appears in the At-a-Glance prose at line 31.

### [x] Approved — Delete "Branch in Events" section (lines 380-393, third pass over transfer mechanics)
> **Status:** ✅ Applied
> No such section exists in the current file. Transfer mechanics are covered once in the "How Agent Transfer Works" section.

### [x] Denied — Add dedicated sections for composition agents or split to companion file
> Decision: Denied. No action required.
> **Status:** N/A (Denied)
> **Note:** However, composition agent examples (SequentialAgent, ParallelAgent, LoopAgent) were added to the Examples section — see the "Add construction examples" item below.

### [x] Approved — Move prose explanation before the flow-selection diagram (lines 138-151)
> **Status:** ✅ Applied
> Line 122: `ADK auto-selects the flow based on three conditions. AutoFlow extends SingleFlow — it adds agent transfer/delegation on top of the basic reason-act loop.` appears before the tree diagram at lines 124-133.

### [x] Approved — Move output_schema workaround block (lines 173-177) to Gotchas section
> **Status:** ✅ Applied
> The Gotchas section (line 518) contains: `output_schema and tools are mutually exclusive — when output_schema is set, the agent cannot use tools. Workaround: use output_key to capture text then parse, or use a 2-agent pipeline (agent 1 uses tools, agent 2 formats with output_schema).`
> The field list at line 157-158 no longer has an inline workaround block.

### [x] Denied — Move InvocationContext section to just before "Agent Trees and Transfer"
> Decision: Denied. No action required.
> **Status:** N/A (Denied — InvocationContext remains at lines 211-250, before Agent Trees at line 252)

### [x] Approved — Add construction examples for each composition agent type
> **Status:** ✅ Applied
> Lines 381-418: SequentialAgent, ParallelAgent, and LoopAgent examples added with explanatory comments.

### [x] Approved — Replace thin "Minimal Multi-Agent Example" (lines 399-413) with composition agent example or expand inline
> **Status:** ✅ Applied
> The thin example is gone; the Examples section now opens with "LlmAgent with Routing (Multi-Agent)" (lines 363-379) followed by composition agent examples.

### [x] Denied — Keep InvocationContext field reference table, cut narrative and cross-reference 03-runners.md
> Decision: Denied. No action required.
> **Status:** N/A (Denied — full InvocationContext section with narrative retained)

---

## 05-flows.md

### [x] Approved — Delete "Two Iterations in Practice" section (lines 65-80)
> **Status:** ✅ Applied
> No such section exists in the current file. The file goes from the Loop Iteration Flowchart directly to "The Loop in Detail".

### [x] Approved — Delete or expand "Live Mode" section (lines 167-170)
> **Status:** ✅ Applied
> No "Live Mode" section exists in the current file. Live API references are handled by the `run_live()` entry in `03-runners.md`.

### [x] Approved — Add one sentence: "LlmAgent selects and assigns the flow at construction time based on its configuration"
> **Status:** ✅ Applied
> Line 9: `LlmAgent selects and assigns the flow at construction time based on its configuration, then _run_async_impl delegates to self._llm_flow.run_async(ctx).`

### [x] Approved — Add parenthetical note cross-referencing SingleFlow/AutoFlow relationship to 23-advanced-internals.md
> **Status:** ✅ Applied
> Line 33: `AutoFlow extends SingleFlow — it adds the agent_transfer.py response processor on top of the basic loop. See 04-agents.md for the full flow selection logic and 23-advanced-internals.md for the complete processor pipeline.`

### [x] Approved — Add one sentence: cache fields apply only when context caching enabled; live_connect_config applies only to Live API
> **Status:** ✅ Applied
> Line 160 (in `06-models.md` LlmRequest section): `cache_config: Optional[...] # context cache configuration (only when caching enabled)` and `live_connect_config: Optional[...] # Live API connection config (Gemini Live only)`.
> In `05-flows.md` specifically: the processor table that listed these fields has been replaced with a summary + forward reference (lines 96-100). The cache/live fields are no longer listed in flows without context.

### [x] Approved — Standardize arrow usage (lines 152-163)
> **Status:** ✅ Applied
> The current file uses arrows consistently as label separators in the processor detail section (lines 62-91). No mixed causal/label arrow usage.

### [x] Approved — Delete or collapse Auth Flow section (lines 173-180) to one line; cross-reference 13-auth.md
> **Status:** ✅ Applied
> No "Auth Flow" section exists in the current file.

### [x] Approved — Add one short code example with real runner.run_async() syntax
> **Status:** ✅ Applied
> Lines 122-137: "Example" section with a real `async for event in runner.run_async(...)` code block.

### [x] Approved — Replace incomplete processor tables with summary and forward reference to 23-advanced-internals.md
> **Status:** ✅ Applied
> Lines 96-100: `## Processors` section is a summary paragraph with a forward reference: `For the complete processor pipeline with all 12 processors, see 23-advanced-internals.md.`

### [x] Approved — Collapse duplicate Auth Flow section to single line pointing to 13-auth.md
> **Status:** ✅ Applied (same as "Delete or collapse Auth Flow" item above)

---

## 06-models.md

### [x] Approved — Rewrite misaligned ASCII diagram (lines 73-83) using vertical list-based layout
> **Status:** ✅ Applied
> Lines 69-78: The streaming timeline is now a vertical tree-style layout:
> `├─ chunk 1 (partial=True)  → "The weather"    → stream to UI (real-time)`
> etc. No side-by-side column alignment.

### [x] Approved — Update `"claude-sonnet-4-5"` to a real model ID (line 115)
> **Status:** ✅ Applied
> Line 116: `Return AnthropicLlm(model="claude-sonnet-4-5-20250514")`
> **Note:** `claude-sonnet-4-5-20250514` is still not a real Anthropic model name — real IDs use the format `claude-3-5-sonnet-20241022`. The value was updated from `claude-sonnet-4-5` but may still be incorrect. Recommend verifying against the Anthropic API docs.

### [x] Approved — Move provider-specific model strings out of BaseLlm code block (line 28) to subclass sections
> **Status:** ✅ Applied
> The `BaseLlm` class block (lines 27-50) now shows only `model: str # model name string — see subclass sections for provider-specific formats`. Provider-specific examples appear only in the LLMRegistry section.

### [x] Approved — Add `# Gemini only` comment to connect() method
> **Status:** ✅ Applied
> Line 47: `def connect(self, llm_request: LlmRequest) -> BaseLlmConnection:` followed by `# Bidirectional streaming for Live API (audio/video). Gemini only.`

### [x] Approved — Add one sentence: cache fields apply when caching enabled; live_connect_config for Live API only
> **Status:** ✅ Applied
> Lines 159-163 in LlmRequest block: `cache_config: Optional[...] # context cache configuration (only when caching enabled)` and `live_connect_config: Optional[...] # Live API connection config (Gemini Live only)`

### [x] Approved — Add one sentence with example clarifying model inheritance behavior (lines 185-195)
> **Status:** ✅ Applied
> Lines 144-145: `Model inheritance: if an LlmAgent has model='' (default), it walks up the parent_agent chain looking for a non-empty model. Only if no ancestor sets a model does it fall back to DEFAULT_MODEL. See 04-agents.md for agent field resolution.`

### [x] Approved — Move "Default Model" section before "Adding a Custom Adapter" or add cross-reference to 04-agents.md
> **Status:** ✅ Applied
> The Default Model section (lines 133-145) now appears before LlmRequest (lines 149+) and before "Adding a Custom Adapter" (line 194). A cross-reference to `04-agents.md` is included in the section.

### [x] Approved — Add cross-reference at line 179 to 07-events.md: "See 07-events.md for how Event extends this"
> **Status:** ✅ Applied
> Line 190: `Event extends LlmResponse, so events carry all response fields plus author, invocation_id, actions, and branch. See 07-events.md for the full Event class hierarchy.`

---

## Summary

| File | Approved items | Applied | Not applied | Comments applied |
|------|---------------|---------|-------------|-----------------|
| 00-onboarding-guide.md | 2 | 2 | 0 | 0 |
| 01-request-lifecycle.md | 7 | 7 | 0 | 1 |
| 02-when-to-build-what.md | 9 | 9 | 0 | 0 |
| 03-runners.md | 5 | 5 | 0 | 1 |
| 04-agents.md | 5 | 5 | 0 | 0 |
| 05-flows.md | 9 | 9 | 0 | 0 |
| 06-models.md | 8 | 8 | 0 | 0 |
| **Total** | **45** | **45** | **0** | **2** |

All approved changes and user comments were applied. No missed items found.

### One Flag for Follow-Up

**06-models.md, model ID:** The review approved changing `claude-sonnet-4-5` to a real ID. The current file uses `claude-sonnet-4-5-20250514`. This format (`claude-sonnet-4-5-20250514`) does not follow Anthropic's naming convention (e.g., `claude-3-5-sonnet-20241022`). The model ID is likely still incorrect despite the update. Recommend replacing with a verified ID such as `claude-3-5-sonnet-20241022`.
