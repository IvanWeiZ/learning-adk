# Authentication Deep Dive

> **Official docs:** [Authentication](https://google.github.io/adk-docs/tools/authentication/) | **Source:** [`auth_credential.py`](https://github.com/google/adk-python/blob/main/src/google/adk/auth/auth_credential.py) · [`auth_schemes.py`](https://github.com/google/adk-python/blob/main/src/google/adk/auth/auth_schemes.py) · [`auth_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/auth/auth_tool.py) · [`auth_handler.py`](https://github.com/google/adk-python/blob/main/src/google/adk/auth/auth_handler.py) | **Prereqs:** [09-tools.md](09-tools.md)

---

## At a Glance

ADK's auth module lets tools declare credential requirements (API keys, OAuth tokens, service accounts) via `AuthConfig`. ADK handles the round-trip: requesting credentials, exchanging tokens, and storing results in session state.

Supports five credential types and OpenAPI 3.0 security schemes.

---

## How It Works

Three phases:

1. **Tool declares its auth requirement** by calling `tool_context.request_credential(auth_config)` when it detects no valid credential is available.
2. **ADK returns the auth request to the client** as part of the event stream. For OAuth, this includes a generated `auth_uri` the user must visit.
3. **Client completes auth and returns the response.** ADK stores the exchanged credential in session state, and the tool is re-invoked with the credential now available via `tool_context.get_auth_response(auth_config)`.

```
Tool runs
│
├─ Has credential? ──→ yes ──→ proceed with API call
│
└─ No credential
 ├─ tool_context.request_credential(auth_config)
 │ └─ ADK generates auth_uri (OAuth) or passes config to client
 │
 ├─ Client presents auth flow to user
 │ └─ User completes OAuth / provides API key
 │
 ├─ Client sends auth response back
 │ └─ ADK exchanges code for tokens (OAuth/OIDC)
 │ └─ Stores credential in session state
 │
 └─ Tool re-invoked
 └─ tool_context.get_auth_response(auth_config) returns credential
```

---

## Key Classes

### AuthCredentialTypes

An enum defining the five supported credential types:

```python
class AuthCredentialTypes(str, Enum):
    API_KEY = "apiKey"
    HTTP = "http"
    OAUTH2 = "oauth2"
    OPEN_ID_CONNECT = "openIdConnect"
    SERVICE_ACCOUNT = "serviceAccount"
```

### AuthCredential

The core credential container. Which fields are populated depends on `auth_type`:

```python
class AuthCredential(BaseModel):
    auth_type: AuthCredentialTypes
    resource_ref: str | None = None # future: resource reference
    api_key: str | None = None # for API_KEY type
    http: HttpAuth | None = None # for HTTP type
    service_account: ServiceAccount | None = None # for SERVICE_ACCOUNT type
    oauth2: OAuth2Auth | None = None # for OAUTH2 and OPEN_ID_CONNECT types
```

### HttpAuth and HttpCredentials

For HTTP authentication schemes (Basic, Bearer, etc.):

```python
class HttpCredentials(BaseModel):
    username: str | None = None
    password: str | None = None
    token: str | None = None

class HttpAuth(BaseModel):
    scheme: str # e.g., "basic", "bearer"
    credentials: HttpCredentials
    additional_headers: dict[str, str] | None = None
```

### OAuth2Auth

Holds all the fields needed for an OAuth2 flow lifecycle:

```python
class OAuth2Auth(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    auth_uri: str | None = None # generated authorization URL
    state: str | None = None # CSRF state parameter
    redirect_uri: str | None = None
    auth_response_uri: str | None = None # callback URI with code
    auth_code: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    expires_at: int | None = None
    expires_in: int | None = None
    audience: str | None = None
    token_endpoint_auth_method: Literal[
    "client_secret_basic",
    "client_secret_post",
    "client_secret_jwt",
    "private_key_jwt",
    ] | None = "client_secret_basic"
```

### ServiceAccount

For Google Cloud service account authentication:

```python
class ServiceAccount(BaseModel):
    service_account_credential: ServiceAccountCredential | None = None
    scopes: list[str] | None = None
    use_default_credential: bool | None = False
    use_id_token: bool | None = False # exchange for ID token instead of access token
    audience: str | None = None # required when use_id_token is True
```

Validation: `service_account_credential` is required when `use_default_credential` is `False`. `audience` is required when `use_id_token` is `True`.

### AuthScheme and AuthSchemeType

`AuthScheme` is a union of OpenAPI `SecurityScheme` (from FastAPI's models) and ADK's `OpenIdConnectWithConfig`. ADK reuses FastAPI's OpenAPI security scheme models (`pip install fastapi` required).

```python
AuthScheme = Union[SecurityScheme, OpenIdConnectWithConfig]
AuthSchemeType = SecuritySchemeType # re-export from FastAPI/OpenAPI
```

`OpenIdConnectWithConfig` flattens OIDC discovery into explicit fields:

```python
class OpenIdConnectWithConfig(SecurityBase):
    type_: SecuritySchemeType = SecuritySchemeType.openIdConnect
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str | None = None
    revocation_endpoint: str | None = None
    token_endpoint_auth_methods_supported: list[str] | None = None
    grant_types_supported: list[str] | None = None
    scopes: list[str] | None = None
```

### AuthConfig

The configuration object that ties scheme + credential together and gets passed through the auth flow:

```python
class AuthConfig(BaseModel):
    auth_scheme: AuthScheme
    raw_auth_credential: AuthCredential | None = None
    exchanged_auth_credential: AuthCredential | None = None
    credential_key: str | None = None
```

- `auth_scheme`: Describes the type of auth required (OpenAPI security scheme).
- `raw_auth_credential`: The initial credential from the tool (e.g., client_id + secret for OAuth).
- `exchanged_auth_credential`: Filled in by ADK during the flow. For OAuth, this gets the `auth_uri` and `state` added, then later the access token after exchange.
- `credential_key`: Stable key for storing/loading this credential. If not provided, one is auto-generated from a hash of the scheme and credential.

### AuthHandler

Internal orchestrator (not used directly by tool authors):

```python
class AuthHandler:
    def __init__(self, auth_config: AuthConfig): ...

    def generate_auth_request(self) -> AuthConfig:
        """Generates the auth config with auth_uri for OAuth flows."""

    async def exchange_auth_token(self) -> AuthCredential:
        """Exchanges the auth code/response for tokens."""

    async def parse_and_store_auth_response(self, state: State) -> None:
        """Exchanges tokens and stores the result in session state."""

    def get_auth_response(self, state: State) -> AuthCredential:
        """Retrieves the stored credential from session state."""
```

`generate_auth_request` uses `authlib` to build the authorization URL. Without `authlib`, returns raw credential.

---

## The OAuth Round-Trip Flow

### Detailed Steps

The detailed sequence for OAuth2 authorization code flow:

1. **Tool calls `request_credential`**: This adds the `AuthConfig` to `EventActions.requested_auth_configs`, keyed by `function_call_id`.

> These are internal details — you don't normally interact with `EventActions` or `temp:` keys directly.

2. **ADK calls `AuthHandler.generate_auth_request()`**: If the raw credential has `client_id` and `client_secret` but no `auth_uri`, ADK uses `authlib.OAuth2Session` to generate the authorization URL and CSRF state. The result is stored in `exchanged_auth_credential.oauth2.auth_uri`.

3. **Client receives the event** with the auth request. The client redirects the user to `auth_uri`.

4. **User completes the OAuth flow** and the OAuth provider redirects back. The client captures the callback and sends the `auth_response_uri` or `auth_code` back to ADK.

5. **ADK calls `AuthHandler.parse_and_store_auth_response()`**: For OAuth/OIDC schemes, this calls `exchange_auth_token()` using `OAuth2CredentialExchanger` to swap the auth code for access/refresh tokens. The exchanged credential is stored in session state under the key `"temp:{credential_key}"`.

6. **Tool is re-invoked**. It calls `get_auth_response(auth_config)`, which reads the credential from session state. The tool now has the access token.

---

## Context Methods for Auth

The `CallbackContext` (and its alias used in tools, `ToolContext`) provides these auth methods. Both resolve to the same `Context` class (see [09-tools.md](09-tools.md)).

### request_credential

```python
def request_credential(self, auth_config: AuthConfig) -> None:
```

Triggers the auth flow by storing the request in event actions. Only callable from a tool context (requires `function_call_id`). Raises `ValueError` if `function_call_id` is not set.

### get_auth_response

```python
def get_auth_response(self, auth_config: AuthConfig) -> AuthCredential | None:
```

Retrieves the credential stored after the user completed auth. Returns `None` if the user has not yet responded. Uses the `credential_key` to look up `"temp:{credential_key}"` in session state.

Returns `None` if the user hasn't responded yet or denied OAuth. Guard against infinite retry by checking a counter or timeout.

### save_credential

```python
async def save_credential(self, auth_config: AuthConfig) -> None:
```

Persists a credential to the credential service (if configured). Useful for long-term storage beyond session state.

### load_credential

```python
async def load_credential(self, auth_config: AuthConfig) -> AuthCredential | None:
```

Loads a previously saved credential from the credential service.

Use `save_credential`/`load_credential` for custom credential backends or when you need to persist credentials outside the standard OAuth flow. For most cases, `parse_and_store_auth_response` handles this automatically.

---

## Credential Key

`credential_key` determines storage location (`"temp:{key}"`). If unset:

1. ADK checks `model_extra` on the raw credential and auth scheme for a `credential_key` or `credentialKey` field.
2. If still not found, it auto-generates a key by hashing the auth scheme and raw credential: `"adk_{scheme_type}_{scheme_hash}_{cred_type}_{cred_hash}"`.

Set `credential_key` explicitly for stability across code changes.

---

## Code Examples

### Tool with API Key Auth

```python
from fastapi.openapi.models import SecurityScheme, SecuritySchemeType
from google.adk.auth import AuthCredential, AuthCredentialTypes, AuthConfig

api_key_scheme = SecurityScheme(
    type=SecuritySchemeType.apiKey,
    name="X-API-Key",
    in_="header",
)

api_key_auth_config = AuthConfig(
    auth_scheme=api_key_scheme,
    credential_key="my_api_key",
)

async def call_external_api(
    query: str,
    ctx: ToolContext,
) -> dict[str, str]:
    """Calls an external API that requires an API key."""
    # Check if we already have a credential
    credential = ctx.get_auth_response(api_key_auth_config)

    if credential is None:
        # Request the credential from the user
        ctx.request_credential(api_key_auth_config)
        return {"status": "awaiting_api_key"}

    # Use the credential
    api_key = credential.api_key
    # ... make the API call with the key ...
    return {"result": f"Called API with key for query: {query}"}
```

### Tool with OAuth2 Auth

```python
from fastapi.openapi.models import (
    SecurityScheme,
    SecuritySchemeType,
    OAuthFlows,
    OAuthFlowAuthorizationCode,
)
from google.adk.auth import (
    AuthCredential,
    AuthCredentialTypes,
    AuthConfig,
    OAuth2Auth,
)

oauth_scheme = SecurityScheme(
    type=SecuritySchemeType.oauth2,
    flows=OAuthFlows(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl="https://accounts.google.com/o/oauth2/auth",
            tokenUrl="https://oauth2.googleapis.com/token",
            scopes={
                "https://www.googleapis.com/auth/calendar.readonly": "Read calendar",
            },
        ),
    ),
)

oauth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        redirect_uri="http://localhost:8000/callback",
    ),
)

calendar_auth_config = AuthConfig(
    auth_scheme=oauth_scheme,
    raw_auth_credential=oauth_credential,
    credential_key="google_calendar_oauth",
)

async def list_calendar_events(
    ctx: ToolContext,
) -> dict[str, Any]:
    """Lists upcoming calendar events using OAuth2."""
    # Check if auth flow is complete
    credential = ctx.get_auth_response(calendar_auth_config)

    if credential is None:
        # Initiate OAuth flow — ADK will generate auth_uri
        ctx.request_credential(calendar_auth_config)
        return {"status": "awaiting_oauth"}

    # Auth complete — use the access token
    access_token = credential.oauth2.access_token
    # ... call Google Calendar API with access_token ...
    return {"events": ["Meeting at 10am", "Lunch at noon"]}
```

### Tool with HTTP Bearer Token

```python
from fastapi.openapi.models import SecurityScheme, SecuritySchemeType, HTTPBase
from google.adk.auth import (
    AuthCredential,
    AuthCredentialTypes,
    AuthConfig,
    HttpAuth,
    HttpCredentials,
)
from google.adk.tools import ToolContext

bearer_scheme = SecurityScheme(
    type=SecuritySchemeType.http,
    scheme="bearer",
)

bearer_auth_config = AuthConfig(
    auth_scheme=bearer_scheme,
    credential_key="my_bearer_token",
)

async def call_bearer_api(
    query: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Calls an API that requires a Bearer token."""
    auth = tool_context.get_auth_response(bearer_auth_config)
    if auth is None:
        tool_context.request_credential(bearer_auth_config)
        return {"status": "awaiting_authorization"}
    # auth is available — proceed
    token = auth.http.credentials.token
    # ... make the API call with the bearer token ...
    return {"result": f"Called API for query: {query}"}
```

### Tool with Service Account

```python
from google.adk.auth import AuthCredential, AuthCredentialTypes, ServiceAccount

sa_credential = AuthCredential(
    auth_type=AuthCredentialTypes.SERVICE_ACCOUNT,
    service_account=ServiceAccount(
        use_default_credential=True,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    ),
)
```

For service-to-service ID token exchange (e.g., calling Cloud Run):

```python
sa_credential = AuthCredential(
    auth_type=AuthCredentialTypes.SERVICE_ACCOUNT,
    service_account=ServiceAccount(
        use_default_credential=True,
        use_id_token=True,
        audience="https://my-service-xyz.run.app",
    ),
)
```

### Guard Clause for get_auth_response Returning None

Always guard against `None` before using a credential. If `get_auth_response` returns `None`, request the credential and return early:

```python
auth = tool_context.get_auth_response(auth_config)
if auth is None:
    tool_context.request_credential(auth_config)
    return {"status": "awaiting_authorization"}
# auth is available — proceed
```

---

## Cross-References

- [09-tools.md](09-tools.md) — tools call `request_credential` and `get_auth_response` via `ToolContext`
- [05-flows.md](05-flows.md) — auth flow is triggered during tool execution in the flow's postprocess phase
- [12-artifacts.md](12-artifacts.md) — artifacts, another service-level concern wired similarly to credentials
- [03-runners.md](03-runners.md) — `Runner` accepts `credential_service` and threads it into context
