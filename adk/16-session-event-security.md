# Session & Event Security — Preventing Data Leaks and Privacy Incidents

**Audience:** ADK developers building multi-user or multi-tenant agent systems where session isolation and data privacy are critical.

**Prerequisites:** [06-sessions.md](06-sessions.md), [01-events.md](01-events.md), [13-best-practices.md](13-best-practices.md)

**Source:** [`sessions/state.py`](../adk-python/src/google/adk/sessions/state.py) · [`sessions/base_session_service.py`](../adk-python/src/google/adk/sessions/base_session_service.py) · [`sessions/in_memory_session_service.py`](../adk-python/src/google/adk/sessions/in_memory_session_service.py) · [`sessions/database_session_service.py`](../adk-python/src/google/adk/sessions/database_session_service.py) · [`sessions/_session_util.py`](../adk-python/src/google/adk/sessions/_session_util.py)

---

## Why This Matters

A single session leak can expose an entire conversation history — personal data, credentials, business logic, and tool outputs — to the wrong user. In multi-agent systems, the attack surface multiplies: every agent, tool, callback, and state key is a potential leak vector.

This guide covers the most common ways sessions and events leak across user boundaries, and how to prevent each one.

---

## 1. Session Isolation — The #1 Source of Privacy Incidents

### The Core Rule

**Every `get_session` and `create_session` call MUST include the correct `user_id`.** ADK uses the `(app_name, user_id, session_id)` triple as the session key. If you pass the wrong `user_id`, you either get someone else's session or create a session under the wrong owner.

```python
# ❌ DANGEROUS: Hardcoded or missing user_id
session = await session_service.get_session(
    app_name="my_app",
    user_id="default",          # Every user gets the SAME sessions!
    session_id=request.session_id,
)

# ❌ DANGEROUS: user_id from untrusted input without validation
session = await session_service.get_session(
    app_name="my_app",
    user_id=request.headers["X-User-Id"],  # Client can spoof this!
    session_id=request.session_id,
)

# ✅ CORRECT: user_id from authenticated identity (e.g., JWT, OAuth)
user_id = get_authenticated_user_id(request)  # Verified server-side
session = await session_service.get_session(
    app_name="my_app",
    user_id=user_id,
    session_id=request.session_id,
)
```

### What Happens When user_id Is Wrong

```
Scenario: User A's request arrives with user_id="user_b" (due to a bug)

┌─────────────────────────────────────────────────────────────┐
│  session_service.get_session(user_id="user_b", session_id=X)│
│                                                              │
│  Case 1: Session X belongs to user_b                         │
│  → Returns user_b's full session (all events, all state)     │
│  → User A now sees user_b's entire conversation history!     │
│                                                              │
│  Case 2: Session X doesn't exist for user_b                  │
│  → Returns None (no data leak, but broken UX)                │
│                                                              │
│  Case 3: auto_create_session=True                            │
│  → Creates a NEW session under user_b's account              │
│  → User A's messages now stored in user_b's namespace!       │
└─────────────────────────────────────────────────────────────┘
```

### Warning: list_sessions Can List ALL Users' Sessions

The `BaseSessionService.list_sessions()` accepts an **optional** `user_id`. If you call it without a `user_id`, it returns sessions for ALL users:

```python
# From base_session_service.py:
async def list_sessions(
    self, *, app_name: str, user_id: Optional[str] = None  # Optional!
) -> ListSessionsResponse:

# ❌ DANGEROUS: If your API endpoint exposes this without forcing user_id
sessions = await session_service.list_sessions(app_name="my_app")
# → Returns sessions for ALL users!

# ✅ CORRECT: Always scope list_sessions to the authenticated user
sessions = await session_service.list_sessions(
    app_name="my_app",
    user_id=authenticated_user_id,
)
```

**Never expose `list_sessions` without filtering by `user_id`** in any user-facing API.

### Runner Has No Built-In Authorization

This is critical to understand: **`Runner` performs zero authentication or authorization.** It blindly passes `user_id` to the session service. From `runners.py`:

```python
# Runner.run_async() trusts the caller completely:
async def run_async(
    self,
    *,
    user_id: str,         # No validation — Runner trusts this is correct
    session_id: str,
    new_message: Content,
    ...
) -> AsyncGenerator[Event, None]:
    session = await self._get_or_create_session(user_id, session_id)
    # → Calls session_service.get_session(app_name=self.app_name, user_id=user_id, ...)
    # → If auto_create_session=True, creates a new session under this user_id
```

**This means your application layer is the ONLY security boundary.** If a bug in your API handler passes the wrong `user_id` to `runner.run_async()`, ADK will happily serve the wrong user's session. There are no guardrails inside ADK itself.

### Defense: Validate user_id at the Gateway

