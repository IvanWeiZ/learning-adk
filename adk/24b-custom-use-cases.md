# 24b — Custom Use Cases: Parse, Enrich, and Respond Patterns

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [`agents/`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/) · [`tools/`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/) | **Prereqs:** [02-when-to-build-what.md](02-when-to-build-what.md)

*This file continues from [02-when-to-build-what.md](02-when-to-build-what.md), which covers decision trees and quick reference tables.*

---

## Use Case 1 — Parse the User Message, Enrich with API Context, Feed Only Enriched Context to the Responder Agent

**Scenario:**
The user sends a raw message like `"abc media_id:1"`. You want to:
1. Extract the clean query (`"abc"`) and structured IDs (`media_id=1`)
2. Call external APIs to fetch context for those IDs (media record, user profile, etc.)
3. Hand off to a **responder agent** that sees the enriched context — not the raw original message

The raw message is fine sitting in session events for auditing. The key is that the **responder agent's LLM never sees it**. That is controlled by `include_contents="none"` on the responder — not by deleting it from the session.

**What the responder agent's LLM should receive:**
```
User query is: abc

Current media is:
 id: 1
 title: "Summer Reel"
 tags: ["outdoor", "sports"]

Additional context for the user:
 name: Alice
 tier: premium
 watch_history: [...]

Additional context for the media:
 recommendations: [...]
 trending_score: 0.87
```

---

### How it works: `include_contents="none"` is the key

`LlmAgent` has a field `include_contents: Literal["default", "none"]`. See [05-flows.md](05-flows.md) for full details on content filtering.

- `"default"` — the flow includes all session events (filtered by branch) in the LlmRequest.
- `"none"` — the flow sends **zero** contents to the LLM. Only the system prompt (instruction) is sent.

So the pattern is:
1. **Stage 1** (extractor): parse the raw message, call APIs, write results to `session.state`
2. **Stage 2** (responder): `include_contents="none"` + `instruction` with `{variable}` placeholders that resolve from `session.state`

Stage 2 is completely isolated. It reads only what stage 1 wrote to state.

---

### Three Options for Stage 1 (the extraction step)

The responder agent is always the same. What varies is how you do the extraction.

---

### Comparison

| | Option A: `before_agent_callback` | Option B: `SequentialAgent` | Option C: `before_model_callback` |
|--|-----------------------------------|------------------------------|------------------------------------|
| Extra LLM calls | 0 | 1 (extractor) | 0 |
| Extraction type | Regex / pure Python | LLM + tools | Regex / pure Python |
| Agent structure | 1 agent + 1 callback | 2 agents | 1 agent + 1 callback |
| Responder isolation | `include_contents="none"` | `include_contents="none"` | Rewrites contents in-place |
| Best when | Fast deterministic parsing | Ambiguous/complex extraction | Same as A, slightly more direct |

**Rule of thumb:**
- Parsing is regex/rules → **Option A** (cleanest) or **Option C**
- Parsing needs LLM reasoning → **Option B**

---

#### Option A — `before_agent_callback` on the pipeline (simplest, no extra LLM call)

Use `before_agent_callback` on the root `SequentialAgent` to parse the message and call APIs **before any agent runs**. Pure Python, no LLM involved in extraction. Results go to session state. Then the responder reads from state.

```
before_agent_callback fires (on SequentialAgent)
 ► read ctx.user_content (the raw "abc media_id:1")
 ► parse IDs with regex
 ► call media API + user API concurrently
 ► write to callback_context.state["clean_query"], ["media_context"], ["user_context"]
 ► return None → pipeline runs normally
 │
 ▼
responder_agent (include_contents="none")
 ► instruction resolves {clean_query}, {media_context}, {user_context} from state
 ► LLM sees only the enriched system prompt, nothing else
```

