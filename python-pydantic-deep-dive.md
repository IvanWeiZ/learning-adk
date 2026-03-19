# Python Pydantic v2 Deep Dive

**For:** Experienced Java developers building with Google ADK
**Pydantic version:** 2.x (Python 3.10+)

---

## What It Is

Pydantic is Python's premier data validation and serialization library. It uses standard Python type hints to define data models that validate on construction, serialize to dict/JSON, and generate JSON Schema automatically. For a Java developer, think of it as **Lombok + Jackson + Bean Validation** combined into a single, type-hint-driven system. Every core ADK data structure --- `Session`, `Event`, `EventActions`, `LlmAgent`, `InvocationContext` --- is a Pydantic `BaseModel` subclass.

---

## BaseModel Basics

### Defining Models

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str                        # required, no default
    age: int                         # required
    email: str | None = None         # optional (Python 3.10+ union syntax)
    active: bool = True              # optional with default

user = User(name="Alice", age=30)
print(user.name)    # "Alice"
print(user.email)   # None
```

Pydantic validates on construction. Pass `age="not_a_number"` and you get a `ValidationError` immediately --- no separate `.validate()` call needed.

### model_config (ConfigDict)

`ConfigDict` controls model-wide behavior, similar to class-level annotations in Java:

```python
from pydantic import BaseModel, ConfigDict

class Event(BaseModel):
    model_config = ConfigDict(
        frozen=True,                     # immutable after creation
        arbitrary_types_allowed=True,    # accept non-standard types
        populate_by_name=True,           # accept both field name and alias
        extra="forbid",                  # reject unknown fields
    )
    event_id: str
    timestamp: float
```

### Immutable vs Mutable Models

```python
# Mutable (default) --- fields can be reassigned after creation
class MutableConfig(BaseModel):
    timeout: int = 30

cfg = MutableConfig()
cfg.timeout = 60  # works

# Immutable --- any assignment raises an error
class ImmutableConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    timeout: int = 30

cfg = ImmutableConfig()
cfg.timeout = 60  # raises ValidationError
# To "modify" a frozen model, use model_copy:
new_cfg = cfg.model_copy(update={"timeout": 60})
```

### Serialization and Deserialization

```python
user = User(name="Alice", age=30)

# To Python dict
user.model_dump()                          # {"name": "Alice", "age": 30, "email": None, "active": True}
user.model_dump(exclude_none=True)         # {"name": "Alice", "age": 30, "active": True}
user.model_dump(include={"name", "age"})   # {"name": "Alice", "age": 30}

# To JSON string
user.model_dump_json(indent=2)

# From a dict
user = User.model_validate({"name": "Alice", "age": 30})

# From a JSON string
user = User.model_validate_json('{"name": "Alice", "age": 30}')
```

---

## Validators

### @field_validator (before, after, wrap modes)

```python
from pydantic import BaseModel, field_validator

class Agent(BaseModel):
    name: str

    # mode="after" (default) --- runs after Pydantic's own type coercion
    @field_validator("name")
    @classmethod
    def name_must_be_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError("Agent name must be a valid Python identifier")
        if v == "user":
            raise ValueError('"user" is reserved by ADK')
        return v

    # mode="before" --- runs on the raw input before any type conversion
    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    # mode="wrap" --- wraps the default validator; receives a handler
    @field_validator("name", mode="wrap")
    @classmethod
    def wrap_name(cls, v, handler):
        return handler(v).lower()    # call chain, then post-process
```

### @model_validator (before, after, wrap modes)

Cross-field validation that runs after all fields are set:

```python
from pydantic import model_validator

class DateRange(BaseModel):
    start: float
    end: float

    @model_validator(mode="after")
    def end_after_start(self) -> "DateRange":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self

    # mode="before" receives raw input as a dict
    @model_validator(mode="before")
    @classmethod
    def fill_defaults(cls, data: dict) -> dict:
        if "end" not in data:
            data["end"] = data.get("start", 0) + 3600
        return data
```

### Annotated Types with AfterValidator, BeforeValidator

Reusable validation without a model:

```python
from typing import Annotated
from pydantic import AfterValidator, BeforeValidator

def must_be_positive(v: int) -> int:
    if v <= 0:
        raise ValueError("must be positive")
    return v

PositiveInt = Annotated[int, AfterValidator(must_be_positive)]

class Config(BaseModel):
    max_retries: PositiveInt = 3
    timeout_ms: PositiveInt = 5000
