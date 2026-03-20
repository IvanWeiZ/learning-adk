# Artifact Service Deep Dive

> **Official docs:** [Artifacts](https://google.github.io/adk-docs/runtime/artifacts/) | **Source:** [`base_artifact_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/artifacts/base_artifact_service.py) · [`in_memory_artifact_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/artifacts/in_memory_artifact_service.py) · [`file_artifact_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/artifacts/file_artifact_service.py) · [`gcs_artifact_service.py`](https://github.com/google/adk-python/blob/main/src/google/adk/artifacts/gcs_artifact_service.py) | **Prereqs:** [08-sessions.md](08-sessions.md)

---

## What Artifacts Are

Artifacts are versioned, named files (text, images, PDFs, binary) stored outside the event stream.

Use artifacts when a tool needs to:
- Generate a file the user can download (report, chart, CSV)
- Accept an uploaded file and refer to it across turns
- Share binary data between tools within a session
- Persist outputs that survive session deletion

Artifacts are stored as `google.genai.types.Part` objects, which can hold `text`, `inline_data` (binary blob with MIME type), or `file_data` (external URI reference).

---

## Class Hierarchy

```
BaseArtifactService (abstract interface)
 ├── InMemoryArtifactService (dev/test — Python dicts)
 ├── FileArtifactService (local disk — versioned directories)
 └── GcsArtifactService (production — Google Cloud Storage)
```

---

## ArtifactVersion Metadata

Every saved artifact version gets an `ArtifactVersion` record:

```python
class ArtifactVersion(BaseModel):
    version: int # 0-based, monotonically increasing
    canonical_uri: str # URI pointing to the persisted payload
    custom_metadata: dict[str, Any] = {} # user-supplied key-value pairs
    create_time: float # unix timestamp (seconds)
    mime_type: str | None = None # MIME type of the payload
```

Fields use camelCase aliases for JSON serialization (`populate_by_name=True`).

---

## BaseArtifactService Interface

All methods are `async` with keyword-only arguments, scoped by `app_name`, `user_id`, and optional `session_id`.

### save_artifact

```python
async def save_artifact(
    self,
    *,
    app_name: str,
    user_id: str,
    filename: str,
    artifact: types.Part | dict[str, Any],
    session_id: str | None = None,
    custom_metadata: dict[str, Any] | None = None,
) -> int:
```

Saves a new version of the artifact identified by `filename`. Returns the version number (0 for the first save, incremented by 1 after each save). Accepts a `types.Part` or a plain dict (normalized internally via `ensure_part`).

### load_artifact

```python
async def load_artifact(
    self,
    *,
    app_name: str,
    user_id: str,
    filename: str,
    session_id: str | None = None,
    version: int | None = None,
) -> types.Part | None:
```

Loads a specific version. If `version` is `None`, returns the latest version. Returns `None` if not found.

### list_artifact_keys

```python
async def list_artifact_keys(
    self,
    *,
    app_name: str,
    user_id: str,
    session_id: str | None = None,
) -> list[str]:
```

Returns all artifact filenames. If `session_id` is provided, returns both session-scoped and user-scoped filenames. If `session_id` is `None`, returns only user-scoped filenames.

### delete_artifact

```python
async def delete_artifact(
    self,
    *,
    app_name: str,
    user_id: str,
    filename: str,
    session_id: str | None = None,
) -> None:
```

Deletes all versions of an artifact.

### list_versions

```python
async def list_versions(
    self,
    *,
    app_name: str,
    user_id: str,
    filename: str,
    session_id: str | None = None,
) -> list[int]:
```

Returns a list of version numbers (integers) available for the artifact.

### list_artifact_versions

```python
async def list_artifact_versions(
    self,
    *,
    app_name: str,
    user_id: str,
    filename: str,
    session_id: str | None = None,
) -> list[ArtifactVersion]:
```

Returns full `ArtifactVersion` metadata for every version.

### get_artifact_version

```python
async def get_artifact_version(
    self,
    *,
    app_name: str,
    user_id: str,
    filename: str,
    session_id: str | None = None,
    version: int | None = None,
) -> ArtifactVersion | None:
```

Returns metadata for one version. If `version` is `None`, returns metadata for the latest.

---

## Scoping: Session vs. User

Artifacts can be scoped to a **session** or to a **user** (shared across sessions):

- **Session-scoped** (default): pass a `session_id`. Storage path includes the session.
- **User-scoped**: prefix the filename with `"user:"` (e.g., `"user:profile.png"`). The `session_id` is ignored for storage, and the artifact is visible from any session for that user.

When `list_artifact_keys` is called with a `session_id`, it returns both session-scoped artifacts for that session and all user-scoped artifacts.

```
Artifact Scoping — where files are stored:

Session-scoped (default):
 save_artifact("report.pdf", data)
 Path: app_name / user_id / session_id / report.pdf / v0

User-scoped (prefix with "user:"):
 save_artifact("user:avatar.png", data)
 Path: app_name / user_id / avatar.png / v0
 ↑ no session_id — shared across ALL sessions for this user

Version Timeline:
 save_artifact("report.pdf", v1_data) → returns version 0
 save_artifact("report.pdf", v2_data) → returns version 1
 save_artifact("report.pdf", v3_data) → returns version 2

 load_artifact("report.pdf") → returns v3_data (latest)
 load_artifact("report.pdf", version=1) → returns v2_data (specific)

 Versions are immutable — you can always go back.
```

---

## Three Implementations Compared

| | InMemoryArtifactService | FileArtifactService | GcsArtifactService |
|---|---|---|---|
| Storage | Python `dict` | Local filesystem | Google Cloud Storage bucket |
| Init | `InMemoryArtifactService()` | `FileArtifactService(root_dir="./artifacts")` | `GcsArtifactService(bucket_name="my-bucket")` |
| Thread-safe | No (dev/test only) | Yes (via `asyncio.to_thread`) | Yes (via `asyncio.to_thread`) |
| Persistence | Process lifetime only | Survives restarts | Durable cloud storage |
| `file_data` support | Stores as-is (artifact refs) | Not supported (raises error) | Not supported (raises `NotImplementedError`) |
| Custom metadata | Stored in `ArtifactVersion` | Written to `metadata.json` per version | Stored as GCS blob metadata |

### InMemoryArtifactService

Stores artifacts as a `dict[str, list[_ArtifactEntry]]` keyed by path. Suitable for tests and prototyping. Extends `BaseModel` (Pydantic), so its state is serializable.

### FileArtifactService

Writes artifacts to a directory tree under `root_dir`:

```
root_dir/
└── users/
 └── {user_id}/
 ├── sessions/
 │ └── {session_id}/
 │ └── artifacts/
 │ └── {artifact_path}/
 │ └── versions/
 │ └── {version}/
 │ ├── {original_filename}
 │ └── metadata.json
 └── artifacts/ # user-scoped
 └── {artifact_path}/...
```

Filenames can include path separators (`"images/photo.png"`) to create nested directories. Path traversal (`"../../secret.txt"`) is rejected with `InputValidationError`.

### GcsArtifactService

Uses `google.cloud.storage` to read/write blobs. Blob names follow the pattern `{app_name}/{user_id}/{session_id}/{filename}/{version}`. The GCS client is imported lazily inside `__init__`, so the `google-cloud-storage` package is only needed when this backend is used.

---

## Versioning Semantics

- Version numbering starts at **0** and increments by 1 with each `save_artifact` call.
- Every save creates a new version; existing versions are never overwritten.
- `load_artifact(version=None)` returns the latest version.
- `delete_artifact` removes all versions at once.
- The `artifact_delta` on `EventActions` records which artifacts were created/updated during a tool call, mapping `filename -> version`.

---

## Using Artifacts from Tools via CallbackContext

`ToolContext` provides convenience methods that auto-fill `app_name`, `user_id`, and `session_id`:

```python
# CallbackContext methods (available in both ToolContext and callbacks)

async def save_artifact(
    self,
    filename: str,
    artifact: types.Part,
    custom_metadata: dict[str, Any] | None = None,
) -> int:
    """Saves an artifact, returns the version number."""

async def load_artifact(
    self,
    filename: str,
    version: int | None = None,
) -> types.Part | None:
    """Loads an artifact by filename. Returns None if not found."""

async def list_artifacts(self) -> list[str]:
    """Lists all artifact filenames for the current session."""

async def get_artifact_version(
    self,
    filename: str,
    version: int | None = None,
) -> ArtifactVersion | None:
    """Gets metadata for a specific artifact version."""
```

These methods raise `ValueError` if no `artifact_service` is configured on the Runner.

---

## Wiring artifact_service to Runner

Pass the artifact service when creating the `Runner`:

```python
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService

runner = Runner(
    app_name="my_app",
    agent=my_agent,
    artifact_service=InMemoryArtifactService(),
    session_service=InMemorySessionService(),
)
```

For production with GCS:

```python
from google.adk.artifacts import GcsArtifactService

runner = Runner(
    app_name="my_app",
    agent=my_agent,
    artifact_service=GcsArtifactService(bucket_name="my-artifacts-bucket"),
    session_service=session_service,
)
```

For local file-based persistence:

```python
from google.adk.artifacts import FileArtifactService

runner = Runner(
    app_name="my_app",
    agent=my_agent,
    artifact_service=FileArtifactService(root_dir="./artifact_store"),
    session_service=session_service,
)
```

---

## Code Examples

### Saving and loading text artifacts in a tool

```python
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types

async def generate_report(
    topic: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Generates a report and saves it as an artifact."""
    report_text = f"# Report on {topic}\n\nThis is the report content."

    version = await tool_context.save_artifact(
        filename="report.md",
        artifact=types.Part(text=report_text),
    )
    return {"status": "saved", "filename": "report.md", "version": version}

async def read_report(tool_context: ToolContext) -> dict[str, str]:
    """Reads the latest version of the report artifact."""
    part = await tool_context.load_artifact("report.md")
    if part is None:
        return {"error": "No report found"}
    return {"content": part.text}
```

### Saving a binary artifact (image)

```python
async def save_chart(
    chart_bytes: bytes,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Saves a PNG chart as a binary artifact."""
    version = await tool_context.save_artifact(
        filename="chart.png",
        artifact=types.Part(
            inline_data=types.Blob(
                mime_type="image/png",
                data=chart_bytes,
            )
        ),
        custom_metadata={"generated_by": "charting_tool"},
    )
    return {"filename": "chart.png", "version": version}
```

### User-scoped artifacts (shared across sessions)

```python
async def save_user_preference(
    preferences_json: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Saves preferences visible from all sessions for this user."""
    version = await tool_context.save_artifact(
        filename="user:preferences.json", # "user:" prefix = user-scoped
        artifact=types.Part(text=preferences_json),
    )
    return {"version": version}
```

### Listing and inspecting artifact versions

```python
async def inspect_artifacts(tool_context: ToolContext) -> dict[str, Any]:
    """Lists all artifacts and checks version info."""
    filenames = await tool_context.list_artifacts()
    result: dict[str, Any] = {"artifacts": filenames}

    for name in filenames:
        version_info = await tool_context.get_artifact_version(name)
        if version_info:
            result[name] = {
                "latest_version": version_info.version,
                "mime_type": version_info.mime_type,
                "created": version_info.create_time,
            }
    return result
```

---

## Cross-References

- [09-tools.md](09-tools.md) — tools access artifacts via `ToolContext.save_artifact()` and `ToolContext.load_artifact()`
- [10-apps.md](10-apps.md) — `App` container that holds the artifact service
- [03-runners.md](03-runners.md) — `Runner` accepts `artifact_service` and threads it into the invocation context
- [13-auth.md](13-auth.md) — credentials, another service-level concern wired similarly to artifacts
