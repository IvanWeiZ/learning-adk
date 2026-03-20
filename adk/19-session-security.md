# 19 — Session Security: State & Data Protection

> **Official docs:** [Sessions](https://google.github.io/adk-docs/sessions/) | **Source:** [`sessions/state.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/state.py) · [`sessions/base_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/base_session_service.py) · [`sessions/in_memory_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/in_memory_session_service.py) · [`sessions/database_session_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/database_session_service.py) · [`sessions/_session_util.py`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/_session_util.py) | **Prereqs:** [08-sessions.md](08-sessions.md), [07-events.md](07-events.md), [20-best-practices.md](20-best-practices.md)

## At a Glance

State scoping diagram: see [08-sessions.md](08-sessions.md). Security implications below.

A single session leak exposes conversation history, credentials, and tool outputs to the wrong user. Multi-agent systems multiply the attack surface. This document covers common session/event leak vectors and their mitigations for multi-user/multi-tenant agent systems where session isolation matters.

For the security checklist, threat model, and deployment hardening guide, see [19b-security-checklist.md](19b-security-checklist.md).

---

## How It Works

### Session Isolation — The #1 Source of Privacy Incidents

**The Core Rule**

**Every `get_session`/`create_session` call MUST include the correct `user_id`.** ADK keys sessions by `(app_name, user_id, session_id)`. Wrong `user_id` = wrong session.

```python
# DANGEROUS: Hardcoded or missing user_id
session = await session_service.get_session(
    app_name="my_app",
    user_id="default", # Every user gets the SAME sessions!
    session_id=request.session_id,
)

# DANGEROUS: user_id from untrusted input without validation
session = await session_service.get_session(
    app_name="my_app",
    user_id=request.headers["X-User-Id"], # Client can spoof this!
    session_id=request.session_id,
)

# CORRECT: user_id from authenticated identity (e.g., JWT, OAuth)
user_id = get_authenticated_user_id(request) # Verified server-side
session = await session_service.get_session(
    app_name="my_app",
    user_id=user_id,
    session_id=request.session_id,
)
```

**What Happens When user_id Is Wrong**

```
Scenario: User A's request arrives with user_id="user_b" (due to a bug)
│
│   session_service.get_session(user_id="user_b", session_id=X)
│
├── Case 1: Session X belongs to user_b
│      returns user_b's full session (all events, all state)
│      User A now sees user_b's entire conversation history!
│
├── Case 2: Session X doesn't exist for user_b
│      returns None — no data leak, but broken UX
│
└── Case 3: auto_create_session=True
       creates a NEW session under user_b's account
       User A's messages now stored in user_b's namespace!
```

**Warning: list_sessions Can List ALL Users' Sessions**

The `BaseSessionService.list_sessions()` accepts an **optional** `user_id`. If you call it without a `user_id`, it returns sessions for ALL users:

```python
# DANGEROUS: If your API endpoint exposes this without forcing user_id
sessions = await session_service.list_sessions(app_name="my_app")
# → Returns sessions for ALL users!

# CORRECT: Always scope list_sessions to the authenticated user
sessions = await session_service.list_sessions(
    app_name="my_app",
    user_id=authenticated_user_id,
)
```

**Runner Has No Built-In Authorization**

This is critical: **`Runner` performs zero authentication or authorization.** It blindly passes `user_id` to the session service. **Your application layer is the ONLY security boundary.**

**Defense: Validate user_id at the Gateway**

```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Extract and verify user identity from JWT token."""
    payload = verify_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@app.post("/chat")
async def chat(
    message: str,
    session_id: str,
    user_id: str = Depends(get_current_user),
):
    session = await session_service.get_session(
        app_name="my_app",
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # ...
```

### Session ID Guessability — Don't Let Users Enumerate Sessions

```python
# DANGEROUS: Sequential session IDs — trivially guessable
session_id=str(session_counter) # "1", "2", "3"...

# CORRECT: Random UUIDs
session_id=str(uuid.uuid4()) # "a3f8b2c1-..."

# CORRECT: Let ADK generate the session ID (it uses UUIDs internally)
session = await session_service.create_session(
    app_name="my_app", user_id=user_id,
    # session_id omitted — ADK generates a UUID
)
```

### State Prefix Boundaries — Choosing the Right Scope

ADK state scoping is the primary mechanism for controlling data visibility. Picking the wrong prefix is one of the most common causes of cross-user data leakage.

**How State Scoping Actually Works (Source Code)**

```python
# From _session_util.py — this runs on every state write:
def extract_state_delta(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    deltas = {"app": {}, "user": {}, "session": {}}
    for key in state.keys():
        if key.startswith("app:"):
            deltas["app"][key.removeprefix("app:")] = state[key]
        elif key.startswith("user:"):
            deltas["user"][key.removeprefix("user:")] = state[key]
        elif not key.startswith("temp:"):
            deltas["session"][key] = state[key]
        # temp: keys are silently dropped — never stored
    return deltas
```

**The Four Scopes and Their Security Implications**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ APP STATE (prefix: "app:")                                              │
│ WHO SEES IT: Every user, every session, every agent in the application  │
│ PERSISTED: Yes — stored permanently in your session backend             │
│ DANGER: HIGHEST — anything here is globally visible                     │
│ USE FOR: Feature flags, model versions, maintenance mode, counters      │
│ NEVER FOR: User data, PII, credentials, tenant-specific config          │
│                                                                         │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ USER STATE (prefix: "user:")                                      │   │
│ │ WHO SEES IT: All sessions belonging to this user_id               │   │
│ │ PERSISTED: Yes                                                    │   │
│ │ DANGER: MEDIUM — leaks across conversations for same user         │   │
│ │ USE FOR: Preferences, profile refs, accumulated stats             │   │
│ │ NEVER FOR: Secrets, tokens, data that should stay in one chat     │   │
│ │                                                                    │   │
│ │ ┌──────────────────────────────────────────────────────────────┐   │   │
│ │ │ SESSION STATE (no prefix)                                    │   │   │
│ │ │ WHO SEES IT: Only this specific conversation                 │   │   │
│ │ │ PERSISTED: Yes                                               │   │   │
│ │ │ USE FOR: Cart, workflow step, conversation context            │   │   │
│ │ │ NEVER FOR: Raw credentials, credit cards, SSNs               │   │   │
│ │ │                                                              │   │   │
│ │ │ ┌────────────────────────────────────────────────────────┐   │   │   │
│ │ │ │ TEMP STATE (prefix: "temp:")                           │   │   │   │
│ │ │ │ WHO SEES IT: Only this single request (invocation)     │   │   │   │
│ │ │ │ PERSISTED: NO — in-memory only, gone after request     │   │   │   │
│ │ │ │ USE FOR: Auth tokens, API keys, scratch data           │   │   │   │
│ │ │ └────────────────────────────────────────────────────────┘   │   │   │
│ │ └──────────────────────────────────────────────────────────────┘   │   │
│ └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Decision Tree: Which Prefix to Use**

```
What kind of data are you storing?
│
├── Sensitive credential or token?
│   └── temp: (never persisted, gone after this request)
│
├── Per-conversation data (cart, form progress)?
│   └── No prefix (session scope)
│
├── Cross-conversation user data (preferences)?
│   └── user: (shared across this user's sessions)
│
├── Global app configuration (feature flags)?
│   └── app: (shared across ALL users)
│
└── Scratch/cache data for this request only?
    └── temp: (in-memory, not persisted)
```

---

## Examples

### Best Practice State Usage

```python
# TEMP: for secrets and transient data
tool_context.state["temp:oauth_token"] = access_token # Never persisted
tool_context.state["temp:api_response_cache"] = raw_json # Scratch data

# SESSION: for conversation context
tool_context.state["cart_items"] = ["sku_123", "sku_456"]
tool_context.state["workflow_step"] = 3

# USER: for cross-session preferences
tool_context.state["user:display_name"] = "Alice"
tool_context.state["user:preferred_language"] = "en"

# APP: for global configuration only
tool_context.state["app:maintenance_mode"] = False
tool_context.state["app:model_version"] = "2.5"
```

### Common Mistakes That Cause Data Leaks

```python
# CATASTROPHIC: User data in app: scope
tool_context.state["app:last_customer_email"] = "alice@example.com"
# → Every user in the app can now read Alice's email!

# DANGEROUS: Secrets persisted to database
tool_context.state["user:api_key"] = "sk-live-abc123..."
# → Stored in plaintext in every session backend

# WRONG: Forgetting that user: leaks across sessions
tool_context.state["user:last_topic"] = "HIV test results"
# → Visible in ALL of that user's sessions!

# CORRECT: Keep sensitive conversation data in session scope
tool_context.state["last_topic"] = "HIV test results" # Session-only
```

### Event History Leaks in Multi-Agent Systems

```python
# DANGEROUS: Manually creating events without proper branch
event = Event(
    author="internal_agent",
    content=types.Content(parts=[types.Part(text=sensitive_data)]),
    # No branch set — visible to ALL agents in the tree!
)

# CORRECT: Let ADK manage event creation through the normal flow
# Or always set the branch:
event = Event(
    author="internal_agent",
    content=types.Content(parts=[types.Part(text=sensitive_data)]),
    branch="root_agent.internal_agent",
    invocation_id=ctx.invocation_id,
)
```

### Sensitive Data in Event Content — What Gets Persisted

Everything in events is persisted:

```
What gets stored in session.events:
┌──────────────────────────────────────────────────────────┐
│ User messages (everything the user typed)                │
│ LLM responses (agent replies)                            │
│ Tool call arguments (including any PII passed in)        │
│ Tool responses (including any PII returned)              │
│ state_delta (state changes — temp: stripped, rest kept)   │
│ requested_auth_configs (OAuth/auth credentials!)         │
│ Error messages and stack traces                          │
└──────────────────────────────────────────────────────────┘
```

```python
# DANGEROUS: Tool that returns full database records with PII
def lookup_customer(customer_id: str) -> str:
    record = db.get_customer(customer_id)
    return str(record) # SSN, email, etc. stored in events forever!

# CORRECT: Return only what the agent needs
def lookup_customer(customer_id: str) -> str:
    record = db.get_customer(customer_id)
    return f"Customer: {record['name']}, Account status: {record['status']}"
```

### Callback and Plugin Security

```python
# DANGEROUS: Callback with closure over mutable shared state
collected_data = [] # Shared across ALL invocations!

async def my_after_agent(callback_context):
    collected_data.append(callback_context.state.get("result"))
    return None
# → User A's results leak into User B's processing

# CORRECT: Use session state for per-session data
async def my_after_agent(callback_context):
    results = callback_context.state.get("results", [])
    results.append(callback_context.state.get("result"))
    callback_context.state["results"] = results
    return None
```

---

## Gotchas

- **Runner has no built-in authorization.** Your application layer is the ONLY security boundary.
- **`list_sessions(user_id=None)` returns ALL users' sessions.** Never expose this in a user-facing API without forcing `user_id`.
- **`app:` state is a single shared row per application.** Never store user-specific data here.
- **`user:` state leaks across conversations.** Anything stored with the `user:` prefix is visible in ALL of that user's sessions.
- **Tool arguments are persisted.** Never accept raw credentials as tool arguments.
- **`requested_auth_configs` are persisted.** Ensure your database is encrypted at rest.
- **Deleting a session does NOT delete `user:` or `app:` state.** These live in separate storage tables.
- **SQLite has no row-level locking.** Concurrent writes from multiple processes can corrupt data.

*Continued in [19b-security-checklist.md](19b-security-checklist.md) — audit checklist, threat model, deployment hardening, and multi-tenant architecture patterns.*

---

## Related

- [19b-security-checklist.md](19b-security-checklist.md) — Security checklist and deployment hardening
- [08-sessions.md](08-sessions.md) — Session data model and service implementations
- [07-events.md](07-events.md) — Event structure and what gets persisted
- [03-runners.md](03-runners.md) — How Runner manages session lifecycle
- [20-best-practices.md](20-best-practices.md) — General ADK best practices
