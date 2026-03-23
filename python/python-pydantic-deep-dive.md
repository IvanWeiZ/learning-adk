# Python Pydantic v2 — Deep Dive

> **ADK relevance:** Every ADK data structure (Event, Session, EventActions, tool schemas) is a Pydantic model | **Estimated time:** 4-5 hours

## At a Glance

```
+------------------------------------------------------------------+
|              Pydantic v2 Architecture                              |
|                                                                    |
|  BaseModel                                                        |
|    |                                                               |
|    +-- Field()           Constraints, aliases, descriptions       |
|    +-- Validators        @field_validator, @model_validator        |
|    +-- Serialization     model_dump(), model_dump_json()           |
|    +-- Deserialization   model_validate(), model_validate_json()   |
|    +-- model_copy()      Immutable updates (critical for ADK)     |
|    +-- JSON Schema       model_json_schema() -> tool definitions  |
|    +-- ConfigDict        frozen, strict, extra handling           |
|    +-- Generics          Response[T], Page[T]                     |
|    +-- Discriminated     Union[TypeA, TypeB] by field value       |
|       Unions                                                      |
|                                                                    |
|  Java analogy: Lombok @Data + Jackson + Bean Validation in one    |
+------------------------------------------------------------------+
```

Pydantic powers ALL data structures in Google ADK (Event, EventActions, Session, GenerateContentConfig, tool schemas). This guide covers everything from basic model definition through advanced patterns like discriminated unions and JSON schema generation, with Java comparisons throughout.

## BaseModel Fundamentals

#### What is BaseModel?

In Java, you'd use **records** (Java 16+) or **Lombok @Data** to define POJOs with automatic getters, setters, equals, hashCode, and toString. **Pydantic's BaseModel** is similar but goes further: it validates data on construction and provides serialization/deserialization out of the box.

```python
# Java equivalent (Lombok)
# @Data
# public record User {
#     String name;
#     int age;
# }

from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

# Construction with validation
user = User(name="you", age=30)
print(user.name)  # "you"
print(user.age)   # 30

# Accessing as dict (like Java's .asMap() if you had that method)
print(user.model_dump())  # {'name': 'you', 'age': 30}
```

#### Field Types and Python Typing

Python uses type hints instead of Java's explicit types. Here's the mapping:

| Python Type | Java Type | Notes |
|-------------|-----------|-------|
| `str` | `String` | Text |
| `int` | `int` | Integer |
| `float` | `double` | Floating point |
| `bool` | `boolean` | True/False |
| `list[str]` | `List<String>` | List of strings |
| `dict[str, int]` | `Map<String, Integer>` | Key-value pairs |
| `bytes` | `byte[]` | Binary data |
| `datetime` | `LocalDateTime` | Date and time |
| `UUID` | `UUID` | Unique identifier |

```python
from typing import Optional
from datetime import datetime
from uuid import UUID

class Event(BaseModel):
    id: UUID
    name: str
    timestamp: datetime
    metadata: dict[str, int]
    tags: list[str]
    is_critical: bool
    duration_seconds: float

# Pydantic coerces types automatically (lax mode by default)
event = Event(
    id="550e8400-e29b-41d4-a716-446655440000",  # String → UUID
    name="User Login",
    timestamp="2026-03-15T10:30:00",  # String → datetime
    metadata={"retries": 3},
    tags=["auth", "security"],
    is_critical=True,
    duration_seconds=1.5
)
```

#### Optional Fields and Defaults

In Java, you'd use `@Nullable` or Optional. In Pydantic:

```python
from typing import Optional

class User(BaseModel):
    name: str  # Required
    email: str
    phone: Optional[str] = None  # Optional with default None
    age: int = 25  # Optional with default value
    is_admin: bool = False

# Valid constructions
user1 = User(name="you", email="wei@example.com")
user2 = User(name="you", email="wei@example.com", phone="+1-555-0123")
user3 = User(
    name="you",
    email="wei@example.com",
    phone=None,
    age=30,
    is_admin=True
)

# Invalid - missing required field
try:
    user_bad = User(email="wei@example.com")  # Missing 'name'
except Exception as e:
    print(e)  # Validation error
```

> **Field order:** In plain Python dataclasses, required fields after optional fields cause a `TypeError`. Pydantic v2 allows any field order — you can freely mix required and optional fields. This is a Pydantic-specific feature; standard `dataclass` and plain `__init__` still require required parameters before optional ones.