```python
import re
import asyncio
import json
import httpx
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# --- Parsing helper ---
def parse_user_message(raw: str) -> tuple[str, dict]:
    """'abc media_id:1' → ('abc', {'media_id': '1'})"""
    ids = {}
    clean = raw
    for match in re.finditer(r'(\w+_id):(\w+)', raw):
        ids[match.group(1)] = match.group(2)
        clean = clean.replace(match.group(0), '').strip()
    return clean.strip(), ids

# --- The callback: runs before any agent in the pipeline ---
async def enrich_before_pipeline(callback_context: CallbackContext):
    # Read the raw user message from context
    # WARNING: _invocation_context is private — may change between ADK versions.
    user_content = callback_context._invocation_context.user_content
    if not user_content or not user_content.parts:
        return None

    raw = user_content.parts[0].text or ""
    clean_query, ids = parse_user_message(raw)

    # Fetch API context concurrently
    async with httpx.AsyncClient() as client:
        tasks = {}
        if "media_id" in ids:
            tasks["media"] = client.get(f"https://api.example.com/media/{ids['media_id']}")
        if "user_id" in ids:
            tasks["user"] = client.get(f"https://api.example.com/users/{ids['user_id']}")

        responses = {k: (await v).json() for k, v in zip(tasks.keys(), await asyncio.gather(*tasks.values()))}

    # Write enriched context to session state
    callback_context.state["clean_query"] = clean_query
    callback_context.state["media_context"] = json.dumps(responses.get("media", {}), indent=2)
    callback_context.state["user_context"] = json.dumps(responses.get("user", {}), indent=2)

    return None # proceed — don't short-circuit the pipeline

# --- Responder: never sees the raw message ---
responder_agent = LlmAgent(
    name="responder",
    model="gemini-2.5-flash",
    include_contents="none", # ← zero session history sent to LLM
    instruction="""
    You are a helpful media assistant.

    User query is: {clean_query}

    Current media:
    {media_context}

    User context:
    {user_context}

    Answer the user's query based only on the context above.
    """,
)

# --- Wire it up ---
pipeline = SequentialAgent(
    name="media_pipeline",
    sub_agents=[responder_agent], # just the responder; extraction is in the callback
    before_agent_callback=enrich_before_pipeline,
)
```

**Tradeoffs:**
- Zero extra LLM calls — extraction is pure Python
- Simplest structure — one agent, one callback
- Parsing logic is hardcoded — no LLM reasoning during extraction
- Complex extraction (ambiguous queries, nested structures) needs more code

---

#### Option B — `SequentialAgent` with extractor `LlmAgent` (LLM does the extraction)

Use a first LlmAgent to parse and enrich using tools. The LLM handles ambiguous or complex extraction. Results are stored in state. The responder reads from state with `include_contents="none"`.

```
SequentialAgent
 │
 ├─ extractor_agent (LlmAgent — sees raw message, calls tools)
 │  ► parse_and_extract("abc media_id:1")
 │  ► state["clean_query"] = "abc"
 │  ► state["media_context"] = "{...}"
 │  ► state["user_context"] = "{...}"
 │
 └─ responder_agent (LlmAgent — include_contents="none")
    ► instruction: "User query is: {clean_query} ..."
    ► LLM sees only the enriched system prompt
```