```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Extract and verify user identity from JWT token."""
    payload = verify_jwt(token)  # Raises on invalid/expired tokens
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@app.post("/chat")
async def chat(
    message: str,
    session_id: str,
    user_id: str = Depends(get_current_user),  # Always from verified token
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

---

## 2. Session ID Guessability — Don't Let Users Enumerate Sessions

### The Problem

If session IDs are sequential or predictable, an attacker can guess other users' session IDs:

```python
# ❌ DANGEROUS: Sequential session IDs
session_counter = 0

async def create_user_session(user_id: str):
    global session_counter
    session_counter += 1
    return await session_service.create_session(
        app_name="my_app",
        user_id=user_id,
        session_id=str(session_counter),  # "1", "2", "3"... trivially guessable
    )

# ❌ DANGEROUS: User-provided session IDs without ownership check
@app.get("/session/{session_id}")
async def get_session(session_id: str):
    # Any user can request any session_id!
    return await session_service.get_session(
        app_name="my_app",
        user_id=request.user_id,
        session_id=session_id,
    )
```

### Defense: Use UUIDs and Always Check Ownership

```python
import uuid

# ✅ CORRECT: Random UUIDs — not guessable
session = await session_service.create_session(
    app_name="my_app",
    user_id=user_id,
    session_id=str(uuid.uuid4()),  # "a3f8b2c1-..."
)

# ✅ CORRECT: Let ADK generate the session ID (it uses UUIDs internally)
session = await session_service.create_session(
    app_name="my_app",
    user_id=user_id,
    # session_id omitted — ADK generates a UUID
)
```

ADK's `get_session` already requires matching `(app_name, user_id, session_id)`, so even if someone guesses a session ID, they can't access it without also matching the `user_id`. In `DatabaseSessionService`, this is enforced via a composite primary key lookup:

```python
# From database_session_service.py:
storage_session = await sql_session.get(
    schema.StorageSession, (app_name, user_id, session_id)  # Composite PK
)
```

In `InMemorySessionService`, it's enforced via nested dict lookup:

```python
# From in_memory_session_service.py:
# self.sessions is: dict[app_name, dict[user_id, dict[session_id, Session]]]
if user_id not in self.sessions[app_name]:
    return None
if session_id not in self.sessions[app_name][user_id]:
    return None
