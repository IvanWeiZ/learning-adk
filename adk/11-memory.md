# Memory — Long-Term Recall Across Sessions

> **Official docs:** [Memory](https://google.github.io/adk-docs/runtime/memory/) | **Source:** [`base_memory_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/memory/base_memory_service.py) · [`in_memory_memory_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/memory/in_memory_memory_service.py) · [`vertex_ai_memory_bank_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/memory/vertex_ai_memory_bank_service.py) | **Prereqs:** [08-sessions.md](08-sessions.md)

---

## What It Is

`Memory` lets agents recall information from past sessions. Unlike `Session.state` (one conversation), memory stores searchable entries that persist across conversations. Storage is not automatic — requires explicit `add_session_to_memory()` call or a callback wired to trigger it.

Comparison:

| | Session State | Memory |
|---|---|---|
| Scope | One session | All sessions for a user/app |
| Lifetime | Until session deleted | Indefinitely |
| Access | Direct key lookup | Semantic / vector search |
| Written by | Agent via `state_delta` | App code or Runner at end of session |
| Typical content | Cart, draft, current task | User preferences, past decisions, facts |

Optional. Skip for agents that don't need cross-session recall.

### When to Use Memory vs Session State

```
Need to remember something?
│
├── Within this conversation only?
│   └── Use session.state (via state_delta in EventActions)
│
├── Across conversations, exact key known?
│   └── Use user-scoped state: state['user:preference_key']
│
└── Across conversations, needs semantic search?
    └── Use memory_service.add_session_to_memory() + search_memory()
```

---

## Class Hierarchy

```
BaseMemoryService (memory/base_memory_service.py — abstract interface)
 ├── InMemoryMemoryService (dev/test — stores in Python dicts)
 └── VertexAiMemoryBankService (production — Vertex AI Memory Bank, vector search)
```

---

## Core Data Types

### MemoryEntry

Unit of storage:

```python
class MemoryEntry(BaseModel):
    content: types.Content # the remembered information (text, structured data)
    author: Optional[str] = None # who produced this (agent name or 'user')
    timestamp: Optional[str] = None # when this was stored (ISO 8601)
    id: Optional[str] = None # unique identifier
    custom_metadata: Optional[dict] = None # arbitrary key-value metadata
    # (Vertex AI backend adds an embedding vector internally)
```

### SearchMemoryResponse

What comes back from a query:

```python
class SearchMemoryResponse(BaseModel):
    memories: list[MemoryEntry]
```

---

## BaseMemoryService — The Interface

```python
class BaseMemoryService(ABC):

    async def add_session_to_memory(self, session: Session) -> None:
        """
        Distills a completed session into memory entries.
        Called by the app/runner after a session ends.
        The implementation decides what to extract and how to store it.
        """

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """
        Semantic search over past sessions for this user.
        Returns ranked MemoryEntry list.
        """
```

Two methods. Complexity lives in implementations.

---

## Implementations

### InMemoryMemoryService

Stores event text in a list; search is case-insensitive exact substring matching (not fuzzy/semantic).

```python
from google.adk.memory import InMemoryMemoryService

memory_service = InMemoryMemoryService()
```

- **Use for:** development, unit tests, demos
- **Not for:** production (no persistence, no semantic search, no scale)

### VertexAiMemoryBankService

Sends sessions to Vertex AI Memory Bank:
1. Uses an LLM to extract key facts/summaries from the session
2. Embeds them as vectors
3. Supports semantic similarity search at query time

```python
from google.adk.memory import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project="my-gcp-project",
    location="us-central1",
    agent_engine_id="projects/.../agentEngines/...",
)
```

- **Use for:** production systems with Vertex AI
- **Provides:** LLM-extracted facts, semantic vector search, managed scaling

---

## How Memory Plugs In

### Visual: Cross-Session Timeline

```
Session A (March 1)
│
├── User: "I love sushi"
├── Agent: "Great taste!"
└── End of session:
    └── add_session_to_memory(session_A)
        └── stored in MemoryService

        ↓ days pass...

Session B (March 5)
│
├── User: "Where should I eat?"
├── load_memory_tool triggers:
│   └── search_memory("eat")
│       └── finds: "User loves sushi" (from Session A)
│           └── injected into LLM prompt
│
└── Agent: "Since you love sushi, try Tsukiji restaurant!"
```

### Without Memory vs With Memory

```
WITHOUT memory:
 Session B prompt: "You are a helpful assistant."
 Agent has NO idea user likes sushi → generic restaurant suggestions

WITH memory:
 Session B prompt: "You are a helpful assistant.
 Relevant memories: User mentioned they love sushi (March 1)"
 Agent recommends sushi restaurants → personalized answer
```

### Wiring to Runner

Pass the memory service to `Runner` alongside the session service:

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

runner = Runner(
    agent=root_agent,
    app_name="my_app",
    session_service=InMemorySessionService(),
    memory_service=InMemoryMemoryService(), # ← plug in here
)
```

### Saving a Session to Memory

After a session completes, call `add_session_to_memory`:

```python
# Refetch session to get complete event history (the runner loop may have ended)
session = await session_service.get_session(
    app_name="my_app", user_id="alice", session_id="sess_123"
)
await memory_service.add_session_to_memory(session)
```

### Querying Memory in a Tool

Inside a tool, use `tool_context` to access the memory service:

```python
from google.adk.tools import ToolContext

async def recall_past_preferences(query: str, tool_context: ToolContext) -> str:
    """Search the user's memory for relevant past information."""
    response = await tool_context.search_memory(query)
    if not response.memories:
        return "No relevant past information found."
    top = response.memories[0]
    return f"From a past session: {top.content.parts[0].text}"
```

ADK automatically injects `tool_context` when the function parameter is named `tool_context`.

---

## Practical Patterns

### Pattern 1: Automatic Memory on Session End

```python
from google.adk.agents import LlmAgent

# Note: add_session_to_memory() lives on BaseMemoryService, not on CallbackContext.
# The callback accesses the memory service via the invocation context.
async def after_agent(callback_context) -> None:
    session = callback_context._invocation_context.session
    memory_service = callback_context._invocation_context.memory_service
    if memory_service:
        await memory_service.add_session_to_memory(session)

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    after_agent_callback=after_agent,
)
```

### Pattern 2: Memory-Augmented System Prompt

Inject memories into the system prompt via `before_model_callback`:

```python
async def inject_memories(callback_context, llm_request) -> None:
    query = llm_request.contents[-1].parts[0].text # last user message
    results = await callback_context.search_memory(query)
    if results.memories:
        snippets = "\n".join(
            f"- {m.content.parts[0].text}" for m in results.memories[:3]
        )
        memory_block = f"\n\nRelevant past context:\n{snippets}"
        # Guard: system_instruction may be None or str
        existing = llm_request.config.system_instruction or ""
        llm_request.config.system_instruction = existing + memory_block
```

### Pattern 3: Explicit Memory Tool

Agent-controlled memory recall:

```python
async def search_my_memory(topic: str, tool_context: ToolContext) -> str:
    """Search your memory for information about a topic from past conversations."""
    results = await tool_context.search_memory(topic)
    if not results.memories:
        return "Nothing relevant found."
    return "\n".join(
        m.content.parts[0].text
        for m in results.memories[:5]
    )

agent = LlmAgent(
    name="memory_agent",
    model="gemini-2.5-flash",
    tools=[search_my_memory],
)
```

---

## Related

- [`memory/base_memory_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/memory/base_memory_service.py) — abstract interface
- [`memory/in_memory_memory_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/memory/in_memory_memory_service.py) — dev implementation
- [`memory/vertex_ai_memory_bank_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/memory/vertex_ai_memory_bank_service.py) — production implementation
- [08-sessions.md](08-sessions.md) — session state (within-session persistence)
- [09-tools.md](09-tools.md) — `ToolContext` provides `search_memory()` for tool-based memory access
- [10-apps.md](10-apps.md) — App container that holds the memory service
- [03-runners.md](03-runners.md) — Runner that threads memory_service into context