---

## Field() Configuration

Pydantic's `Field()` function gives you fine-grained control over individual fields, similar to Java's validation annotations (`@NotNull`, `@Min`, `@Pattern`, etc.).

#### Basic Field() Usage

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(
        description="Product name",
        min_length=1,
        max_length=100
    )
    price: float = Field(
        description="Price in USD",
        ge=0.0,  # Greater than or equal to
        le=1000000.0  # Less than or equal to
    )
    sku: str = Field(
        description="Stock keeping unit",
        pattern=r"^[A-Z]{3}-\d{6}$"  # Regex pattern
    )
    quantity: int = Field(
        default=0,
        ge=0,
        description="Available quantity"
    )

# Valid
product = Product(
    name="Laptop",
    price=999.99,
    sku="LAP-123456"
)

# Invalid - violates constraints
try:
    bad_product = Product(
        name="",  # Too short
        price=-100,  # Negative price
        sku="invalid"  # Doesn't match pattern
    )
except Exception as e:
    print(f"Validation error: {e}")
```

#### Aliases and Serialization Names

Often you receive data with different field names (e.g., from APIs using snake_case or camelCase):

```python
class User(BaseModel):
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email_address: str = Field(
        alias="emailAddress",
        validation_alias="email"  # Accept during validation only
    )

# Input uses alias names
user = User(
    firstName="you",
    lastName="Doe",
    emailAddress="wei@example.com"
)

# Output uses Python names by default
print(user.model_dump())
# {'first_name': 'you', 'last_name': 'Doe', 'email_address': 'wei@example.com'}

# Output with aliases
print(user.model_dump(by_alias=True))
# {'firstName': 'you', 'lastName': 'Doe', 'emailAddress': 'wei@example.com'}

# JSON input with aliases
json_str = '{"firstName":"you","lastName":"Doe","emailAddress":"wei@example.com"}'
user_from_json = User.model_validate_json(json_str)
```

#### default_factory for Mutable Defaults

This is crucial! In Java, you might initialize collections in constructors. In Python, if you use `= []` as a default, all instances share the same list. Use `default_factory`:

```python
from pydantic import BaseModel, Field
from typing import Optional

class Session(BaseModel):
    user_id: str
    # ✗ WRONG - all sessions share the same list
    # tags: list[str] = []

    # ✓ CORRECT - each session gets its own list
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

# Proof that default_factory works
session1 = Session(user_id="user1")
session2 = Session(user_id="user2")

session1.tags.append("important")
print(session1.tags)  # ['important']
print(session2.tags)  # [] - NOT shared!
```

#### Exclude and Deprecated Fields

```python
class Document(BaseModel):
    title: str
    content: str
    internal_id: str = Field(exclude=True)  # Never serialize
    legacy_format: Optional[str] = Field(
        default=None,
        deprecated=True
    )  # Warn if used

# internal_id won't appear in serialization
doc = Document(
    title="Guide",
    content="...",
    internal_id="doc_12345"
)
print(doc.model_dump())
# {'title': 'Guide', 'content': '...'}
```

---

## Validation

Pydantic validates data **on construction**, automatically catching errors before they propagate. This is more like Java's builder pattern with validation.

> **Re-validation on field assignment:** By default, Pydantic does **not** re-validate when you assign to a field after construction (`model.field = new_value`). To enable re-validation on assignment, add `validate_assignment=True` to your `ConfigDict`:
>
> ```python
> class MyModel(BaseModel):
>     model_config = ConfigDict(validate_assignment=True)
>     value: int
>
> m = MyModel(value=1)
> m.value = "not-an-int"  # raises ValidationError only with validate_assignment=True
> ```
>
> Without it, an invalid assignment silently succeeds. This is a common ADK gotcha when mutating model state after creation.

#### Automatic Validation (Lax vs Strict Mode)

By default, Pydantic is **lenient** and coerces compatible types:

```python
from pydantic import BaseModel, ConfigDict

class Point(BaseModel):
    x: int
    y: int

# Lax mode (default) - string → int
point = Point(x="10", y="20")
print(point.x, point.y)  # 10, 20

# JSON also works
point2 = Point.model_validate_json('{"x":"10","y":"20"}')
print(point2.x)  # 10

# Strict mode - no coercion
class StrictPoint(BaseModel):
    model_config = ConfigDict(strict=True)
    x: int
    y: int