```python
import re
import json
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext

def parse_and_extract(raw_query: str, tool_context: ToolContext) -> dict:
    """Parse the raw user message. Saves clean_query to state.

    Args:
        raw_query: The original user message, e.g. 'abc media_id:1'.
    """
    ids = {}
    clean = raw_query
    for match in re.finditer(r'(\w+_id):(\w+)', raw_query):
        ids[match.group(1)] = match.group(2)
        clean = clean.replace(match.group(0), '').strip()
    tool_context.state["clean_query"] = clean.strip()
    return {"clean_query": clean.strip(), **ids}

async def fetch_and_store_media(media_id: str, tool_context: ToolContext) -> dict:
    """Fetch media record and save to state['media_context'].

    Args:
        media_id: The media ID extracted from the user's message.
    """
    import httpx
    async with httpx.AsyncClient() as client:
        data = (await client.get(f"https://api.example.com/media/{media_id}")).json()
    tool_context.state["media_context"] = json.dumps(data, indent=2)
    return data

async def fetch_and_store_user(user_id: str, tool_context: ToolContext) -> dict:
    """Fetch user profile and save to state['user_context'].

    Args:
        user_id: The user ID extracted from the user's message.
    """
    import httpx
    async with httpx.AsyncClient() as client:
        data = (await client.get(f"https://api.example.com/users/{user_id}")).json()
    tool_context.state["user_context"] = json.dumps(data, indent=2)
    return data

extractor_agent = LlmAgent(
    name="extractor",
    model="gemini-2.5-flash",
    instruction="""
    You are a message parser. Given the user's raw message:
    1. Call parse_and_extract with the full raw message.
    2. If a media_id was returned, call fetch_and_store_media with it.
    3. If a user_id was returned, call fetch_and_store_user with it.
    Respond with nothing else. Only call the tools.
    """,
    tools=[parse_and_extract, fetch_and_store_media, fetch_and_store_user],
)

responder_agent = LlmAgent(
    name="responder",
    model="gemini-2.5-flash",
    include_contents="none", # ← never sees extractor's conversation or raw message
    instruction="""
    You are a helpful media assistant.

    User query is: {clean_query}

    Current media:
    {media_context}

    User context:
    {user_context}

    Answer the user's query based only on the context above.
    """,
)

pipeline = SequentialAgent(
    name="media_pipeline",
    sub_agents=[extractor_agent, responder_agent],
)
```

**Tradeoffs:**
- LLM handles ambiguous parsing ("find that sports clip from yesterday media_id:5")
- Extractor and responder are independently testable
- Easy to add more extraction tools without changing the responder
- 2 LLM calls per turn (extractor + responder)
- More moving parts

---

#### Option C — `before_model_callback` on the responder (no SequentialAgent needed)

If you don't want a two-agent structure at all, use a single agent with `before_model_callback`. It rewrites `llm_request.contents` just before the LLM call — the LLM receives the enriched version, never the raw string. See [04-agents.md](04-agents.md) for the full `before_model_callback` API.

```
Single LlmAgent
 ► flow builds LlmRequest with raw "abc media_id:1" in contents
 ► before_model_callback fires
 ► parse + call APIs
 ► replace llm_request.contents[-1] with enriched text
 ► LLM sees enriched message
```

```python
from google.adk.models.llm_request import LlmRequest

async def enrich_before_model(callback_context: CallbackContext, llm_request: LlmRequest):
    # Find the last plain-text user message in the request
    for i in range(len(llm_request.contents) - 1, -1, -1):
        c = llm_request.contents[i]
        if c.role == "user" and c.parts and c.parts[0].text:
            raw = c.parts[0].text
            clean_query, ids = parse_user_message(raw)
            if not ids:
                return None # nothing to enrich

            async with httpx.AsyncClient() as client:
                media = (await client.get(f"https://api.example.com/media/{ids['media_id']}")).json() if "media_id" in ids else {}
                user = (await client.get(f"https://api.example.com/users/{ids['user_id']}")).json() if "user_id" in ids else {}

            enriched = (
                f"User query is: {clean_query}\n\n"
                + (f"Current media:\n{json.dumps(media, indent=2)}\n\n" if media else "")
                + (f"User context:\n{json.dumps(user, indent=2)}" if user else "")
            )
            llm_request.contents[i] = types.Content(
                role="user", parts=[types.Part(text=enriched.strip())]
            )
            return None # proceed with modified request
    return None

agent = LlmAgent(
    name="media_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful media assistant.",
    before_model_callback=enrich_before_model,
)
```

**Tradeoffs:**
- Simplest possible structure — one agent, one callback, no SequentialAgent
- 1 LLM call per turn
- Enrichment logic is embedded in a callback, harder to test
- Doesn't work if you need an LLM to do the extraction

---


---


## Related

- [02-when-to-build-what.md](02-when-to-build-what.md) — Decision trees and quick reference tables
- [04-agents.md](04-agents.md) — Agent types deep dive
- [09-tools.md](09-tools.md) — Tool system reference