```

### Custom Types

For domain types that need Pydantic-aware validation, implement `__get_pydantic_core_schema__`:

```python
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

class AgentName(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate, core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, v: str) -> "AgentName":
        if not v.isidentifier() or v == "user":
            raise ValueError(f"Invalid agent name: {v!r}")
        return cls(v)
```

---

## How ADK Uses Pydantic

### Session, Event, EventActions Are All BaseModel Subclasses

```python
# Simplified from google.adk.sessions.session
class Session(BaseModel):
    id: str
    app_name: str
    user_id: str
    state: dict[str, Any] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    last_update_time: float = 0.0

# Simplified from google.adk.events.event
class Event(BaseModel):
    id: str
    invocation_id: str
    author: str
    content: Content | None = None
    actions: EventActions = Field(default_factory=EventActions)
    timestamp: float | None = None

# Simplified from google.adk.events.event_actions
class EventActions(BaseModel):
    state_delta: dict[str, Any] = Field(default_factory=dict)
    transfer_to_agent: str | None = None
    escalate: bool = False
    artifact_delta: dict[str, int] = Field(default_factory=dict)
```

Because these are all `BaseModel`, you get validation, serialization, and JSON Schema for free.

### LlmAgent Fields Use Pydantic Validation

`LlmAgent` declares its configuration as typed Pydantic fields. The model name, temperature, tools list, and callback hooks are all validated when you construct an agent:

```python
agent = LlmAgent(
    name="weather_agent",
    model="gemini-2.0-flash",
    instruction="You are a weather assistant.",
    tools=[get_weather],
)
```

Pass an invalid `name` (like `"user"`) and Pydantic raises a `ValidationError` at construction time, not at runtime.

### InvocationContext as a Pydantic Model

`InvocationContext` carries session, state, and credentials through every call. ADK creates child contexts using `model_copy(update={...})`:

```python
child_ctx = parent_ctx.model_copy(update={
    "agent": sub_agent,
    "branch": f"{parent_ctx.branch}.{sub_agent.name}",
})
```

### Tool Argument Schemas Derived from Type Hints

When you define a tool function, ADK inspects its type hints and generates a JSON Schema that the LLM uses to produce structured arguments --- mirroring Pydantic's `model_json_schema()`:

```python
def get_weather(city: str, unit: str = "celsius") -> str:
    """Get the current weather for a city."""
    ...
# ADK generates: {"type": "object", "properties": {"city": {"type": "string"},
#   "unit": {"type": "string", "default": "celsius"}}, "required": ["city"]}
```

---

## Common Patterns

### Optional Fields with Defaults

```python
class AgentConfig(BaseModel):
    name: str                                          # required
    model: str = "gemini-2.0-flash"                    # optional with default
    temperature: float | None = None                   # optional, None means "use model default"
    tools: list[str] = Field(default_factory=list)     # mutable default via factory
```

### Nested Models

```python
class ToolResult(BaseModel):
    output: str
    error: str | None = None

class Event(BaseModel):
    author: str
    tool_result: ToolResult | None = None

# Pydantic auto-converts dicts to nested models:
event = Event(author="tool", tool_result={"output": "18C in Tokyo"})
print(type(event.tool_result))  # <class 'ToolResult'>
```

### arbitrary_types_allowed

ADK models sometimes hold non-Pydantic objects (e.g., `asyncio.Lock`, third-party SDK types):

```python
from pydantic import BaseModel, ConfigDict
import asyncio

class RunnerState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
```

### Computed Fields (@computed_field)

Derived values that appear in serialization but are not stored:

```python
from pydantic import computed_field

class Session(BaseModel):
    events: list[Event] = Field(default_factory=list)

    @computed_field
    @property
    def turn_count(self) -> int:
        return len([e for e in self.events if e.author == "user"])
```

### Private Attributes (PrivateAttr)

Internal state that Pydantic ignores during validation and serialization:

```python
from pydantic import PrivateAttr

class Agent(BaseModel):
    name: str
    _call_count: int = PrivateAttr(default=0)

    def record_call(self) -> None:
        self._call_count += 1