try:
    strict_point = StrictPoint(x="10", y="20")
except Exception as e:
    print(f"Strict mode rejected string: {e}")
```

#### @field_validator

Use `@field_validator` to add custom validation logic (replaces Pydantic v1's `@validator`):

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    username: str
    age: int
    email: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric with underscores")
        return v

    @field_validator("age")
    @classmethod
    def age_range(cls, v):
        if v < 0 or v > 150:
            raise ValueError("Age must be between 0 and 150")
        return v

    @field_validator("email")
    @classmethod
    def email_format(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

# Valid
user = User(username="wei_123", age=30, email="wei@example.com")

# Invalid
try:
    bad_user = User(username="wei-123", age=30, email="wei@example.com")
except Exception as e:
    print(f"Validation failed: {e}")
```

##### Validation Pipeline — Flowchart

```
Raw Input Value
    │
    ▼
┌──────────────────────────┐
│  mode="before" validator │  Runs on raw input before type coercion
│  (pre-processing)        │  e.g., strip whitespace, parse strings
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Core type coercion      │  Pydantic's built-in: str→int, dict→Model, etc.
│  (Pydantic internals)    │  In strict mode, no coercion — must match exactly
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  mode="after" validator  │  Runs on the coerced Python value (default mode)
│  (post-processing)       │  e.g., range checks, business rules
└──────────┬───────────────┘
           │
           ▼
     Validated Value

mode="wrap" wraps the ENTIRE pipeline — your validator calls
handler(v) to invoke core coercion + after validators, with
full control over pre- and post-processing.
```

##### Validation Modes: before, after, wrap

```python
from pydantic import field_validator

class Temperature(BaseModel):
    celsius: float

    # 'before' - validates/transforms raw input before type coercion
    @field_validator("celsius", mode="before")
    @classmethod
    def parse_celsius(cls, v):
        if isinstance(v, str):
            return float(v.strip())
        return v

    # 'after' - validates after type coercion (default)
    @field_validator("celsius", mode="after")
    @classmethod
    def check_range(cls, v):
        if v < -273.15:  # Absolute zero
            raise ValueError("Temperature below absolute zero")
        return v

    # 'wrap' - full control over validation
    @field_validator("celsius", mode="wrap")
    @classmethod
    def wrap_celsius(cls, v, handler, info):
        # Pre-processing
        if isinstance(v, str):
            v = float(v)

        # Call original validator
        result = handler(v)

        # Post-processing
        print(f"Validated celsius: {result}")
        return result

temp = Temperature(celsius="25.5")
```

#### @model_validator

Validate across multiple fields or after all fields are set:

```python
from pydantic import BaseModel, field_validator, model_validator

class DateRange(BaseModel):
    start_date: str
    end_date: str

    @model_validator(mode="after")
    def check_range(self):
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self

# Valid
valid_range = DateRange(start_date="2026-01-01", end_date="2026-12-31")

# Invalid
try:
    invalid_range = DateRange(
        start_date="2026-12-31",
        end_date="2026-01-01"
    )
except Exception as e:
    print(f"Cross-field validation failed: {e}")
```

#### Custom Validation with Annotated Types

For reusable validation constraints:

```python
from typing import Annotated
from pydantic import BaseModel, Field, field_validator

# Define a reusable constraint
PositiveInt = Annotated[int, Field(gt=0)]
ShortString = Annotated[str, Field(max_length=50)]

class Item(BaseModel):
    name: ShortString
    quantity: PositiveInt
    discount: Annotated[float, Field(ge=0, le=1)]

# Works
item = Item(name="Widget", quantity=10, discount=0.15)

# Invalid
try:
    bad_item = Item(name="x" * 100, quantity=-5, discount=1.5)
except Exception as e:
    print(f"Validation failed: {e}")
```

---

## Serialization & Deserialization

Pydantic seamlessly converts between Python objects and JSON/dicts. In Java, you'd use libraries like Jackson or Gson for this.

#### model_dump() and model_dump_json()

