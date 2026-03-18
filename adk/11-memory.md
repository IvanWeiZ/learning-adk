# Memory — Long-Term Recall Across Sessions

**Source:** [`memory/base_memory_service.py`](../adk-python/src/google/adk/memory/base_memory_service.py) · [`memory/in_memory_memory_service.py`](../adk-python/src/google/adk/memory/in_memory_memory_service.py) · [`memory/vertex_ai_memory_bank_service.py`](../adk-python/src/google/adk/memory/vertex_ai_memory_bank_service.py)

---

## What It Is

`Memory` gives agents the ability to recall information from **past sessions** — not just the current conversation. Where `Session.state` is ephemeral to one conversation thread, the memory service stores distilled facts or entire sessions as searchable entries that survive across conversations.

Think of the distinction as:

| | Session State | Memory |
|---|---|---|
| Scope | One session | All sessions for a user/app |
| Lifetime | Until session deleted | Indefinitely |
| Access | Direct key lookup | Semantic / vector search |
| Written by | Agent via `state_delta` | App code or Runner at end of session |
| Typical content | Cart, draft, current task | User preferences, past decisions, facts |

The memory service is optional. Agents that don't need cross-session recall don't need it.

---

## Class Hierarchy

```
BaseMemoryService           (memory/base_memory_service.py — abstract interface)
    ├── InMemoryMemoryService       (dev/test — stores in Python dicts)
    └── VertexAiMemoryBankService   (production — Vertex AI Memory Bank, vector search)
```

---

## Core Data Types

### MemoryEntry

The unit of storage. A memory is a distilled piece of information with metadata:

```python
class MemoryEntry(BaseModel):
    content: types.Content                    # the remembered information (text, structured data)
    author: Optional[str] = None              # who produced this (agent name or 'user')
    timestamp: Optional[str] = None           # when this was stored (ISO 8601)
    id: Optional[str] = None                  # unique identifier
    custom_metadata: Optional[dict] = None    # arbitrary key-value metadata
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

That's the entire interface — two methods. The complexity lives in the implementations.

---

## Implementations

### InMemoryMemoryService

Stores the full text of all events in a Python list; search is simple substring/keyword matching.

```python
from google.adk.memory import InMemoryMemoryService

memory_service = InMemoryMemoryService()
```

- **Use for:** development, unit tests, demos
- **Not for:** production (no persistence, no semantic search, no scale)

### VertexAiMemoryBankService

Sends sessions to Vertex AI Memory Bank, which:
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
    memory_service=InMemoryMemoryService(),   # ← plug in here
)
```

### Saving a Session to Memory

After a session completes, call `add_session_to_memory`:

```python
session = await session_service.get_session(
    app_name="my_app", user_id="alice", session_id="sess_123"
)
await memory_service.add_session_to_memory(session)
```

Some apps do this automatically in an `after_agent_callback` or as a post-processing step.

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

## Memory vs Session State — Decision Guide

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

## Practical Patterns

### Pattern 1: Automatic Memory on Session End

```python
from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

async def after_agent(callback_context) -> None:
    await callback_context.add_session_to_memory()

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    after_agent_callback=after_agent,
)
```

### Pattern 2: Memory-Augmented System Prompt

Fetch relevant memories before the LLM call and inject them into the system prompt via `before_model_callback`:

```python
async def inject_memories(callback_context, llm_request) -> None:
    query = llm_request.contents[-1].parts[0].text  # last user message
    results = await callback_context.search_memory(query)
    if results.memories:
        snippets = "\n".join(
            f"- {m.content.parts[0].text}" for m in results.memories[:3]
        )
        llm_request.config.system_instruction += f"\n\nRelevant past context:\n{snippets}"
```

### Pattern 3: Explicit Memory Tool

Give the agent a tool to explicitly recall memories on demand — only when the agent judges it relevant:

```python
async def search_my_memory(topic: str, tool_context: ToolContext) -> str:
    """Search your memory for information about a topic from past conversations."""
    results = await tool_context.search_memory(topic)
    if not results.memories:
        return "Nothing relevant found."
    return "\n".join(
        f"{m.content.parts[0].text}"
        for m in results.memories[:5]
    )

agent = LlmAgent(
    name="memory_agent",
    model="gemini-2.5-flash",
    tools=[search_my_memory],
)
```

---

## Java Comparison

| Java concept | ADK equivalent |
|---|---|
| `EntityManager` / JPA | `BaseMemoryService` |
| Full-text search index | `search_memory()` |
| `@Cacheable` across requests | `add_session_to_memory` + `search_memory` |
| `HttpSession` attributes | `Session.state` (per-session, not cross-session) |

---

## Related Files

- [`memory/base_memory_service.py`](../adk-python/src/google/adk/memory/base_memory_service.py) — abstract interface
- [`memory/in_memory_memory_service.py`](../adk-python/src/google/adk/memory/in_memory_memory_service.py) — dev implementation
- [`memory/vertex_ai_memory_bank_service.py`](../adk-python/src/google/adk/memory/vertex_ai_memory_bank_service.py) — production implementation
- [`08-sessions.md`](./08-sessions.md) — session state (within-session persistence)
- [`10-apps.md`](./10-apps.md) — App container that holds the memory service
- [`03-runners.md`](./03-runners.md) — Runner that threads memory_service into context
