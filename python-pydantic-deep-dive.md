# Comprehensive Pydantic Deep Dive Guide for Java Developers

**For:** Wei (Java → Python transition, building Google ADK agents)
**Audience:** Experienced Java developers learning Pydantic fundamentals
**Context:** Pydantic powers ALL data structures in Google ADK (Event, EventActions, Session, GenerateContentConfig, tool schemas)

---

## Table of Contents

1. [BaseModel Fundamentals](#basemodel-fundamentals)
2. [Field() Configuration](#field-configuration)
3. [Validation](#validation)
4. [Serialization & Deserialization](#serialization--deserialization)
5. [model_copy(update={...}) - Critical for ADK](#model_copyupdate---critical-for-adk)
6. [Nested Models & Composition](#nested-models--composition)
7. [Discriminated Unions](#discriminated-unions)
8. [Generic Models](#generic-models)
9. [JSON Schema Generation](#json-schema-generation)
10. [ConfigDict](#configdict)
11. [Computed Fields](#computed-fields)
12. [Inheritance](#inheritance)
13. [Custom Types](#custom-types)
14. [Performance Tips](#performance-tips)
15. [ADK-Specific Patterns](#adk-specific-patterns)
16. [Common Pitfalls](#common-pitfalls)
17. [Java → Pydantic Reference](#java--pydantic-reference)

---

## BaseModel Fundamentals

### What is BaseModel?

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
user = User(name="Wei", age=30)
print(user.name)  # "Wei"
print(user.age)   # 30

# Accessing as dict (like Java's .asMap() if you had that method)
print(user.model_dump())  # {'name': 'Wei', 'age': 30}
```

### Field Types and Python Typing

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

### Optional Fields and Defaults

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
user1 = User(name="Wei", email="wei@example.com")
user2 = User(name="Wei", email="wei@example.com", phone="+1-555-0123")
user3 = User(
    name="Wei",
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

### Field Order Matters

Fields without defaults must come before fields with defaults:

```python
# ✓ Correct
class Config(BaseModel):
    name: str  # Required, no default
    timeout: int = 30  # Optional with default

# ✗ Wrong - Python syntax error
# class Config(BaseModel):
#     timeout: int = 30
#     name: str  # Required field after optional field
```

---

## Field() Configuration

Pydantic's `Field()` function gives you fine-grained control over individual fields, similar to Java's validation annotations (`@NotNull`, `@Min`, `@Pattern`, etc.).

### Basic Field() Usage

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

### Aliases and Serialization Names

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
    firstName="Wei",
    lastName="Zheng",
    emailAddress="wei@example.com"
)

# Output uses Python names by default
print(user.model_dump())
# {'first_name': 'Wei', 'last_name': 'Zheng', 'email_address': 'wei@example.com'}

# Output with aliases
print(user.model_dump(by_alias=True))
# {'firstName': 'Wei', 'lastName': 'Zheng', 'emailAddress': 'wei@example.com'}

# JSON input with aliases
json_str = '{"firstName":"Wei","lastName":"Zheng","emailAddress":"wei@example.com"}'
user_from_json = User.model_validate_json(json_str)
```

### default_factory for Mutable Defaults

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

### Exclude and Deprecated Fields

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

### Automatic Validation (Lax vs Strict Mode)

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

### @field_validator

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

#### Validation Modes: before, after, wrap

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

### @model_validator

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

### Custom Validation with Annotated Types

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

### model_dump() and model_dump_json()

```python
from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    name: str
    email: str
    created_at: datetime
    is_active: bool

user = User(
    name="Wei",
    email="wei@example.com",
    created_at=datetime.now(),
    is_active=True
)

# To Python dict
print(user.model_dump())
# {'name': 'Wei', 'email': 'wei@example.com', 'created_at': datetime(...), 'is_active': True}

# To JSON string
print(user.model_dump_json(indent=2))
# {
#   "name": "Wei",
#   "email": "wei@example.com",
#   "created_at": "2026-03-15T...",
#   "is_active": true
# }

# To JSON dict-like (strings as JSON values)
print(user.model_dump_json())
# {"name":"Wei","email":"wei@example.com","created_at":"2026-03-15T...","is_active":true}
```

### model_validate() and model_validate_json()

```python
# From dict
user_dict = {
    "name": "Wei",
    "email": "wei@example.com",
    "created_at": "2026-03-15T10:30:00",
    "is_active": True
}
user = User.model_validate(user_dict)

# From JSON string
json_str = '{"name":"Wei","email":"wei@example.com","created_at":"2026-03-15T10:30:00","is_active":true}'
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

### Include/Exclude Fields

Useful for controlling what gets serialized (e.g., sensitive data):

```python
class User(BaseModel):
    name: str
    email: str
    password_hash: str
    api_key: str

user = User(
    name="Wei",
    email="wei@example.com",
    password_hash="hashed_password",
    api_key="sk_test_123456"
)

# Exclude sensitive fields
print(user.model_dump(exclude={"password_hash", "api_key"}))
# {'name': 'Wei', 'email': 'wei@example.com'}

# Include only specific fields
print(user.model_dump(include={"name", "email"}))
# {'name': 'Wei', 'email': 'wei@example.com'}

# Nested exclusion
print(user.model_dump(exclude={"api_key"}))
```

### Custom Serializers

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

### Model Serializer (Full Control)

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

### Basic model_copy()

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

### Deep Copy vs Shallow Copy

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
        attributes={"author": "Wei"}
    )
)

# Shallow copy (default)
shallow = original.model_copy()
shallow.metadata.tags.append("addk")

print(original.metadata.tags)  # ['python', 'pydantic', 'addk'] - SHARED!
print(shallow.metadata.tags)   # ['python', 'pydantic', 'addk']

# Deep copy
import copy
original2 = Document(
    title="Guide",
    metadata=Metadata(
        tags=["python", "pydantic"],
        attributes={"author": "Wei"}
    )
)

deep = original2.model_copy(deep=True)
deep.metadata.tags.append("addk")

print(original2.metadata.tags)  # ['python', 'pydantic'] - NOT shared
print(deep.metadata.tags)       # ['python', 'pydantic', 'addk']
```

### ADK Pattern: Nested Context

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
    custom_metadata: dict[str, str] = {}

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

### Basic Nesting

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
    name="Wei",
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
    name="Wei",
    email="wei@example.com",
    address=Address(
        street="456 Oak Ave",
        city="New York",
        zipcode="10001"
    )
)
```

### Lists and Dicts of Models

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
        {"name": "Wei", "phone": "555-0123"},
        {"name": "Alice", "phone": "555-0456"}
    ],
    departments={
        "Engineering": "Wei",
        "Sales": "Bob"
    }
)

print(company.contacts[0].name)  # "Wei"
print(len(company.contacts))     # 2
```

### Optional Nested Models

```python
from typing import Optional

class Profile(BaseModel):
    bio: str
    website: Optional[str] = None

class User(BaseModel):
    name: str
    profile: Optional[Profile] = None

# Valid - no profile
user1 = User(name="Wei")
print(user1.profile)  # None

# Valid - with profile
user2 = User(
    name="Wei",
    profile={"bio": "Python developer", "website": "example.com"}
)
print(user2.profile.bio)  # "Python developer"
```

### Validation Cascades

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
        name="Wei",
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

## Discriminated Unions

This is critical for ADK, which uses unions for different event types, tool types, etc. Discriminated unions tell Pydantic which model to use based on a specific field.

### Basic Discriminated Union

Without a discriminator, Pydantic tries each type in order, which is inefficient:

```python
from typing import Union

class CircleEvent(BaseModel):
    event_type: str = "circle"  # Discriminator value
    radius: float

class SquareEvent(BaseModel):
    event_type: str = "square"  # Discriminator value
    side: float

ShapeEvent = Union[CircleEvent, SquareEvent]

# This works but is slow (tries CircleEvent first)
circle = CircleEvent(radius=5.0)
```

### With Field(discriminator=...)

Use Annotated with discriminator for efficient routing:

```python
from typing import Annotated, Union, Literal
from pydantic import BaseModel, Field

class CircleEvent(BaseModel):
    event_type: Literal["circle"]  # Exact type
    radius: float

class SquareEvent(BaseModel):
    event_type: Literal["square"]  # Exact type
    side: float

class TriangleEvent(BaseModel):
    event_type: Literal["triangle"]
    side_a: float
    side_b: float
    side_c: float

# Discriminated union
ShapeEvent = Annotated[
    Union[CircleEvent, SquareEvent, TriangleEvent],
    Field(discriminator="event_type")
]

class ShapeProcessor(BaseModel):
    event: ShapeEvent

# Pydantic automatically routes based on event_type
processor1 = ShapeProcessor(
    event={"event_type": "circle", "radius": 5.0}
)
print(type(processor1.event))  # <class '__main__.CircleEvent'>

processor2 = ShapeProcessor(
    event={"event_type": "triangle", "side_a": 3, "side_b": 4, "side_c": 5}
)
print(type(processor2.event))  # <class '__main__.TriangleEvent'>
```

### ADK Pattern: Tool Union

How ADK likely defines different tool types:

```python
from typing import Annotated, Union, Literal
from pydantic import BaseModel, Field

class FunctionTool(BaseModel):
    type: Literal["function"]
    name: str
    description: str
    parameters: dict

class SearchTool(BaseModel):
    type: Literal["search"]
    name: str
    query_template: str

class ApiTool(BaseModel):
    type: Literal["api"]
    name: str
    endpoint: str
    method: str

Tool = Annotated[
    Union[FunctionTool, SearchTool, ApiTool],
    Field(discriminator="type")
]

class ToolRegistry(BaseModel):
    tools: list[Tool]

# Mix different tool types
registry = ToolRegistry(
    tools=[
        {"type": "function", "name": "add", "description": "Add two numbers", "parameters": {}},
        {"type": "search", "name": "google", "query_template": "q={query}"},
        {"type": "api", "name": "weather", "endpoint": "https://api.weather.com", "method": "GET"}
    ]
)

# Access as specific types
for tool in registry.tools:
    if isinstance(tool, FunctionTool):
        print(f"Function: {tool.name}")
    elif isinstance(tool, SearchTool):
        print(f"Search: {tool.name}")
```

---

## Generic Models

Create reusable model templates that work with any type. Like Java generics but for models.

### Basic Generic Model

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")  # Type variable

class Response(BaseModel, Generic[T]):
    """A generic response wrapper."""
    status: str
    data: T
    error: Optional[str] = None

# Concrete types
class UserResponse(Response[dict]):
    pass

class ListResponse(Response[list]):
    pass

# Usage
user_response = UserResponse(
    status="success",
    data={"user_id": 123, "name": "Wei"}
)

list_response = ListResponse(
    status="success",
    data=[1, 2, 3, 4, 5]
)

print(user_response.data)  # {'user_id': 123, 'name': 'Wei'}
print(list_response.data)  # [1, 2, 3, 4, 5]
```

### Generic with Nested Models

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: list[T]
    page_number: int
    total_items: int

class User(BaseModel):
    id: int
    name: str
    email: str

# Use with User
user_page = Page[User](
    items=[
        {"id": 1, "name": "Wei", "email": "wei@example.com"},
        {"id": 2, "name": "Alice", "email": "alice@example.com"}
    ],
    page_number=1,
    total_items=100
)

print(user_page.items[0].name)  # "Wei"
print(type(user_page.items[0]))  # <class '__main__.User'>
```

### TypeAdapter for Generic Validation

Sometimes you need to validate generic types directly without a model:

```python
from pydantic import TypeAdapter
from typing import Generic, TypeVar

T = TypeVar("T")

# Validate list of dicts
list_adapter = TypeAdapter(list[dict[str, int]])
data = [{"a": 1, "b": 2}, {"c": 3}]
validated = list_adapter.validate_python(data)

# Validate dict with string keys and int values
dict_adapter = TypeAdapter(dict[str, int])
validated_dict = dict_adapter.validate_python({"x": 10, "y": 20})
```

---

## JSON Schema Generation

This is HOW ADK auto-generates tool definitions! Pydantic converts type hints to JSON Schema that LLMs understand.

### Basic JSON Schema

```python
from pydantic import BaseModel, Field
import json

class Calculator(BaseModel):
    """A simple calculator function."""
    operation: str = Field(
        description="Mathematical operation: add, subtract, multiply, divide"
    )
    a: float = Field(description="First operand")
    b: float = Field(description="Second operand")

# Generate schema
schema = Calculator.model_json_schema()
print(json.dumps(schema, indent=2))

# Output:
# {
#   "properties": {
#     "operation": {
#       "description": "Mathematical operation: ...",
#       "type": "string"
#     },
#     "a": {
#       "description": "First operand",
#       "type": "number"
#     },
#     "b": {
#       "description": "Second operand",
#       "type": "number"
#     }
#   },
#   "required": ["operation", "a", "b"],
#   "type": "object"
#   "title": "Calculator"
# }
```

### Schema with Constraints

Field constraints become JSON Schema constraints:

```python
from pydantic import BaseModel, Field
import json

class Product(BaseModel):
    """A product with constraints."""
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0, le=1000000)
    quantity: int = Field(ge=0, description="Stock level")
    tags: list[str] = Field(
        min_length=1,
        max_length=10,
        description="Product tags"
    )

schema = Product.model_json_schema()
print(json.dumps(schema, indent=2))

# Output shows constraints:
# "name": {
#   "type": "string",
#   "minLength": 1,
#   "maxLength": 100
# },
# "price": {
#   "type": "number",
#   "minimum": 0,
#   "maximum": 1000000
# }
```

### Schema with Enums

```python
from enum import Enum
from pydantic import BaseModel, Field
import json

class Status(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

class Task(BaseModel):
    """A task with enum status."""
    title: str
    status: Status = Field(description="Task status")

schema = Task.model_json_schema()
print(json.dumps(schema, indent=2))

# Shows enum values:
# "status": {
#   "enum": ["pending", "active", "completed"],
#   "type": "string",
#   "description": "Task status"
# }
```

### ADK Pattern: Tool Schema Generation

How ADK generates tool definitions:

```python
from pydantic import BaseModel, Field
import json

class SearchToolDefinition(BaseModel):
    """Definition of a search tool."""
    type: str = "function"
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")

class SearchToolInput(BaseModel):
    """Input parameters for search."""
    query: str = Field(
        description="Search query",
        min_length=1,
        max_length=500
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max results"
    )
    language: str = Field(
        default="en",
        description="Result language"
    )

# Generate schema for tool input
tool_def = SearchToolDefinition(
    name="search",
    description="Search the web"
)

# This is what gets sent to the LLM
input_schema = SearchToolInput.model_json_schema()
print(json.dumps({
    **tool_def.model_dump(),
    "parameters": input_schema
}, indent=2))

# LLM sees:
# {
#   "type": "function",
#   "name": "search",
#   "description": "Search the web",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "query": {...},
#       "limit": {...},
#       "language": {...}
#     },
#     "required": ["query"]
#   }
# }
```

---

## ConfigDict

Global configuration for a model, like Java's @Configuration annotations.

### Common ConfigDict Options

```python
from pydantic import BaseModel, ConfigDict

class ImmutableUser(BaseModel):
    """Immutable user (frozen)."""
    model_config = ConfigDict(frozen=True)
    name: str
    age: int

# Cannot modify
user = ImmutableUser(name="Wei", age=30)
try:
    user.name = "Alice"  # Error
except Exception as e:
    print(f"Cannot modify frozen model: {e}")

# But model_copy works
user2 = user.model_copy(update={"name": "Alice"})
```

### Validation Configuration

```python
from pydantic import BaseModel, ConfigDict, field_validator

class StrictConfig(BaseModel):
    """Strict validation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Strip leading/trailing whitespace
        strict=True  # No type coercion
    )
    name: str

# Whitespace stripped automatically
user = StrictConfig(name="  Wei  ")
print(f"'{user.name}'")  # 'Wei' (stripped)

# Strict mode - no coercion
try:
    bad = StrictConfig(name=123)  # Error - no int to str coercion
except Exception as e:
    print(f"Strict mode rejected: {e}")
```

### Allow Arbitrary Types

For fields with types Pydantic doesn't understand by default:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone

class EventWithTimezone(BaseModel):
    """Allow arbitrary types like timezone objects."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    timezone: timezone

event = EventWithTimezone(
    name="Meeting",
    timezone=timezone.utc
)
print(event.timezone)  # UTC
```

### Populate by Name

Allow both field names and aliases:

```python
from pydantic import BaseModel, Field, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")

# Both work
user1 = User(firstName="Wei", lastName="Zheng")
user2 = User(first_name="Wei", last_name="Zheng")  # Field name also works

print(user1.first_name)  # "Wei"
print(user2.first_name)  # "Wei"
```

### Extra Fields Handling

Control what happens with unknown fields:

```python
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    """Forbid extra fields."""
    model_config = ConfigDict(extra="forbid")
    name: str

try:
    bad = StrictModel(name="Wei", age=30)  # 'age' is extra
except Exception as e:
    print(f"Extra field rejected: {e}")

class FlexibleModel(BaseModel):
    """Allow and ignore extra fields."""
    model_config = ConfigDict(extra="ignore")
    name: str

flexible = FlexibleModel(name="Wei", age=30)
print(flexible.model_dump())  # {'name': 'Wei'} - age ignored

class AllowExtraModel(BaseModel):
    """Allow extra fields."""
    model_config = ConfigDict(extra="allow")
    name: str

allow_extra = AllowExtraModel(name="Wei", age=30)
print(allow_extra.model_dump())  # {'name': 'Wei', 'age': 30}
```

---

## Computed Fields

Fields that are derived from other fields and appear in serialization, but aren't stored.

### Basic Computed Field

```python
from pydantic import BaseModel, computed_field

class User(BaseModel):
    first_name: str
    last_name: str

    @computed_field  # Not stored, computed on access
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

user = User(first_name="Wei", last_name="Zheng")
print(user.full_name)  # "Wei Zheng"

# Shows in serialization
print(user.model_dump())
# {'first_name': 'Wei', 'last_name': 'Zheng', 'full_name': 'Wei Zheng'}
```

### Computed Field with Complex Logic

```python
from pydantic import BaseModel, computed_field
from datetime import datetime, timedelta

class Subscription(BaseModel):
    start_date: datetime
    duration_days: int

    @computed_field
    @property
    def end_date(self) -> datetime:
        return self.start_date + timedelta(days=self.duration_days)

    @computed_field
    @property
    def is_active(self) -> bool:
        return datetime.now() < self.end_date

subscription = Subscription(
    start_date=datetime.now(),
    duration_days=30
)

print(subscription.end_date)  # 30 days from now
print(subscription.is_active)  # True
```

---

## Inheritance

Reuse model structure through inheritance, like Java class hierarchies.

### Basic Inheritance

```python
from pydantic import BaseModel, Field

class Animal(BaseModel):
    """Base animal model."""
    name: str
    age: int

class Dog(Animal):
    """Dog extends Animal."""
    breed: str
    good_boy: bool = True

class Cat(Animal):
    """Cat extends Animal."""
    indoor: bool
    lives_remaining: int = 9

# Dog gets name and age from Animal
dog = Dog(name="Buddy", age=5, breed="Golden Retriever")
print(dog.name)  # "Buddy"
print(dog.breed)  # "Golden Retriever"

cat = Cat(name="Whiskers", age=3, indoor=True)
print(cat.name)  # "Whiskers"
print(cat.lives_remaining)  # 9
```

### Overriding Fields

```python
from pydantic import BaseModel, Field

class Vehicle(BaseModel):
    brand: str
    color: str = "white"

class Car(Vehicle):
    color: str = "blue"  # Override default
    doors: int = 4

car = Car(brand="Toyota")
print(car.color)  # "blue" (not "white")
```

### Multiple Inheritance

```python
from pydantic import BaseModel

class TimestampMixin(BaseModel):
    created_at: str
    updated_at: str

class AuthorMixin(BaseModel):
    author: str
    reviewer: str

class Document(TimestampMixin, AuthorMixin):
    """Document with timestamps and authors."""
    title: str
    content: str

doc = Document(
    title="Guide",
    content="...",
    created_at="2026-03-15",
    updated_at="2026-03-15",
    author="Wei",
    reviewer="Alice"
)
```

---

## Custom Types

Create custom types that Pydantic validates correctly.

### Using __get_pydantic_core_schema__

For custom validation of non-standard types:

```python
from pydantic import BaseModel
from pydantic_core import core_schema
from typing import Annotated

class UppercaseString:
    """A string that's always uppercase."""
    def __init__(self, value: str):
        self.value = value.upper()

    def __str__(self):
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        python_schema = core_schema.no_info_plain_validator_function(
            lambda v: cls(v) if isinstance(v, str) else v
        )
        return python_schema

class User(BaseModel):
    name: UppercaseString
    code: Annotated[UppercaseString, core_schema.no_info_plain_validator_function(
        lambda v: UppercaseString(v)
    )]

user = User(name="wei", code="abc")
print(user.name.value)  # "WEI"
print(user.code.value)  # "ABC"
```

### Using Annotated for Simple Custom Validation

```python
from typing import Annotated
from pydantic import BaseModel, Field, PlainValidator

def validate_phone(v: str) -> str:
    # Remove non-digits
    digits = ''.join(c for c in v if c.isdigit())
    if len(digits) != 10:
        raise ValueError("Phone must have 10 digits")
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

PhoneNumber = Annotated[str, PlainValidator(validate_phone)]

class Contact(BaseModel):
    phone: PhoneNumber

contact = Contact(phone="5550123456")
print(contact.phone)  # "(555) 012-3456"
```

---

## Performance Tips

### model_construct() - Skip Validation

For performance-critical code where you know data is valid:

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

# Normal construction (validates)
user = User(name="Wei", age=30)

# Bypass validation (DANGEROUS - use carefully)
user_fast = User.model_construct(name="Wei", age=30)

# Both work, but model_construct is faster for trusted data
print(user_fast.name)  # "Wei"
```

### TypeAdapter for Bulk Validation

Validate many items efficiently:

```python
from pydantic import TypeAdapter

class User(BaseModel):
    name: str
    age: int

# Create adapter once
adapter = TypeAdapter(list[User])

# Validate many items
data = [
    {"name": "Wei", "age": 30},
    {"name": "Alice", "age": 28},
    {"name": "Bob", "age": 35}
]

users = adapter.validate_python(data)
print(len(users))  # 3
print(users[0].name)  # "Wei"
```

### Dataclasses vs Pydantic

Use dataclasses when you don't need validation:

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

# Faster construction, no validation
point = Point(x=10, y=20)

# But no JSON serialization
# print(point.model_dump_json())  # Error
```

---

## ADK-Specific Patterns

### Modeling Events

```python
from typing import Annotated, Union, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Event types
class UserLoginEvent(BaseModel):
    event_type: Literal["user_login"]
    user_id: str
    timestamp: datetime
    ip_address: str

class UserLogoutEvent(BaseModel):
    event_type: Literal["user_logout"]
    user_id: str
    timestamp: datetime
    session_duration: int  # seconds

class ErrorEvent(BaseModel):
    event_type: Literal["error"]
    timestamp: datetime
    error_code: int
    error_message: str
    user_id: Optional[str] = None

# Discriminated union
Event = Annotated[
    Union[UserLoginEvent, UserLogoutEvent, ErrorEvent],
    Field(discriminator="event_type")
]

class EventLog(BaseModel):
    events: list[Event]

# Use
log = EventLog(
    events=[
        {
            "event_type": "user_login",
            "user_id": "user_123",
            "timestamp": "2026-03-15T10:00:00",
            "ip_address": "192.168.1.1"
        },
        {
            "event_type": "user_logout",
            "user_id": "user_123",
            "timestamp": "2026-03-15T11:00:00",
            "session_duration": 3600
        }
    ]
)

for event in log.events:
    if isinstance(event, UserLoginEvent):
        print(f"User {event.user_id} logged in from {event.ip_address}")
```

### Modeling Sessions

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SessionMetadata(BaseModel):
    """Session metadata."""
    browser: str
    os: str
    language: str

class Session(BaseModel):
    """User session."""
    session_id: str = Field(description="Unique session ID")
    user_id: str = Field(description="User ID")
    created_at: datetime
    last_activity: datetime
    metadata: SessionMetadata
    is_active: bool = True

    def mark_inactive(self) -> "Session":
        """Create inactive copy."""
        return self.model_copy(update={"is_active": False})

session = Session(
    session_id="sess_123",
    user_id="user_456",
    created_at=datetime.now(),
    last_activity=datetime.now(),
    metadata=SessionMetadata(
        browser="Chrome",
        os="macOS",
        language="en"
    )
)

inactive = session.mark_inactive()
print(session.is_active)      # True
print(inactive.is_active)     # False
print(session.session_id)     # "sess_123" (unchanged)
```

### Modeling Tool Definitions

```python
from pydantic import BaseModel, Field
from typing import Any, Optional
import json

class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type (string, number, boolean, etc)")
    description: str = Field(description="Parameter description")
    required: bool = False
    default: Optional[Any] = None

class ToolDefinition(BaseModel):
    """Definition of a callable tool."""
    name: str = Field(
        description="Tool name",
        min_length=1,
        max_length=100
    )
    description: str = Field(
        description="Tool description",
        min_length=10
    )
    parameters: list[ToolParameter] = Field(
        default_factory=list,
        description="Tool parameters"
    )

    def to_openai_format(self) -> dict:
        """Convert to OpenAI function schema."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

# Create tool definition
calculator = ToolDefinition(
    name="calculate",
    description="Perform basic arithmetic operations",
    parameters=[
        ToolParameter(
            name="operation",
            type="string",
            description="Operation (add, subtract, multiply, divide)",
            required=True
        ),
        ToolParameter(
            name="a",
            type="number",
            description="First operand",
            required=True
        ),
        ToolParameter(
            name="b",
            type="number",
            description="Second operand",
            required=True
        )
    ]
)

print(json.dumps(calculator.to_openai_format(), indent=2))
```

### Modeling Agent Configuration

```python
from pydantic import BaseModel, Field
from typing import Optional, dict, list
from enum import Enum

class ModelProvider(str, Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class GenerateContentConfig(BaseModel):
    """Configuration for content generation."""
    model: str = Field(
        description="Model ID (e.g., 'gemini-pro')"
    )
    provider: ModelProvider = Field(
        default=ModelProvider.GOOGLE,
        description="Model provider"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=32000,
        description="Maximum tokens in response"
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    system_prompt: Optional[str] = None

class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str = Field(description="Agent name")
    description: str = Field(description="Agent description")
    generate_config: GenerateContentConfig = Field(
        description="Content generation config"
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Available tool names"
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        description="Maximum iterations"
    )
    retry_policy: dict[str, int] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff_ms": 1000},
        description="Retry configuration"
    )

# Create config
agent_config = AgentConfig(
    name="research_agent",
    description="Agent for research tasks",
    generate_config=GenerateContentConfig(
        model="gemini-pro",
        provider=ModelProvider.GOOGLE,
        temperature=0.5
    ),
    tools=["search", "browse", "summarize"],
    max_iterations=20
)

print(agent_config.model_dump_json(indent=2))
```

### Mini Project: Complete ADK-like System

```python
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Union, Literal, Optional
from datetime import datetime
import json

# ============ Core Types ============

class ToolInput(BaseModel):
    """Input to a tool."""
    tool_name: str
    arguments: dict

class ToolResult(BaseModel):
    """Result from a tool."""
    success: bool
    output: str
    error: Optional[str] = None

# ============ Actions ============

class TextAction(BaseModel):
    action_type: Literal["text"]
    content: str

class ToolCallAction(BaseModel):
    action_type: Literal["tool_call"]
    tool_input: ToolInput

Action = Annotated[
    Union[TextAction, ToolCallAction],
    Field(discriminator="action_type")
]

# ============ Context ============

class InvocationContext(BaseModel):
    """Context for agent invocation."""
    request_id: str
    user_id: str
    session_id: str
    parent_request_id: Optional[str] = None
    depth: int = 0

    def create_child_context(self, tool_name: str) -> "InvocationContext":
        """Create child context for tool invocation."""
        return self.model_copy(
            update={
                "request_id": f"{self.request_id}_{tool_name}",
                "parent_request_id": self.request_id,
                "depth": self.depth + 1
            }
        )

# ============ Agent Response ============

class AgentResponse(BaseModel):
    """Response from agent."""
    status: Literal["success", "failed", "partial"]
    actions: list[Action]
    context: InvocationContext

    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return any(
            isinstance(a, ToolCallAction)
            for a in self.actions
        )

# ============ Usage ============

def example_adk_flow():
    # Create root context
    root_context = InvocationContext(
        request_id="req_001",
        user_id="user_123",
        session_id="sess_456"
    )

    # Agent takes action
    response = AgentResponse(
        status="success",
        actions=[
            TextAction(action_type="text", content="I'll search for information"),
            ToolCallAction(
                action_type="tool_call",
                tool_input=ToolInput(
                    tool_name="search",
                    arguments={"query": "Pydantic Python"}
                )
            )
        ],
        context=root_context
    )

    print(json.dumps(response.model_dump(), indent=2, default=str))

    # Process tool calls
    if response.has_tool_calls():
        for action in response.actions:
            if isinstance(action, ToolCallAction):
                # Create child context for tool
                child_context = response.context.create_child_context(
                    action.tool_input.tool_name
                )
                print(f"\nTool call context depth: {child_context.depth}")
                print(f"Child request ID: {child_context.request_id}")

example_adk_flow()
```

---

## Common Pitfalls

### 1. Mutable Default Values

**WRONG:**

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    tags: list[str] = []  # WRONG! Shared across instances

user1 = User(name="Wei")
user2 = User(name="Alice")

user1.tags.append("admin")
print(user1.tags)  # ['admin']
print(user2.tags)  # ['admin'] - WRONG! Shared!
```

**RIGHT:**

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)  # Each instance gets its own

user1 = User(name="Wei")
user2 = User(name="Alice")

user1.tags.append("admin")
print(user1.tags)  # ['admin']
print(user2.tags)  # [] - Correct! Not shared
```

### 2. Forgetting model_copy

**WRONG:**

```python
context = InvocationContext(request_id="req_1", user_id="user_1", session_id="sess_1")
context.depth += 1  # Modifies original!
# Now context.depth = 1
```

**RIGHT:**

```python
context = InvocationContext(request_id="req_1", user_id="user_1", session_id="sess_1")
child = context.model_copy(update={"depth": context.depth + 1})
# context.depth = 0 (unchanged)
# child.depth = 1 (new)
```

### 3. Validation Errors in Nested Models

When nested model validation fails, the error shows the full path:

```python
class Address(BaseModel):
    zipcode: str

class User(BaseModel):
    name: str
    address: Address

try:
    user = User(
        name="Wei",
        address={"zipcode": 123}  # Invalid: should be string
    )
except Exception as e:
    print(e)
    # Error shows: address.zipcode (value should be a valid string)
```

### 4. Circular References

Models can reference each other, but you need forward references:

```python
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    parent: Optional["User"] = None  # Forward reference (string)

# Now it works
user1 = User(name="Parent")
user2 = User(name="Child", parent={"name": "Parent"})

# Update forward references
User.model_rebuild()
```

### 5. JSON Schema Not Including Constraints

If you're generating JSON schema for tools, make sure to add Field descriptions:

```python
# WRONG - No description in schema
class Calculator(BaseModel):
    a: int
    b: int

# RIGHT - Descriptions appear in schema
class Calculator(BaseModel):
    a: int = Field(description="First number")
    b: int = Field(description="Second number")

# LLM sees descriptions in schema
print(Calculator.model_json_schema())
```

### 6. Using Mutable Types as Defaults

```python
# WRONG
class Config(BaseModel):
    metadata: dict = {}  # Shared!

# RIGHT
class Config(BaseModel):
    metadata: dict = Field(default_factory=dict)  # Each instance gets its own

# Or Optional
class Config(BaseModel):
    metadata: Optional[dict] = None
```

### 7. Forgetting to Import Field

```python
# WRONG
from pydantic import BaseModel

class User(BaseModel):
    age: int = Field(ge=0)  # NameError: Field not defined

# RIGHT
from pydantic import BaseModel, Field

class User(BaseModel):
    age: int = Field(ge=0)
```

### 8. Type Hints Are Not Enforced at Runtime

```python
# Pydantic validates on construction
user = User(name="Wei", age=30)  # Valid

# But direct assignment doesn't validate
user.age = "not an int"  # No error!
print(user.age)  # "not an int"

# To prevent this, use frozen
class ImmutableUser(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    age: int

immutable = ImmutableUser(name="Wei", age=30)
immutable.age = 31  # Error: frozen model
```

---

## Java → Pydantic Reference

| Java | Pydantic | Notes |
|------|----------|-------|
| `public record User { String name; int age; }` | `class User(BaseModel): name: str; age: int` | Simple data class |
| `@Data @Lombok` | `class User(BaseModel)` | Automatic getters/setters |
| `@Nullable` | `Optional[T]` or `T = None` | Optional field |
| `@NotNull` | Required field (no default) | Field is required |
| `@Min(0)` | `Field(ge=0)` | Greater than or equal |
| `@Max(100)` | `Field(le=100)` | Less than or equal |
| `@Length(min=1, max=100)` | `Field(min_length=1, max_length=100)` | String length |
| `@Pattern("regex")` | `Field(pattern="regex")` | Regex validation |
| `@Valid` | Automatic for nested models | Nested validation |
| `@JsonAlias("firstName")` | `Field(alias="firstName")` | JSON field alias |
| `@JsonIgnore` | `Field(exclude=True)` | Exclude from serialization |
| `@Deprecated` | `Field(deprecated=True)` | Mark as deprecated |
| `@JsonProperty` | `Field(alias="...")` | Rename in JSON |
| `.toBuilder()` | `.model_copy(update={...})` | Create modified copy |
| `.equals()` | Automatic via BaseModel | Equality comparison |
| `.toString()` | Automatic via BaseModel | String representation |
| Jackson ObjectMapper | `model_dump_json()` / `model_validate_json()` | JSON serialization |
| Custom JsonSerializer | `@field_serializer` | Custom serialization |
| Custom JsonDeserializer | `@field_validator` | Custom deserialization |
| Sealed class + discriminator | `Union` + `Field(discriminator=...)` | Discriminated union |
| `List<User>` | `list[User]` | List of models |
| `Map<String, Integer>` | `dict[str, int]` | Dictionary type |
| `@Configuration` | `ConfigDict` | Model configuration |
| `@Transactional` | Not applicable | Pydantic is not ORM |
| Custom Validator | `@field_validator` | Custom validation |
| Builder pattern | `.model_copy(update={...})` | Immutable updates |

---

## Summary

**Key Takeaways for Wei:**

1. **BaseModel is your foundation** - Replace Java records/Lombok @Data with Pydantic BaseModel
2. **Validation happens on construction** - This is different from Java; you get errors early
3. **Field() is your friend** - Use it for constraints, aliases, and validation
4. **model_copy(update={...}) is critical in ADK** - Don't mutate, create copies
5. **Discriminated unions handle type variants** - Better than Java's sealed classes for JSON
6. **JSON schema generation is automatic** - model_json_schema() powers tool definitions
7. **Nested models validate automatically** - Validation cascades through composition
8. **Always use default_factory for mutable defaults** - Avoid the shared list trap
9. **Frozen models prevent mutations** - Use ConfigDict(frozen=True) when you need immutability
10. **Type hints are the schema** - Your Python types directly become JSON schemas for LLMs

**ADK-Specific Patterns:**

- Events are discriminated unions (`Annotated[Union[...], Field(discriminator="event_type")]`)
- Contexts use `model_copy(update={...})` to create child contexts
- Tool definitions generate JSON schemas automatically
- Sessions are immutable copies of each other
- Validation is declarative, not imperative

---

*Part of the Python for ADK learning series — March 2026*