```

But relying on this alone is insufficient — always use unpredictable IDs as defense in depth.

---

## 3. State Prefix Boundaries — Choosing the Right Scope

ADK state scoping is the primary mechanism for controlling data visibility between users. Picking the wrong prefix is one of the most common causes of cross-user data leakage. Understand these boundaries deeply before writing any state.

### How State Scoping Actually Works (Source Code)

Understanding the implementation is critical for reasoning about security. ADK does **not** store all state in one flat dict — it splits state into three separate storage locations based on prefix:

```python
# From _session_util.py — this runs on every state write:
def extract_state_delta(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    deltas = {"app": {}, "user": {}, "session": {}}
    for key in state.keys():
        if key.startswith("app:"):
            deltas["app"][key.removeprefix("app:")] = state[key]    # → StorageAppState table
        elif key.startswith("user:"):
            deltas["user"][key.removeprefix("user:")] = state[key]  # → StorageUserState table
        elif not key.startswith("temp:"):
            deltas["session"][key] = state[key]                      # → StorageSession table
        # temp: keys are silently dropped — never stored
    return deltas
```

This means:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Storage Architecture (DatabaseSessionService)                            │
│                                                                           │
│  StorageAppState table:    One row per app_name                           │
│  ├── Primary key: (app_name)                                              │
│  └── state: {"feature_flags": {...}, "model_version": "2.5"}              │
│      ↑ Writes from ANY user update this SAME row                          │
│                                                                           │
│  StorageUserState table:   One row per (app_name, user_id)                │
│  ├── Primary key: (app_name, user_id)                                     │
│  └── state: {"preferences": {...}, "total_orders": 42}                    │
│      ↑ Writes from ANY session for this user update this SAME row         │
│                                                                           │
│  StorageSession table:     One row per (app_name, user_id, session_id)    │
│  ├── Primary key: (app_name, user_id, session_id)                         │
│  └── state: {"cart": [...], "step": 3}                                    │
│      ↑ Only this session reads/writes here                                │
│                                                                           │
│  In-memory only (temp:):   Never hits the database                        │
│  └── Lives in session.state dict during the request, then vanishes        │
└──────────────────────────────────────────────────────────────────────────┘
```

On read, `_merge_state()` re-adds the prefixes and combines all three sources:

```python
# From database_session_service.py:
def _merge_state(app_state, user_state, session_state) -> dict[str, Any]:
    merged_state = copy.deepcopy(session_state)
    for key in app_state:
        merged_state["app:" + key] = app_state[key]   # Re-adds prefix
    for key in user_state:
        merged_state["user:" + key] = user_state[key]  # Re-adds prefix
    return merged_state
```

**Security implication:** The `app:` row is a single shared row per application. A write to `app:maintenance_mode` from User A's session modifies the exact same database row that User B reads from. There is no per-user isolation at the storage level for `app:` state.

### The Four Scopes and Their Security Implications

```
┌──────────────────────────────────────────────────────────────────────────┐
│  APP STATE (prefix: "app:")                                               │
│  WHO SEES IT: Every user, every session, every agent in the application   │
│  PERSISTED:   Yes — stored permanently in your session backend            │
│  DANGER:      HIGHEST — anything here is globally visible                 │
│  USE FOR:     Feature flags, model versions, maintenance mode, counters   │
│  NEVER FOR:   User data, PII, credentials, tenant-specific config        │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  USER STATE (prefix: "user:")                                       │  │
│  │  WHO SEES IT: All sessions belonging to this user_id                │  │
│  │  PERSISTED:   Yes                                                   │  │
│  │  DANGER:      MEDIUM — leaks across conversations for same user     │  │
│  │  USE FOR:     Preferences, profile refs, accumulated stats          │  │
│  │  NEVER FOR:   Secrets, tokens, data that should stay in one chat    │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  SESSION STATE (no prefix)                                    │  │  │
│  │  │  WHO SEES IT: Only this specific conversation                 │  │  │
│  │  │  PERSISTED:   Yes                                             │  │  │
│  │  │  DANGER:      LOW — but still in the database                 │  │  │
│  │  │  USE FOR:     Cart, workflow step, conversation context        │  │  │
│  │  │  NEVER FOR:   Raw credentials, credit cards, SSNs             │  │  │
│  │  │                                                               │  │  │
│  │  │  ┌────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  TEMP STATE (prefix: "temp:")                          │  │  │  │
│  │  │  │  WHO SEES IT: Only this single request (invocation)    │  │  │  │
│  │  │  │  PERSISTED:   NO — in-memory only, gone after request  │  │  │  │
│  │  │  │  DANGER:      LOWEST — never hits storage              │  │  │  │
│  │  │  │  USE FOR:     Auth tokens, API keys, scratch data      │  │  │  │
│  │  │  └────────────────────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Visibility Matrix

```
┌──────────────────────┬───────────┬───────────┬──────────┬───────────┐
│  Scope                │ Same      │ Different │ Different│ Persisted │
│                       │ session   │ session   │ user     │ to disk   │
│                       │ same user │ same user │          │           │
├──────────────────────┼───────────┼───────────┼──────────┼───────────┤
│ Session (no prefix)   │ ✅ Yes    │ ❌ No     │ ❌ No    │ ✅ Yes    │
│ user:                 │ ✅ Yes    │ ✅ Yes    │ ❌ No    │ ✅ Yes    │
│ app:                  │ ✅ Yes    │ ✅ Yes    │ ✅ Yes   │ ✅ Yes    │
│ temp:                 │ ✅ Yes*   │ ❌ No     │ ❌ No    │ ❌ No     │
└──────────────────────┴───────────┴───────────┴──────────┴───────────┘
* temp: visible within the same request/invocation only, not across turns
```

### Decision Tree: Which Prefix to Use

```
What kind of data are you storing?
│
├── Sensitive credential or token (API key, OAuth token, JWT)?
│   └── temp:   (never persisted, gone after this request)
│       If the token is needed across requests → store externally
│       (credential service, vault), NOT in state
│
├── Per-conversation data (cart, form progress, current step)?
│   └── No prefix (session scope)
│       Only this conversation sees it
│
├── Cross-conversation user data (preferences, profile, history)?
│   └── user:   (shared across this user's sessions)
│       ⚠️  Do NOT store PII directly — use references
│       ⚠️  Everything here is visible in ALL of this user's chats
│
├── Global app configuration (feature flags, maintenance mode)?
│   └── app:    (shared across ALL users)
│       ⚠️  NEVER store user-specific data here
│       ⚠️  NEVER store tenant-specific data here (in multi-tenant setups)
│
└── Scratch/cache data for this request only?
    └── temp:   (in-memory, not persisted)
```

### Best Practice Examples

```python
# ─── TEMP: for secrets and transient data ─────────────────
# Auth tokens, API keys, intermediate computation
tool_context.state["temp:oauth_token"] = access_token     # ✅ Never persisted
tool_context.state["temp:api_response_cache"] = raw_json   # ✅ Scratch data
tool_context.state["temp:retry_count"] = 0                 # ✅ Request-local counter

# ⚠️  WARNING: temp: state vanishes after the request ends!
# Next request: tool_context.state.get("temp:oauth_token") → None

# ─── SESSION: for conversation context ────────────────────
# Data that belongs to THIS chat only
tool_context.state["cart_items"] = ["sku_123", "sku_456"]  # ✅ This conversation's cart
tool_context.state["workflow_step"] = 3                     # ✅ Where we are in the flow
tool_context.state["last_search_query"] = "flights Tokyo"   # ✅ Conversation context

# ─── USER: for cross-session preferences ──────────────────
# Data that follows the user across conversations
tool_context.state["user:display_name"] = "Alice"           # ✅ Low-sensitivity profile data
tool_context.state["user:preferred_language"] = "en"        # ✅ Preference
tool_context.state["user:total_sessions"] = 42              # ✅ Aggregate stat
tool_context.state["user:profile_id"] = "prof_abc123"       # ✅ Reference to external system

# ─── APP: for global configuration only ───────────────────
# Data shared across ALL users — use sparingly
tool_context.state["app:maintenance_mode"] = False          # ✅ Global flag
tool_context.state["app:model_version"] = "2.5"            # ✅ App-wide config
tool_context.state["app:announcement"] = "System upgrade tonight"  # ✅ Broadcast
```

### Common Mistakes That Cause Data Leaks

```python
# ❌ CATASTROPHIC: User data in app: scope
tool_context.state["app:last_customer_email"] = "alice@example.com"
# → Every user in the app can now read Alice's email!

tool_context.state["app:preferences"] = {"theme": "dark"}
# → User A sets this → User B reads it → Last-write-wins chaos

# ❌ DANGEROUS: Secrets persisted to database
tool_context.state["user:api_key"] = "sk-live-abc123..."
# → Stored in plaintext in every session backend, survives DB backups

tool_context.state["credit_card"] = "4111-1111-1111-1111"
# → Persisted to session storage, visible in DB admin tools

# ❌ WRONG: Forgetting that user: leaks across sessions
def tool_a(tool_context: ToolContext) -> str:
    """In Session 1: user asks about medical condition."""
    tool_context.state["user:last_topic"] = "HIV test results"
    return "Here are your results..."

# Session 2 (same user, different conversation — maybe with a colleague watching):
def tool_b(tool_context: ToolContext) -> str:
    """Agent reads user:last_topic and mentions it in a new context."""
    topic = tool_context.state.get("user:last_topic")
    # → "I see you were recently asking about HIV test results..."
    # → Private medical information leaked into a different conversation!

# ✅ CORRECT: Keep sensitive conversation data in session scope
def tool_a(tool_context: ToolContext) -> str:
    tool_context.state["last_topic"] = "HIV test results"  # Session-only, no prefix
    return "Here are your results..."
```

### The app: State Trap in Multi-Tenant Systems

`app:` state is shared across every user in the application. In multi-tenant setups, this means across ALL tenants:

```python
# ❌ CATASTROPHIC: Tenant-specific config in app: state
tool_context.state["app:billing_plan"] = "enterprise"
# → Tenant A sets this, Tenant B reads it

# ❌ CATASTROPHIC: Using app: for per-user data
def save_user_preferences(prefs: dict, tool_context: ToolContext) -> str:
    tool_context.state["app:preferences"] = prefs  # EVERY user sees this!
    return "Saved"
# → User A sets preferences → User B's next request reads them
# → Last write wins — preferences keep flip-flopping

# ✅ CORRECT: user: scope for per-user data
def save_user_preferences(prefs: dict, tool_context: ToolContext) -> str:
    tool_context.state["user:preferences"] = prefs
    return "Saved"

# ✅ CORRECT: If you must store tenant config globally, namespace it
tool_context.state["app:tenant_a:billing_plan"] = "enterprise"
# → Still visible to all users, but at least clearly namespaced
# → Better approach: use separate app_name per tenant (see Section 9)
```

### How temp: State Works Under the Hood

`temp:` is the only scope that is **never persisted** to any storage backend. Here's exactly what happens in the source code:

```python
# From base_session_service.py — called for EVERY event:

async def append_event(self, session: Session, event: Event) -> Event:
    if event.partial:
        return event
    # Step 1: Apply temp state to in-memory session (so other agents can read it)
    self._apply_temp_state(session, event)
    # Step 2: Strip temp keys from the event delta (so they're never persisted)
    event = self._trim_temp_delta_state(event)
    # Step 3: Apply remaining state (session/user/app) normally
    self._update_session_state(session, event)
    session.events.append(event)
    return event

def _apply_temp_state(self, session, event):
    """Writes temp: keys to in-memory session.state only."""
    for key, value in event.actions.state_delta.items():
        if key.startswith("temp:"):
            session.state[key] = value  # In-memory only!

def _trim_temp_delta_state(self, event):
    """Removes temp: keys from event before persistence."""
    event.actions.state_delta = {
        key: value for key, value in event.actions.state_delta.items()
        if not key.startswith("temp:")  # Stripped!
    }
    return event
```

**This means:**
- `temp:` values exist in `session.state` for the duration of the current invocation
- They're available to subsequent agents within the same `run_async()` call (e.g., in `SequentialAgent`)
- They are **stripped from the event** before the event is saved to storage
- On the next `run_async()` call, `get_session()` loads from storage — `temp:` keys are gone
- This makes `temp:` the **safest scope for secrets** — they cannot leak through DB backups, event logs, or session dumps

### State Prefix Quick Reference

```
┌────────────┬──────────────────────┬──────────────────────────────────┐
│  Prefix     │  Safe to Store        │  NEVER Store                      │
├────────────┼──────────────────────┼──────────────────────────────────┤
│  (none)     │  Cart, step, context  │  Passwords, credit cards, SSNs    │
│  user:      │  Preferences, refs    │  Secrets, medical data, PII       │
│  app:       │  Feature flags, config│  ANY user data, ANY tenant data   │
│  temp:      │  Tokens, cache, scratch│ Data needed after this request   │
└────────────┴──────────────────────┴──────────────────────────────────┘
```

---

## 4. Event History Leaks in Multi-Agent Systems

### The Branch Isolation Problem

In multi-agent trees, events carry a `branch` field that controls visibility. If you manually construct events or bypass the normal flow, you can accidentally make events visible to wrong agents — and their users.

```python
# ❌ DANGEROUS: Manually creating events without proper branch
event = Event(
    author="internal_agent",
    content=types.Content(parts=[types.Part(text=sensitive_data)]),
    # No branch set — visible to ALL agents in the tree!
)
await session_service.append_event(session, event)

# ✅ CORRECT: Let ADK manage event creation through the normal flow
# Events created by agents through run_async() automatically get the correct branch.
# If you must create events manually, always set the branch:
event = Event(
    author="internal_agent",
    content=types.Content(parts=[types.Part(text=sensitive_data)]),
    branch="root_agent.internal_agent",  # Only visible to this agent's lineage
    invocation_id=ctx.invocation_id,
)
```

### Cross-User Event Visibility via Shared Sessions

```python
# ❌ DANGEROUS: Two users sharing a session
# If two users connect to the same session_id, they see each other's messages
session = await session_service.get_session(
    app_name="my_app",
    user_id="shared_account",  # Multiple humans behind one "user"
    session_id="common_room",
)
# → User A's medical questions visible to User B

# ✅ CORRECT: One session per user, period
# If you need shared context, use app: state for non-sensitive shared data
# and keep conversations isolated per user
```

---

## 5. Sensitive Data in Event Content — What Gets Persisted

### Everything in Events Is Persisted

Every event yielded by an agent is passed to `session_service.append_event()` and stored permanently. This includes:

```
What gets stored in session.events (verified from event_actions.py):
┌──────────────────────────────────────────────────────────┐
│  ✓ User messages (everything the user typed)              │
│  ✓ LLM responses (agent replies)                          │
│  ✓ Tool call arguments (including any PII passed in)      │
│  ✓ Tool responses (including any PII returned)            │
│  ✓ state_delta (state changes — temp: stripped, rest kept)│
│  ✓ requested_auth_configs (OAuth/auth credentials!)       │
│  ✓ Error messages and stack traces                        │
│  ✓ File/blob content (if not using artifact service)      │
└──────────────────────────────────────────────────────────┘
```

**The `requested_auth_configs` field is especially dangerous.** When a tool requests OAuth credentials, the `EventActions` stores `dict[str, AuthConfig]` keyed by function call ID. These auth configs are **persisted to your session storage backend** as part of the event. If your database isn't encrypted at rest, auth credentials sit in plaintext.

### Common Leak Vectors

```python
# ❌ DANGEROUS: Tool that returns full database records with PII
def lookup_customer(customer_id: str) -> str:
    """Look up customer details."""
    record = db.get_customer(customer_id)
    return str(record)
    # Returns: {"name": "Alice", "ssn": "123-45-6789", "email": "..."}
    # ALL of this is now stored in the session events forever!

# ✅ CORRECT: Return only what the agent needs
def lookup_customer(customer_id: str) -> str:
    """Look up customer details."""
    record = db.get_customer(customer_id)
    return f"Customer: {record['name']}, Account status: {record['status']}"
    # SSN, email, and other PII never enter the event stream

# ✅ CORRECT: Redact sensitive fields
def lookup_customer(customer_id: str) -> str:
    """Look up customer details."""
    record = db.get_customer(customer_id)
    safe_record = {
        "name": record["name"],
        "status": record["status"],
        "account_type": record["account_type"],
        # Deliberately omit: ssn, email, phone, address
    }
    return str(safe_record)
```

### Tool Arguments Are Also Stored

```python
# ❌ DANGEROUS: Tool that accepts sensitive data as arguments
def process_payment(card_number: str, amount: float) -> str:
    """Process a payment."""
    # card_number is stored in the FunctionCall event!
    charge(card_number, amount)
    return "Payment processed"

# ✅ CORRECT: Use references, not raw credentials
def process_payment(payment_method_id: str, amount: float) -> str:
    """Process a payment using a saved payment method."""
    # Only a reference is stored in the event
    charge_saved_method(payment_method_id, amount)
    return "Payment processed"
```

---

## 6. Session Service Backend Security

### InMemorySessionService — Development Only

```python
# ❌ DANGEROUS: Using InMemorySessionService in production
runner = Runner(
    agent=agent,
    app_name="production_app",
    session_service=InMemorySessionService(),  # No persistence, no encryption
)
# Problems:
# - Data lost on restart (not a security issue, but a reliability one)
# - No access control at the storage layer
# - No audit logging
# - All sessions in one Python process's memory
```

### DatabaseSessionService — Production Considerations

```python
# ✅ Production setup with security considerations
from google.adk.sessions import DatabaseSessionService

session_service = DatabaseSessionService(
    db_url="postgresql+asyncpg://user:pass@db-host/adk_sessions",
    # Connection string should come from secrets manager, not code!
)
```

**Concurrency safety (verified from source):** `DatabaseSessionService` uses two layers of protection for concurrent `append_event` calls:
1. **In-process `asyncio.Lock`** per session — keyed by `(app_name, user_id, session_id)` — serializes writes within the same Python process
2. **Database row-level locking** (`SELECT ... FOR UPDATE`) on Postgres, MySQL, and MariaDB — serializes writes across processes

SQLite does **not** support row-level locking, so concurrent writes from multiple processes can corrupt data. Use SQLite only for single-process deployments.

**Production database security checklist:**

```
┌────────────────────────────────────────────────────────────────┐
│  Database Security for Session Storage                          │
│                                                                 │
│  □ Use encrypted connections (SSL/TLS) to the database          │
│  □ Store DB credentials in a secrets manager (not in code)      │
│  □ Enable encryption at rest for the database                   │
│  □ Restrict DB user permissions (only needed tables/operations) │
│  □ Enable audit logging for session table access                │
│  □ Set up row-level security if your DB supports it             │
│  □ Regular backups — and encrypt those backups too               │
│  □ Network isolation (DB not accessible from public internet)   │
│  □ Implement session expiry/TTL to auto-delete old sessions     │
│  □ Monitor for unusual access patterns (bulk reads, etc.)       │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. Session Lifecycle — Creation, Access, and Deletion

### Don't Reuse Sessions Across Users

```python
# ❌ DANGEROUS: Reassigning a session to a different user
session = await session_service.get_session(
    app_name="my_app",
    user_id="user_a",
    session_id="session_123",
)
# ... later, a different user tries to "take over" the session
# This won't work with ADK (user_id is part of the key), but
# if you build a lookup layer on top, watch out for this pattern.
```

### Implement Session Expiry

ADK does not automatically delete old sessions. In production, stale sessions containing sensitive data sit in storage indefinitely unless you clean them up:

```python
# ✅ Implement a cleanup job
import asyncio
from datetime import datetime, timedelta

async def cleanup_expired_sessions(
    session_service: DatabaseSessionService,
    app_name: str,
    max_age_days: int = 30,
):
    """Delete sessions older than max_age_days."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    cutoff_timestamp = cutoff.timestamp()

    # List all users and their sessions
    # (Implementation depends on your user registry)
    for user_id in await get_all_user_ids():
        sessions = await session_service.list_sessions(
            app_name=app_name,
            user_id=user_id,
        )
        for session_info in sessions.sessions:
            if session_info.last_update_time < cutoff_timestamp:
                await session_service.delete_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_info.id,
                )
```

### User Data Deletion (GDPR / Right to Be Forgotten)

When a user requests data deletion, you must delete all their sessions:

```python
async def delete_all_user_data(
    session_service: BaseSessionService,
    app_name: str,
    user_id: str,
):
    """Delete all sessions and data for a user (GDPR compliance)."""
    sessions = await session_service.list_sessions(
        app_name=app_name,
        user_id=user_id,
    )
    for session_info in sessions.sessions:
        await session_service.delete_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_info.id,
        )
    # Also clean up: artifacts, memory service entries, credential store
```

---

## 8. Callback and Plugin Security

### Callbacks Can Leak Data Across Sessions

```python
# ❌ DANGEROUS: Callback with closure over mutable shared state
collected_data = []  # Shared across ALL invocations!

async def my_after_agent(callback_context):
    # Every user's agent output is appended to the same list
    collected_data.append(callback_context.state.get("result"))
    return None

# → User A's results leak into User B's processing
# → Memory grows unbounded

# ✅ CORRECT: Use session state for per-session data
async def my_after_agent(callback_context):
    results = callback_context.state.get("results", [])
    results.append(callback_context.state.get("result"))
    callback_context.state["results"] = results  # Session-scoped
    return None
```

### before_model_callback — Don't Log Full Requests

```python
# ❌ DANGEROUS: Logging the full LLM request (contains conversation history)
async def my_before_model(callback_context, llm_request):
    logger.info(f"LLM request: {llm_request}")  # Logs all user messages!
    return None

# ✅ CORRECT: Log only metadata, not content
async def my_before_model(callback_context, llm_request):
    logger.info(
        f"LLM call: model={callback_context.agent_name}, "
        f"messages={len(llm_request.contents)}"
    )
    return None
```

---

## 9. Multi-Tenant Architecture Patterns

### Pattern 1: One App Per Tenant (Strongest Isolation)

```
Tenant A: app_name="app_tenant_a"  →  Separate DB / schema
Tenant B: app_name="app_tenant_b"  →  Separate DB / schema

Pros: Complete isolation, tenant-specific configuration
Cons: More infrastructure, harder to manage
```

### Pattern 2: Shared App, User-Level Isolation (Common)

```
All tenants: app_name="my_app"
Tenant A users: user_id="tenant_a:user_1", "tenant_a:user_2"
Tenant B users: user_id="tenant_b:user_1", "tenant_b:user_2"

Pros: Simpler infrastructure
Cons: app: state is shared across ALL tenants!
```

```python
# ✅ If using shared-app multi-tenancy, namespace user_ids
def get_namespaced_user_id(tenant_id: str, user_id: str) -> str:
    """Prefix user_id with tenant to prevent cross-tenant access."""
    return f"{tenant_id}:{user_id}"

# ❌ DANGEROUS: Without namespacing, "user_1" in Tenant A and Tenant B
# are the same user in ADK — they share user: scoped state!
```

### Pattern 3: Separate Session Services Per Tenant

```python
# ✅ Strongest isolation with shared infrastructure
tenant_session_services: dict[str, BaseSessionService] = {
    "tenant_a": DatabaseSessionService(db_url=TENANT_A_DB_URL),
    "tenant_b": DatabaseSessionService(db_url=TENANT_B_DB_URL),
}

def get_session_service(tenant_id: str) -> BaseSessionService:
    service = tenant_session_services.get(tenant_id)
    if not service:
        raise ValueError(f"Unknown tenant: {tenant_id}")
    return service
```

---

## 10. Security Checklist

```
┌────────────────────────────────────────────────────────────────────┐
│          Session & Event Security Checklist                          │
│                                                                     │
│  Authentication & Authorization                                     │
│  □ user_id always comes from verified authentication (JWT, OAuth)   │
│  □ Never trust client-provided user_id or session_id without auth   │
│  □ Session IDs are UUIDs (not sequential or guessable)              │
│  □ API gateway validates authentication before reaching ADK         │
│                                                                     │
│  State Scoping                                                      │
│  □ PII is NEVER stored in app: scoped state                         │
│  □ Sensitive tokens use temp: scope (not persisted)                 │
│  □ State keys are reviewed for correct scope prefix                 │
│  □ Parallel agents use distinct state keys (no race conditions)     │
│                                                                     │
│  Event Content                                                      │
│  □ Tools return minimal data (no full DB records with PII)          │
│  □ Tool arguments don't include raw credentials or secrets          │
│  □ Error messages don't expose internal system details              │
│  □ Sensitive data is redacted before entering the event stream      │
│                                                                     │
│  Session Lifecycle                                                  │
│  □ Session expiry/cleanup is implemented                            │
│  □ User data deletion flow exists (GDPR compliance)                 │
│  □ InMemorySessionService is NOT used in production                 │
│  □ Database connections use TLS and credentials from secrets mgr    │
│                                                                     │
│  Multi-Tenancy                                                      │
│  □ Tenant isolation strategy is defined and documented              │
│  □ user_ids are namespaced per tenant (if shared app)               │
│  □ app: state does not contain tenant-specific data                 │
│                                                                     │
│  Logging & Monitoring                                               │
│  □ Logs do NOT contain conversation content or PII                  │
│  □ Callbacks don't capture data in shared mutable state             │
│  □ Monitoring alerts on unusual session access patterns             │
│  □ Audit trail exists for session creation and deletion             │
│                                                                     │
│  Code Review                                                        │
│  □ Every tool is reviewed for what data it returns to the LLM       │
│  □ State key scopes are reviewed in PRs                             │
│  □ No global/module-level mutable state shared across requests      │
└────────────────────────────────────────────────────────────────────┘
```

---

## 11. Incident Scenarios and Mitigations

### Scenario 1: User Sees Another User's Conversation

```
Root cause: user_id extracted from unverified header instead of auth token.
Mitigation: Always derive user_id from server-side verified authentication.
Detection:  Monitor for sessions accessed by multiple IP addresses.
```

### Scenario 2: PII Leaked via Tool Response

```
Root cause: Tool returned full customer record including SSN and email.
Mitigation: Tools return only the fields the agent needs. Redact at the tool layer.
Detection:  Regex scan on event content for PII patterns (SSN, email, credit card).
```

### Scenario 3: Tenant A Reads Tenant B's Feature Flags

```
Root cause: Feature flags stored in app: state in a shared-app multi-tenant setup.
Mitigation: Use tenant-specific state keys ("app:tenant_a:flags") or separate apps.
Detection:  Audit app: state writes — flag any that contain tenant-specific data.
```

### Scenario 4: Stale Sessions Exposed in Data Breach

```
Root cause: No session TTL — 2-year-old conversations still in the database.
Mitigation: Implement automated session cleanup with configurable retention period.
Detection:  Periodic report on session age distribution.
```

### Scenario 5: Agent Logs Expose Conversation Content

```
Root cause: before_model_callback logs full LLM requests for debugging.
Mitigation: Log only metadata (message count, model name, latency). Never log content.
Detection:  Scan log output for conversation patterns. Use structured logging with allow-lists.
```

---

## 12. ADK's Built-In Safety Mechanisms (Source Code Verified)

ADK includes several safety mechanisms. Understanding what ADK does and doesn't protect helps you know where to add your own defenses.

### What ADK DOES Protect

```
┌────────────────────────────────────────────────────────────────────────┐
│  Built-in safety (verified from source code)                            │
│                                                                         │
│  ✓ Composite key isolation: get_session requires (app_name, user_id,    │
│    session_id) match — wrong user_id returns None, not another user's   │
│    data  [database_session_service.py, in_memory_session_service.py]    │
│                                                                         │
│  ✓ temp: state never persisted: _trim_temp_delta_state() strips temp:   │
│    keys from events before storage  [base_session_service.py:131-146]   │
│                                                                         │
│  ✓ Pydantic extra='forbid': Session and Event models reject unknown     │
│    fields, preventing injection via unexpected keys  [session.py:31]    │
│                                                                         │
│  ✓ State delta separation: extract_state_delta() routes state to        │
│    separate storage tables (app/user/session)  [_session_util.py:37-50] │
│                                                                         │
│  ✓ Row-level locking: DatabaseSessionService uses SELECT FOR UPDATE     │
│    on Postgres/MySQL to prevent concurrent write corruption              │
│    [database_session_service.py:560-561]                                │
│                                                                         │
│  ✓ Staleness detection: append_event checks if the session was updated  │
│    externally and reloads from storage if needed                        │
│    [database_session_service.py:594-614]                                │
│                                                                         │
│  ✓ Deep copy on read: InMemorySessionService returns deepcopy of        │
│    sessions, preventing callers from mutating stored state directly     │
│    [in_memory_session_service.py:178]                                   │
│                                                                         │
│  ✓ Branch isolation: Events carry a branch field encoding the agent     │
│    hierarchy; flows filter events by branch so agents only see their    │
│    own lineage  [event.py:60-68]                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### What ADK Does NOT Protect

```
┌────────────────────────────────────────────────────────────────────────┐
│  NOT built-in — your responsibility                                     │
│                                                                         │
│  ✗ Authentication: Runner trusts user_id blindly — no verification      │
│    [runners.py: run_async accepts user_id as a plain string]            │
│                                                                         │
│  ✗ Authorization: list_sessions(user_id=None) returns ALL sessions      │
│    [base_session_service.py:86 — user_id is Optional]                   │
│                                                                         │
│  ✗ Encryption at rest: State and events are stored as-is in the DB      │
│    (including requested_auth_configs with OAuth credentials)             │
│                                                                         │
│  ✗ PII redaction: Tools can return any data; ADK doesn't filter it      │
│                                                                         │
│  ✗ Session expiry: No built-in TTL — old sessions live forever          │
│                                                                         │
│  ✗ Rate limiting: No protection against session enumeration attacks      │
│                                                                         │
│  ✗ Audit logging: No built-in logging of who accessed which session     │
│                                                                         │
│  ✗ User state cleanup: Deleting a session does NOT delete the user:     │
│    or app: state rows — those persist independently                     │
│    [database_session_service.py: delete_session only deletes session]   │
└────────────────────────────────────────────────────────────────────────┘
```

The last point deserves emphasis: **when you delete a session, `user:` state and `app:` state are NOT deleted.** These live in separate storage tables (`user_states` and `app_states`). For full GDPR compliance, you must also clean up these tables directly.

---

## Cross-references

- [06-sessions.md](06-sessions.md) — Session data model and service implementations
- [01-events.md](01-events.md) — Event structure and what gets persisted
- [03-runners.md](03-runners.md) — How Runner manages session lifecycle
- [13-best-practices.md](13-best-practices.md) — General ADK best practices
- [08-apps.md](08-apps.md) — App configuration and plugins
- [07-tools.md](07-tools.md) — Tool system (relevant to data returned by tools)