```python
from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    name: str
    email: str
    created_at: datetime
    is_active: bool

user = User(
    name="you",
    email="wei@example.com",
    created_at=datetime.now(),
    is_active=True
)

# To Python dict
print(user.model_dump())
# {'name': 'you', 'email': 'wei@example.com', 'created_at': datetime(...), 'is_active': True}

# To JSON string
print(user.model_dump_json(indent=2))
# {
#   "name": "you",
#   "email": "wei@example.com",
#   "created_at": "2026-03-15T...",
#   "is_active": true
# }

# To JSON dict-like (strings as JSON values)
print(user.model_dump_json())
# {"name":"you","email":"wei@example.com","created_at":"2026-03-15T...","is_active":true}
```

#### model_validate() and model_validate_json()

```python
# From dict
user_dict = {
    "name": "you",
    "email": "wei@example.com",
    "created_at": "2026-03-15T10:30:00",
    "is_active": True
}
user = User.model_validate(user_dict)

# From JSON string
json_str = '{"name":"you","email":"wei@example.com","created_at":"2026-03-15T10:30:00","is_active":true}'
user = User.model_validate_json(json_str)

# From JSON with strict mode
try:
    user = User.model_validate_json(
        json_str,
        strict=True  # No type coercion
    )
except Exception as e:
    print(f"Strict validation failed: {e}")
```

#### Include/Exclude Fields

Useful for controlling what gets serialized (e.g., sensitive data):

```python
class User(BaseModel):
    name: str
    email: str
    password_hash: str
    api_key: str

user = User(
    name="you",
    email="wei@example.com",
    password_hash="hashed_password",
    api_key="sk_test_123456"
)

# Exclude sensitive fields
print(user.model_dump(exclude={"password_hash", "api_key"}))
# {'name': 'you', 'email': 'wei@example.com'}

# Include only specific fields
print(user.model_dump(include={"name", "email"}))
# {'name': 'you', 'email': 'wei@example.com'}

# Nested exclusion
print(user.model_dump(exclude={"api_key"}))
```

#### Custom Serializers

For complex serialization logic:

```python
from pydantic import BaseModel, field_serializer
from datetime import datetime

class Event(BaseModel):
    name: str
    timestamp: datetime
    duration_ms: int

    @field_serializer("timestamp")
    def serialize_timestamp(self, value):
        return value.isoformat()

    @field_serializer("duration_ms")
    def serialize_duration(self, value):
        return f"{value}ms"

event = Event(
    name="Login",
    timestamp=datetime.now(),
    duration_ms=1500
)

print(event.model_dump())
# {'name': 'Login', 'timestamp': '2026-03-15T...', 'duration_ms': '1500ms'}
```

#### Model Serializer (Full Control)

For complete serialization control:

```python
from pydantic import BaseModel, model_serializer

class Response(BaseModel):
    status: str
    data: dict

    @model_serializer
    def serialize_model(self):
        return {
            "code": 200 if self.status == "success" else 400,
            "message": self.status,
            "payload": self.data
        }

response = Response(status="success", data={"user_id": 123})
print(response.model_dump())
# {'code': 200, 'message': 'success', 'payload': {'user_id': 123}}
```

---

## model_copy(update={...}) - Critical for ADK

This is arguably the most important pattern in ADK. Instead of mutating objects, you create modified copies. This is similar to Java's builder pattern but more concise.

#### Basic model_copy()

```python
from pydantic import BaseModel

class Context(BaseModel):
    user_id: str
    session_id: str
    request_id: str
    timeout: int = 30

# Original context
context = Context(
    user_id="user_123",
    session_id="sess_456",
    request_id="req_789",
    timeout=30
)

# Create a modified copy (immutable pattern)
child_context = context.model_copy(update={
    "request_id": "req_child_001",
    "timeout": 60
})

print(context.request_id)       # "req_789"
print(child_context.request_id) # "req_child_001"
print(child_context.user_id)    # "user_123" (unchanged)

# Original unchanged
assert context.request_id == "req_789"
assert child_context.request_id == "req_child_001"
```

#### Deep Copy vs Shallow Copy

By default, `model_copy()` creates a **shallow copy**. Nested objects are still references:

```python
from pydantic import BaseModel

class Metadata(BaseModel):
    tags: list[str]
    attributes: dict[str, str]

class Document(BaseModel):
    title: str
    metadata: Metadata

# Original
original = Document(
    title="Guide",
    metadata=Metadata(
        tags=["python", "pydantic"],
        attributes={"author": "you"}
    )
)

# Shallow copy (default)
shallow = original.model_copy()
shallow.metadata.tags.append("adk")

print(original.metadata.tags)  # ['python', 'pydantic', 'adk'] - SHARED!
print(shallow.metadata.tags)   # ['python', 'pydantic', 'adk']

# Deep copy
import copy
original2 = Document(
    title="Guide",
    metadata=Metadata(
        tags=["python", "pydantic"],
        attributes={"author": "you"}
    )
)

deep = original2.model_copy(deep=True)
deep.metadata.tags.append("addk")

print(original2.metadata.tags)  # ['python', 'pydantic'] - NOT shared
print(deep.metadata.tags)       # ['python', 'pydantic', 'addk']
```