agent = Agent(name="assistant")
agent.record_call()
print(agent._call_count)       # 1
print(agent.model_dump())      # {"name": "assistant"} --- _call_count excluded
```

---

## Java Comparison Table

| Java | Pydantic v2 | Notes |
|------|-------------|-------|
| `record User(String name, int age) {}` | `class User(BaseModel): name: str; age: int` | Immutable data carrier |
| `@Data` (Lombok) | `class User(BaseModel)` | Auto equals, hash, repr |
| `@Value` (Lombok, immutable) | `model_config = ConfigDict(frozen=True)` | Immutable after creation |
| `@JsonProperty("first_name")` | `Field(alias="first_name")` | JSON field mapping |
| `@JsonIgnore` | `Field(exclude=True)` | Exclude from serialization |
| `@NotNull` | Required field (no default) | Fails if missing |
| `@Min(0) @Max(100)` | `Field(ge=0, le=100)` | Numeric constraints |
| `@Size(min=1, max=50)` | `Field(min_length=1, max_length=50)` | String/collection length |
| `@Pattern("^[a-z]+$")` | `Field(pattern="^[a-z]+$")` | Regex constraint |
| `@Valid` (nested) | Automatic for nested BaseModel | Cascading validation |
| `ObjectMapper.writeValueAsString()` | `model.model_dump_json()` | Serialize to JSON |
| `ObjectMapper.readValue(json, Cls)` | `Cls.model_validate_json(json)` | Deserialize from JSON |
| `toBuilder().field(x).build()` | `model.model_copy(update={"field": x})` | Immutable update |
| `sealed interface` + `@JsonTypeInfo` | `Union[A, B]` + `Field(discriminator=...)` | Discriminated unions |
| Custom `JsonDeserializer` | `@field_validator(mode="before")` | Custom deserialization |
| Custom `JsonSerializer` | `@field_serializer` | Custom serialization |
| `@Transient` | `PrivateAttr(default=...)` | Non-serialized internal state |

---

## Gotchas

### 1. Pydantic v1 vs v2 Differences

ADK uses Pydantic v2. Many tutorials and older code use v1 APIs. Key renames:

| v1 (deprecated) | v2 (current) |
|------------------|--------------|
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.parse_obj(data)` | `.model_validate(data)` |
| `.parse_raw(json)` | `.model_validate_json(json)` |
| `.copy(update={})` | `.model_copy(update={})` |
| `.schema()` | `.model_json_schema()` |
| `@validator` | `@field_validator` |
| `@root_validator` | `@model_validator` |
| `class Config:` (inner class) | `model_config = ConfigDict(...)` |

If you see `user.dict()` in example code, it is v1 syntax and will emit a deprecation warning.

### 2. Mutable Default Gotcha

```python
# BUG: all instances share the same list object
class Bad(BaseModel):
    tags: list[str] = []

# FIX: each instance gets a fresh list
class Good(BaseModel):
    tags: list[str] = Field(default_factory=list)
```

Pydantic v2 actually protects against this in most cases by copying defaults, but using `default_factory` is the explicit, safe convention --- and what you will see throughout ADK source code.

### 3. Serialization of Non-Standard Types

Types like `asyncio.Lock` or custom classes cannot be serialized to JSON. If your model holds them, either:
- Use `PrivateAttr` to exclude them from serialization.
- Set `arbitrary_types_allowed=True` and add a `@field_serializer` to handle them.
- Use `Field(exclude=True)` to skip them in `model_dump()`.

### 4. Direct Assignment Skips Validation

```python
class User(BaseModel):
    age: int

user = User(age=30)
user.age = "not_a_number"   # no error! Pydantic only validates on construction
print(user.age)             # "not_a_number"
```

Use `ConfigDict(frozen=True)` or `ConfigDict(validate_assignment=True)` to prevent this.

### 5. model_copy() is Shallow by Default

```python
original = Session(state={"counter": [1, 2, 3]})
copy = original.model_copy()
copy.state["counter"].append(4)
print(original.state["counter"])  # [1, 2, 3, 4] --- shared reference!

# Use deep=True for independent nested copies:
copy = original.model_copy(deep=True)
```

---

## Cross-References

- [Events](adk/07-events.md) --- `Event` and `EventActions` are the most visible Pydantic models in ADK
- [Sessions](adk/08-sessions.md) --- `Session` is a BaseModel; `state` dict is carried in EventActions
- [Agents](adk/04-agents.md) --- `LlmAgent` and `BaseAgent` use Pydantic fields for configuration
- [Python for ADK Learning Plan](python/python-for-adk-learning-plan.md) --- broader Python curriculum including Pydantic
- [Decorators and Metaprogramming](python/python-decorators-metaprogramming-deep-dive.md) --- `@field_validator` and `@model_validator` are decorator-based

---

*Part of the [learning-adk](README.md) documentation series.*
