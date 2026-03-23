# 19b — Security Checklist: Audit, Threat Model, Deployment Hardening

> **Official docs:** [Sessions](https://google.github.io/adk-docs/sessions/) | **Source:** [`sessions/`](https://github.com/google/adk-python/blob/main/src/google/adk/sessions/) | **Prereqs:** [19-session-security.md](19-session-security.md)

*This file continues from [19-session-security.md](19-session-security.md), which covers developer-facing security patterns, state scoping, and validation.*

---

## Session Service Backend Security

**InMemorySessionService — Development Only**

```python
# DANGEROUS: Using InMemorySessionService in production
runner = Runner(
    agent=agent,
    app_name="production_app",
    session_service=InMemorySessionService(), # No persistence, no encryption
)
# Problems:
# - Data lost on restart
# - No access control at the storage layer
# - No audit logging
# - All sessions in one Python process's memory
```

**DatabaseSessionService — Production Considerations**

```python
from google.adk.sessions import DatabaseSessionService

session_service = DatabaseSessionService(
    db_url="postgresql+asyncpg://user:pass@db-host/adk_sessions",
    # Connection string should come from secrets manager, not code!
)
```

**Concurrency safety (verified from source):** `DatabaseSessionService` uses two layers of protection:
1. **In-process `asyncio.Lock`** per session — keyed by `(app_name, user_id, session_id)`
2. **Database row-level locking** (`SELECT ... FOR UPDATE`) on Postgres, MySQL, and MariaDB

SQLite does **not** support row-level locking — use only for single-process deployments.

**Production database security checklist:**

```
┌────────────────────────────────────────────────────────────────┐
│ Database Security for Session Storage                         │
│                                                                │
│ Use encrypted connections (SSL/TLS) to the database            │
│ Store DB credentials in a secrets manager (not in code)        │
│ Enable encryption at rest for the database                     │
│ Restrict DB user permissions (only needed tables/operations)   │
│ Enable audit logging for session table access                  │
│ Set up row-level security if your DB supports it               │
│ Regular backups — and encrypt those backups too                 │
│ Network isolation (DB not accessible from public internet)     │
│ Implement session expiry/TTL to auto-delete old sessions       │
│ Monitor for unusual access patterns (bulk reads, etc.)         │
└────────────────────────────────────────────────────────────────┘
```

---

## Session Lifecycle — Creation, Access, and Deletion

**Implement Session Expiry**

ADK does not automatically delete old sessions. In production, stale sessions containing sensitive data sit in storage indefinitely:

```python
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

**User Data Deletion (GDPR / Right to Be Forgotten)**

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

## Multi-Tenant Architecture Patterns

**Pattern 1: One App Per Tenant (Strongest Isolation)**

```
Tenant A: app_name="app_tenant_a" → Separate DB / schema
Tenant B: app_name="app_tenant_b" → Separate DB / schema

Pros: Complete isolation, tenant-specific configuration
Cons: More infrastructure, harder to manage
```

**Pattern 2: Shared App, User-Level Isolation (Common)**

```
All tenants: app_name="my_app"
Tenant A users: user_id="tenant_a:user_1", "tenant_a:user_2"
Tenant B users: user_id="tenant_b:user_1", "tenant_b:user_2"

Pros: Simpler infrastructure
Cons: app: state is shared across ALL tenants!
```

```python
# If using shared-app multi-tenancy, namespace user_ids
def get_namespaced_user_id(tenant_id: str, user_id: str) -> str:
    return f"{tenant_id}:{user_id}"

# DANGEROUS: Without namespacing, "user_1" in Tenant A and Tenant B
# are the same user in ADK — they share user: scoped state!
```

**Pattern 3: Separate Session Services Per Tenant**

```python
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

## Incident Scenarios and Mitigations

**Scenario 1: User Sees Another User's Conversation**

```
Root cause: user_id extracted from unverified header instead of auth token.
Mitigation: Always derive user_id from server-side verified authentication.
Detection: Monitor for sessions accessed by multiple IP addresses.
```

**Scenario 2: PII Leaked via Tool Response**

```
Root cause: Tool returned full customer record including SSN and email.
Mitigation: Tools return only the fields the agent needs. Redact at the tool layer.
Detection: Regex scan on event content for PII patterns (SSN, email, credit card).
```

**Scenario 3: Tenant A Reads Tenant B's Feature Flags**

```
Root cause: Feature flags stored in app: state in a shared-app multi-tenant setup.
Mitigation: Use tenant-specific state keys or separate apps.
Detection: Audit app: state writes — flag any that contain tenant-specific data.
```

**Scenario 4: Stale Sessions Exposed in Data Breach**

```
Root cause: No session TTL — 2-year-old conversations still in the database.
Mitigation: Implement automated session cleanup with configurable retention period.
Detection: Periodic report on session age distribution.
```

**Scenario 5: Agent Logs Expose Conversation Content**

```
Root cause: before_model_callback logs full LLM requests for debugging.
Mitigation: Log only metadata (message count, model name, latency). Never log content.
Detection: Scan log output for conversation patterns.
```

---

## ADK's Built-In Safety Mechanisms (Source Code Verified)

**What ADK DOES Protect**

```
┌────────────────────────────────────────────────────────────────────────┐
│ Built-in safety (verified from source code)                           │
│                                                                        │
│ Composite key isolation: get_session requires (app_name, user_id,      │
│   session_id) match — wrong user_id returns None                       │
│                                                                        │
│ temp: state never persisted: _trim_temp_delta_state() strips temp:     │
│   keys from events before storage                                      │
│                                                                        │
│ Pydantic extra='forbid': Session and Event models reject unknown       │
│   fields, preventing injection via unexpected keys                     │
│                                                                        │
│ State delta separation: extract_state_delta() routes state to          │
│   separate storage tables (app/user/session)                           │
│                                                                        │
│ Row-level locking: DatabaseSessionService uses SELECT FOR UPDATE       │
│   on Postgres/MySQL to prevent concurrent write corruption             │
│                                                                        │
│ Deep copy on read: InMemorySessionService returns deepcopy of          │
│   sessions, preventing callers from mutating stored state directly     │
│                                                                        │
│ Branch isolation: Events carry a branch field; flows filter events     │
│   by branch so agents only see their own lineage                       │
└────────────────────────────────────────────────────────────────────────┘
```

**What ADK Does NOT Protect**

```
┌────────────────────────────────────────────────────────────────────────┐
│ NOT built-in — your responsibility                                     │
│                                                                        │
│ Authentication: Runner trusts user_id blindly — no verification        │
│ Authorization: list_sessions(user_id=None) returns ALL sessions        │
│ Encryption at rest: State and events are stored as-is in the DB        │
│ PII redaction: Tools can return any data; ADK doesn't filter it        │
│ Session expiry: No built-in TTL — old sessions live forever            │
│ Rate limiting: No protection against session enumeration attacks       │
│ Audit logging: No built-in logging of who accessed which session       │
│ User state cleanup: Deleting a session does NOT delete user:/app: rows │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Security Checklist

```
┌────────────────────────────────────────────────────────────────────┐
│ Session & Event Security Checklist                                │
│                                                                    │
│ Authentication & Authorization                                     │
│   user_id always comes from verified authentication (JWT, OAuth)   │
│   Never trust client-provided user_id or session_id without auth   │
│   Session IDs are UUIDs (not sequential or guessable)              │
│   API gateway validates authentication before reaching ADK         │
│                                                                    │
│ State Scoping                                                      │
│   PII is NEVER stored in app: scoped state                         │
│   Sensitive tokens use temp: scope (not persisted)                 │
│   State keys are reviewed for correct scope prefix                 │
│   Parallel agents use distinct state keys (no race conditions)     │
│                                                                    │
│ Event Content                                                      │
│   Tools return minimal data (no full DB records with PII)          │
│   Tool arguments don't include raw credentials or secrets          │
│   Error messages don't expose internal system details              │
│   Sensitive data is redacted before entering the event stream      │
│                                                                    │
│ Session Lifecycle                                                  │
│   Session expiry/cleanup is implemented                            │
│   User data deletion flow exists (GDPR compliance)                 │
│   InMemorySessionService is NOT used in production                 │
│   Database connections use TLS and credentials from secrets mgr    │
│                                                                    │
│ Multi-Tenancy                                                      │
│   Tenant isolation strategy is defined and documented              │
│   user_ids are namespaced per tenant (if shared app)               │
│   app: state does not contain tenant-specific data                 │
│                                                                    │
│ Logging & Monitoring                                               │
│   Logs do NOT contain conversation content or PII                  │
│   Callbacks don't capture data in shared mutable state             │
│   Monitoring alerts on unusual session access patterns             │
│   Audit trail exists for session creation and deletion             │
│                                                                    │
│ Code Review                                                        │
│   Every tool is reviewed for what data it returns to the LLM       │
│   State key scopes are reviewed in PRs                             │
│   No global/module-level mutable state shared across requests      │
└────────────────────────────────────────────────────────────────────┘
```

### State Prefix Quick Reference

```
State Prefix Quick Reference:
│
├── (none) — session scope
│      Safe to store: Cart, step, context
│      NEVER store: Passwords, credit cards, SSNs
│
├── user:
│      Safe to store: Preferences, refs
│      NEVER store: Secrets, medical data, PII
│
├── app:
│      Safe to store: Feature flags, config
│      NEVER store: ANY user data, ANY tenant data
│
└── temp:
       Safe to store: Tokens, cache, scratch
       NEVER store: Data needed after this request
```

---

## Related

- [19-session-security.md](19-session-security.md) — Developer-facing security guide, state scoping, validation
- [08-sessions.md](08-sessions.md) — Session data model and service implementations
- [07-events.md](07-events.md) — Event structure and what gets persisted
- [20-best-practices.md](20-best-practices.md) — General ADK best practices
