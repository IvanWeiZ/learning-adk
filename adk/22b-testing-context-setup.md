# 22b — Testing: Context Setup & Advanced Fixtures

> **Official docs:** [Testing](https://google.github.io/adk-docs/evaluate/) | **Source:** [`tests/`](https://github.com/google/adk-python/tree/main/tests) | **Prereqs:** [22-testing.md](22-testing.md)

*This file continues from [22-testing.md](22-testing.md), which covers MockModel, InMemoryRunner, simplify_events, and the test utilities reference.*

---

## Creating Dependencies

### create_invocation_context — Full Context Without a Runner

For low-level tests that need direct access to `InvocationContext` without a full runner:

```python
from tests.unittests.testing_utils import create_invocation_context

ctx = await create_invocation_context(
    agent=my_agent,
    user_content='test message',         # optional
    run_config=RunConfig(),              # optional
    plugins=[my_plugin],                 # optional
)
# ctx has:
#   ctx.artifact_service  → InMemoryArtifactService
#   ctx.session_service   → InMemorySessionService
#   ctx.memory_service    → InMemoryMemoryService
#   ctx.plugin_manager    → PluginManager(plugins)
#   ctx.session           → fresh session with app_name='test_app', user_id='test_user'
```

### Creating a ToolContext (Context)

**Important:** `ToolContext` is an alias for `Context` (see `tool_context.py` line 30: `ToolContext = Context`). `Context` extends `ReadonlyContext` and adds mutable state, artifacts, credentials, memory, and tool confirmation.

#### Option A: Via MagicMock (unit-level, for isolated tool testing)

```python
from unittest.mock import MagicMock
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.session import Session
from google.adk.tools.tool_context import ToolContext  # alias for Context

@pytest.fixture
def mock_tool_context() -> ToolContext:
    mock_invocation_context = MagicMock(spec=InvocationContext)
    mock_invocation_context.session = MagicMock(spec=Session)
    mock_invocation_context.session.state = MagicMock()
    return ToolContext(invocation_context=mock_invocation_context)
```

This is the simplest approach. Use it when you just need a `ToolContext` parameter and don't need real state or artifact operations.

#### Option B: Via create_invocation_context (integration-level, real services)

```python
from tests.unittests.testing_utils import create_invocation_context
from google.adk.tools.tool_context import ToolContext

async def make_real_tool_context() -> ToolContext:
    agent = LlmAgent(name='test_agent')
    ctx = await create_invocation_context(agent)
    return ToolContext(invocation_context=ctx)
```

This gives you real in-memory services, so `tool_context.state`, `tool_context.save_artifact()`, etc. all work.

#### Option C: Via InMemoryRunner (full integration, tools execute in agent loop)

```python
# No manual ToolContext creation needed — the runner wires everything
mock = MockModel.create(responses=[
    Part.from_function_call(name='my_tool', args={'x': 1}),
    'done',
])
agent = Agent(name='test', model=mock, tools=[my_tool])
runner = InMemoryRunner(root_agent=agent)
events = runner.run('do it')
```

### Creating a ReadonlyContext (for instruction/field tests)

```python
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.in_memory_session_service import InMemorySessionService

async def _create_readonly_context(
    agent: LlmAgent, state: dict[str, Any] | None = None
) -> ReadonlyContext:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name='test_app', user_id='test_user', state=state
    )
    invocation_context = InvocationContext(
        invocation_id='test_id',
        agent=agent,
        session=session,
        session_service=session_service,
    )
    return ReadonlyContext(invocation_context)
```

### Creating an InvocationContext Manually

For maximum control, build `InvocationContext` directly:

```python
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.plugins.plugin_manager import PluginManager

session_service = InMemorySessionService()
session = await session_service.create_session(
    app_name='test_app', user_id='test_user'
)

ctx = InvocationContext(
    invocation_id='test_invocation_id',
    agent=my_agent,
    session=session,
    session_service=session_service,
    artifact_service=InMemoryArtifactService(),       # optional
    memory_service=InMemoryMemoryService(),            # optional
    plugin_manager=PluginManager(plugins=[]),           # optional
    run_config=RunConfig(),                             # optional
)
```

---

## Related

- [22-testing.md](22-testing.md) — MockModel, InMemoryRunner, simplify_events, test utilities reference
- [22c-testing-examples.md](22c-testing-examples.md) — Comprehensive test examples for LlmAgent features, callbacks, plugins, tools