#### ADK Pattern: Nested Context

This is how ADK creates child InvocationContexts:

```python
from pydantic import BaseModel
from typing import Optional

class InvocationContext(BaseModel):
    user_id: str
    session_id: str
    request_id: str
    parent_request_id: Optional[str] = None
    depth: int = 0
    custom_metadata: dict[str, str] = Field(default_factory=dict)

    def create_child_context(self, child_request_id: str):
        """Create a child context for nested invocations."""
        return self.model_copy(
            update={
                "request_id": child_request_id,
                "parent_request_id": self.request_id,
                "depth": self.depth + 1,
                "custom_metadata": self.custom_metadata.copy()  # Shallow copy dict
            },
            deep=False
        )

# Root context
root = InvocationContext(
    user_id="user_123",
    session_id="sess_456",
    request_id="req_root",
    custom_metadata={"source": "api"}
)

# Child context
child = root.create_child_context("req_child_001")

print(f"Root depth: {root.depth}, Child depth: {child.depth}")
# Root depth: 0, Child depth: 1

print(f"Root parent: {root.parent_request_id}, Child parent: {child.parent_request_id}")
# Root parent: None, Child parent: req_root

print(f"Root request: {root.request_id}, Child request: {child.request_id}")
# Root request: req_root, Child request: req_child_001
```

---

## Nested Models & Composition

Real-world data is hierarchical. Pydantic handles nested validation gracefully.

#### Basic Nesting

```python
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str
    zipcode: str

class User(BaseModel):
    name: str
    email: str
    address: Address  # Nested model

# Construction - Pydantic auto-converts dicts to models
user = User(
    name="you",
    email="wei@example.com",
    address={
        "street": "123 Main St",
        "city": "San Francisco",
        "zipcode": "94105"
    }
)

print(user.address.city)  # "San Francisco"
print(type(user.address))  # <class '__main__.Address'>

# Or pass Address object directly
user2 = User(
    name="you",
    email="wei@example.com",
    address=Address(
        street="456 Oak Ave",
        city="New York",
        zipcode="10001"
    )
)
```

#### Lists and Dicts of Models

```python
from typing import Optional

class Contact(BaseModel):
    name: str
    phone: str

class Company(BaseModel):
    name: str
    contacts: list[Contact]  # List of models
    departments: dict[str, str]  # Key is dept name, value is manager

# Construction with nested lists
company = Company(
    name="TechCorp",
    contacts=[
        {"name": "you", "phone": "555-0123"},
        {"name": "Alice", "phone": "555-0456"}
    ],
    departments={
        "Engineering": "you",
        "Sales": "Bob"
    }
)

print(company.contacts[0].name)  # "you"
print(len(company.contacts))     # 2
```

#### Optional Nested Models

```python
from typing import Optional

class Profile(BaseModel):
    bio: str
    website: Optional[str] = None

class User(BaseModel):
    name: str
    profile: Optional[Profile] = None

# Valid - no profile
user1 = User(name="you")
print(user1.profile)  # None

# Valid - with profile
user2 = User(
    name="you",
    profile={"bio": "Python developer", "website": "example.com"}
)
print(user2.profile.bio)  # "Python developer"
```

#### Validation Cascades

When nested models fail validation, the error propagates:

```python
class Address(BaseModel):
    street: str
    city: str
    zipcode: str

class User(BaseModel):
    name: str
    address: Address

try:
    user = User(
        name="you",
        address={
            "street": "123 Main St",
            # Missing 'city' and 'zipcode'
        }
    )
except Exception as e:
    print(f"Validation error in nested model: {e}")
    # Shows which fields are missing in Address
```

---

> **Continued in [python-pydantic-advanced.md](python-pydantic-advanced.md)** — discriminated unions, generics, JSON schema generation, ConfigDict, computed fields, inheritance, custom types, performance tips, and ADK-specific patterns.

---

