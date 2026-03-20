# ADK Onboarding Guide — From Zero to Your First Multi-Agent System

For new team members. No ADK knowledge assumed.

---

## 1. The Big Picture: What ADK Does

ADK (Agent Development Kit) is Google's Python framework for building **multi-agent AI systems**. a runtime that connects LLMs, tools, and conversation state into a coherent pipeline.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ What You Build with ADK │
│ │
│ User: "Book a flight to Tokyo and find a hotel" │
│ │ │
│ ▼ │
│ ┌───────────┐ ┌────────────────┐ ┌─────────────────┐ │
│ │ Runner │───▶│ Root Agent │───▶│ Flight Agent │ │
│ │ (engine) │ │ (dispatcher) │ │ (specialist) │ │
│ └───────────┘ │ │ │ tools: [ │ │
│ │ │ Decides which │ │ search_flights │ │
│ │ │ agent handles │ │ book_flight │ │
│ │ │ each part │ │ ] │ │
│ │ │ │ └─────────────────┘ │
│ │ │ │ ┌─────────────────┐ │
│ │ │ │───▶│ Hotel Agent │ │
│ │ └────────────────┘ │ (specialist) │ │
│ │ │ tools: [ │ │
│ ▼ │ search_hotels │ │
│ ┌───────────┐ │ book_hotel │ │
│ │ Session │ │ ] │ │
│ │ (memory) │ └─────────────────┘ │
│ └───────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts in 5 Minutes

Six building blocks:

```
┌──────────────────────────────────────────────────────────────────┐
│ ADK Architecture Layers │
│ │
│ ┌──────────┐ │
│ │ Runner │ ← Orchestrator: receives user message, │
│ └─────┬────┘ manages session, calls agent │
│ │ │
│ ┌─────▼────┐ │
│ │ Agent │ ← Blueprint: defines behavior (instruction, │
│ └─────┬────┘ model, tools, sub-agents) │
│ │ │
│ ┌─────▼────┐ │
│ │ Flow │ ← Reason-Act loop: sends prompt to LLM, │
│ └─────┬────┘ processes response, calls tools, repeats │
│ │ │
│ ┌─────▼────┐ │
│ │ Model │ ← LLM adapter: Gemini, Claude, GPT, etc. │
│ └──────────┘ │
│ │
│ ┌──────────┐ ┌──────────┐ │
│ │ Session │ │ Tools │ ← State storage + capabilities │
│ └──────────┘ └──────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

| Concept | What It Is | Java Analogy |
|---------|-----------|--------------|
| **Agent** | Blueprint for AI behavior | A `@Service` class with configuration |
| **Runner** | Stateless orchestrator | A `@Controller` that processes requests |
| **Flow** | LLM reason-act loop | A `while` loop calling an API |
| **Model** | LLM adapter | A `RestTemplate` for different AI APIs |
| **Session** | Conversation history + state | An HTTP session + cache |
| **Tool** | Capability the LLM can invoke | A `@RequestMapping` endpoint |
| **Event** | Data flowing through every layer | A domain event / message |

---

## 3. Your First Agent (5 Lines)

```python
from google.adk import Agent

root_agent = Agent(
    model="gemini-2.5-flash",
    name="greeter",
    instruction="You are a friendly assistant. Greet users warmly.",
)
```

```
User message: "Hi!"
 │
 ▼
┌─────────────┐ ┌────────────┐ ┌────────────┐
│ Runner │───▶│ greeter │───▶│ Gemini │
│ │ │ Agent │ │ 2.5 Flash │
│ 1. Load │ │ │ │ │
│ session │ │ instruction│ │ "You are │
│ 2. Build │ │ = "You are │ │ friendly │
│ context │ │ friendly │ │ ..." │
│ 3. Call │ │ ..." │ │ │
│ agent │ └────────────┘ └─────┬──────┘
│ 4. Stream │ │
│ events │◀───────────────────────────┘
│ 5. Save │ Event: "Hello! Welcome!"
│ session │
└─────────────┘
 │
 ▼
Response: "Hello! Welcome! How can I help you today?"
```

---

## 4. Adding Tools (Making Your Agent Useful)

```python
from google.adk import Agent

def get_weather(city: str) -> str:
    """Get current weather for a city."""
    # Call weather API
    weather_data = {
        "Tokyo": "☀️ 22°C, clear skies",
        "London": "🌧️ 14°C, light rain",
        "New York": "⛅ 18°C, partly cloudy",
    }
    return weather_data.get(city, f"Weather data not available for {city}")

def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    import ast
    try:
        result = eval(compile(ast.parse(expression, mode='eval'), '', 'eval'))
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"

root_agent = Agent(
    model="gemini-2.5-flash",
    name="helpful_assistant",
    instruction="You help users with weather info and calculations.",
    tools=[get_weather, calculate],
)
```

```
User: "What's the weather in Tokyo and what's 15 * 7?"
 │
 ▼
┌─────────────────────────────────────────────────────────────┐
│ Reason-Act Loop │
│ │
│ Iteration 1: │
│ ┌─────────┐ ┌──────────────────────────────────┐ │
│ │ LLM │────▶│ "I need weather + calculation" │ │
│ │ thinks │ │ Call: get_weather("Tokyo") │ │
│ └─────────┘ │ Call: calculate("15 * 7") │ │
│ └──────────┬───────────────────────┘ │
│ │ │
│ ▼ │
│ ┌──────────────────────────────────────────────────┐ │
│ │ Tool Execution │ │
│ │ get_weather("Tokyo") → "☀️ 22°C, clear skies" │ │
│ │ calculate("15 * 7") → "Result: 105" │ │
│ └──────────────────────────┬───────────────────────┘ │
│ │ │
│ ▼ │
│ Iteration 2: │
│ ┌─────────┐ ┌──────────────────────────────────┐ │
│ │ LLM │────▶│ "I have both answers, respond" │ │
│ │ thinks │ │ Final text response │ │
│ └─────────┘ └──────────────────────────────────┘ │
│ │
└─────────────────────────────────────────────────────────────┘
 │
 ▼
"The weather in Tokyo is ☀️ 22°C with clear skies. And 15 × 7 = 105."
```

---

## 5. Using ToolContext (Accessing State and Services)

`ToolContext` gives tools access to session state, artifacts, and services:

```python
from google.adk.tools.tool_context import ToolContext

def add_to_cart(item: str, quantity: int, tool_context: ToolContext) -> str:
    """Add an item to the shopping cart."""
    # Read current cart from session state
    cart = tool_context.state.get("cart", [])
    cart.append({"item": item, "qty": quantity})

    # Write updated cart back to session state
    tool_context.state["cart"] = cart

    return f"Added {quantity}x {item} to cart. Cart now has {len(cart)} items."

def view_cart(tool_context: ToolContext) -> str:
    """View current shopping cart contents."""
    cart = tool_context.state.get("cart", [])
    if not cart:
        return "Your cart is empty."
    lines = [f"- {item['qty']}x {item['item']}" for item in cart]
    return "Your cart:\n" + "\n".join(lines)
```

```
┌──────────────────────────────────────────────────────────────┐
│ ToolContext Data Flow │
│ │
│ Runner creates InvocationContext │
│ │ │
│ ├── session ──────────────────┐ │
│ ├── artifact_service ─────────┤ │
│ ├── memory_service ───────────┤ │
│ └── credential_service ───────┤ │
│ ▼ │
│ ┌──────────────┐ │
│ │ ToolContext │ │
│ │ │ │
│ │ .state │ ← read/write dict │
│ │ .session │ ← conversation │
│ │ .actions │ ← side effects │
│ │ .user_id │ ← current user │
│ │ │ │
│ │ .save_artifact() │
│ │ .load_artifact() │
│ │ .search_memory() │
│ └──────────────┘ │
│ │ │
│ ▼ │
│ Your tool function │
└──────────────────────────────────────────────────────────────┘
```

The `tool_context` parameter is auto-detected by type and excluded from the LLM's function declaration.

---

## 6. Multi-Agent Systems (The Real Power)

### [ ] Pattern 1: Agent Transfer (LLM Decides Routing)

```python
from google.adk import Agent

# Specialist agents
flight_agent = Agent(
    model="gemini-2.5-flash",
    name="flight_agent",
    description="Handles flight searches and bookings",
    instruction="You help users find and book flights.",
    tools=[search_flights, book_flight],
)

hotel_agent = Agent(
    model="gemini-2.5-flash",
    name="hotel_agent",
    description="Handles hotel searches and reservations",
    instruction="You help users find and book hotels.",
    tools=[search_hotels, book_hotel],
)

# Root agent dispatches to specialists
root_agent = Agent(
    model="gemini-2.5-flash",
    name="travel_assistant",
    instruction="""You are a travel assistant. Route requests to the right agent:
    - Flight questions → flight_agent
    - Hotel questions → hotel_agent
    For general questions, answer directly.""",
    sub_agents=[flight_agent, hotel_agent],
)
```

```
User: "Find a flight to Tokyo"
 │
 ▼
┌────────────────────────────────────────────────────────────────┐
│ root_agent (travel_assistant) │
│ │
│ LLM thinks: "This is a flight question" │
│ LLM calls: transfer_to_agent("flight_agent") ← auto-injected│
│ │
│ │ │
│ ▼ │
│ ┌──────────────────────────────────────────┐ │
│ │ flight_agent │ │
│ │ │ │
│ │ LLM thinks: "Search for Tokyo flights" │ │
│ │ LLM calls: search_flights("Tokyo") │ │
│ │ Tool returns: [JAL 101, ANA 205, ...] │ │
│ │ LLM responds: "Here are flights..." │ │
│ └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
 │
 ▼
"I found these flights to Tokyo: JAL 101 departing..."
```

ADK auto-injects `transfer_to_agent` into agents with sub-agents. The LLM uses `description` fields to decide routing.

### [ ] Pattern 2: Sequential Pipeline (Fixed Order)

```python
from google.adk import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from pydantic import BaseModel

class PizzaOrder(BaseModel):
    size: str
    crust: str
    toppings: list[str]

# Step 1: Gather order details
order_intake = Agent(
    model="gemini-2.5-flash",
    name="order_intake",
    instruction="Collect pizza order details. Ask about size, crust, and toppings.",
    output_schema=PizzaOrder, # Forces structured output
    output_key="current_order", # Saves to session state
)

# Step 2: Confirm and price
order_confirm = Agent(
    model="gemini-2.5-flash",
    name="order_confirm",
    instruction="""Read the order from state key 'current_order'.
    Calculate the price and confirm with the user.""",
    tools=[calculate_price],
)

# Pipeline: intake → confirm
root_agent = SequentialAgent(
    name="pizza_ordering",
    sub_agents=[order_intake, order_confirm],
)
```

```
User: "I want a large pepperoni pizza"
 │
 ▼
┌────────────────────────────────────────────────────┐
│ SequentialAgent: pizza_ordering │
│ │
│ Step 1 ─────────────────────────────────┐ │
│ │ order_intake │ │
│ │ Collects: size=large, crust=regular, │ │
│ │ toppings=[pepperoni] │ │
│ │ Saves to state["current_order"] │ │
│ └────────────────────────────────────────┘ │
│ │ │
│ ▼ │
│ Step 2 ─────────────────────────────────┐ │
│ │ order_confirm │ │
│ │ Reads state["current_order"] │ │
│ │ Calls calculate_price(order) │ │
│ │ Responds: "Large pepperoni: $18.99" │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

### [ ] Pattern 3: Parallel Execution (Concurrent Agents)

```python
from google.adk import Agent
from google.adk.agents.parallel_agent import ParallelAgent

# These agents run at the same time
sentiment_agent = Agent(
    model="gemini-2.5-flash",
    name="sentiment_analyzer",
    instruction="Analyze the sentiment of the user's message.",
    output_key="sentiment",
)

topic_agent = Agent(
    model="gemini-2.5-flash",
    name="topic_classifier",
    instruction="Classify the topic of the user's message.",
    output_key="topic",
)

# Both run concurrently, results stored in state
parallel_analysis = ParallelAgent(
    name="analyzer",
    sub_agents=[sentiment_agent, topic_agent],
)

# Summarizer reads both results
summarizer = Agent(
    model="gemini-2.5-flash",
    name="summarizer",
    instruction="""Read state keys 'sentiment' and 'topic'.
    Provide a combined analysis report.""",
)

# Full pipeline: parallel analysis → summary
root_agent = SequentialAgent(
    name="analysis_pipeline",
    sub_agents=[parallel_analysis, summarizer],
)
```

```
User: "I love how fast the new API is!"
 │
 ▼
┌──────────────────────────────────────────────────────────────┐
│ SequentialAgent: analysis_pipeline │
│ │
│ Step 1: ParallelAgent ─────────────────────────────┐ │
│ │ │ │
│ │ ┌─────────────────────┐ ┌─────────────────────┐│ │
│ │ │ sentiment_analyzer │ │ topic_classifier ││ │
│ │ │ │ │ ││ │
│ │ │ Running │ │ Running ││ │
│ │ │ concurrently... │ │ concurrently... ││ │
│ │ │ │ │ ││ │
│ │ │ → "Positive (0.95)" │ │ → "Technology/API" ││ │
│ │ │ saved to state │ │ saved to state ││ │
│ │ └─────────────────────┘ └─────────────────────┘│ │
│ └───────────────────────────────────────────────────┘ │
│ │ │
│ ▼ │
│ Step 2: summarizer ────────────────────────────────┐ │
│ │ Reads state["sentiment"] = "Positive (0.95)" │ │
│ │ Reads state["topic"] = "Technology/API" │ │
│ │ Responds: "Positive feedback about API performance"│ │
│ └───────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### [ ] Pattern 4: Loop Agent (Iterate Until Done)

```python
from google.adk import Agent
from google.adk.agents.loop_agent import LoopAgent

refiner = Agent(
    model="gemini-2.5-flash",
    name="code_refiner",
    instruction="""Review and improve the code in state['code'].
    If the code is good enough, call escalate() to stop the loop.
    Otherwise, save improved version to state['code'].""",
    tools=[run_linter, run_tests],
)

root_agent = LoopAgent(
    name="refine_loop",
    sub_agents=[refiner],
    max_iterations=5, # Safety limit
)
```

```
┌─────────────────────────────────────────────────┐
│ LoopAgent: refine_loop (max 5 iterations) │
│ │
│ Iteration 1: │
│ │ code_refiner runs linter → 3 warnings │
│ │ Improves code, saves to state['code'] │
│ │ (does not escalate, continues) │
│ │ │
│ Iteration 2: │
│ │ code_refiner runs linter → 0 warnings │
│ │ Runs tests → all pass │
│ │ Calls escalate() ← exits the loop │
│ └────────────────────────────────────────────── │
│ │
│ Result: Refined code after 2 iterations │
└─────────────────────────────────────────────────┘
```

---

## 7. Running Your Agent

### [ ] Standard Setup

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "my_app"
USER_ID = "user_123"

session_service = InMemorySessionService()

async def handle_message(user_message: str):
    # 1. Create or fetch session
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    # 2. Create runner
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # 3. Build user content
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    # 4. Stream events
    async for event in runner.run_async(
        session_id=session.id,
        user_id=USER_ID,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}]: {part.text}")
```

```
runner.run_async(session_id, user_id, new_message)
 │
 ▼
 ┌─────────────────────────────────────┐
 │ 1. Fetch session from storage │
 │ 2. Build InvocationContext │
 │ (session + services + config) │
 │ 3. Call agent.run_async(context) │
 │ 4. For each yielded Event: │
 │ a. Append to session │
 │ b. Apply state_delta │
 │ c. Stream to caller │
 │ 5. Persist session updates │
 └─────────────────────────────────────┘
```

---

## 8. Understanding Events (The Universal Data Type)

Every action in ADK produces an `Event`. Events carry both content and side effects:

```python
from google.adk.events import Event, EventActions
from google.genai import types

# An event looks like this internally:
event = Event(
    invocation_id="inv_001",
    author="flight_agent", # Which agent produced this
    content=types.Content( # What the agent said
    role="model",
    parts=[types.Part(text="Found 3 flights to Tokyo")],
    ),
    actions=EventActions( # Side effects to apply
    state_delta={"last_search": "Tokyo"},
    transfer_to_agent=None, # Or "hotel_agent" to transfer
    escalate=False, # Or True to exit a loop
    ),
)
```

```
┌──────────────────────────────────────────────────────────────────┐
│ Event Lifecycle │
│ │
│ Agent yields Event │
│ │ │
│ ▼ │
│ ┌──────────────────────────────────────────────┐ │
│ │ Runner processes Event: │ │
│ │ │ │
│ │ event.actions.state_delta? │ │
│ │ ├── Yes → merge into session.state │ │
│ │ │ │ │
│ │ event.actions.transfer_to_agent? │ │
│ │ ├── Yes → switch execution to target agent │ │
│ │ │ │ │
│ │ event.actions.escalate? │ │
│ │ ├── Yes → exit current loop/agent │ │
│ │ │ │ │
│ │ event.content? │ │
│ │ ├── Yes → stream text/data to caller │ │
│ │ │ │ │
│ │ Append event to session.events │ │
│ └──────────────────────────────────────────────┘ │
│ │ │
│ ▼ │
│ Caller receives event (your code) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 9. Session State Scoping

State keys have scopes via prefixes:
- No prefix → this session only
- `user:` → shared across all sessions for this user
- `app:` → shared across all users
- `temp:` → this invocation only (never persisted)

See [08-sessions.md](08-sessions.md) for the full scoping rules and persistence behavior.

---

## 10. The Callback System (Intercepting Everything)

ADK hooks at every layer:

```
┌──────────────────────────────────────────────────────────────────┐
│ Callback Execution Order │
│ │
│ ① before_agent_callback │
│ │ ├── Return Content → skip agent entirely │
│ │ └── Return None → continue │
│ │ │
│ │ ② before_model_callback │
│ │ │ ├── Return LlmResponse → skip LLM call │
│ │ │ └── Return None → continue │
│ │ │ │
│ │ │ ┌──────────────┐ │
│ │ │ │ LLM Call │ │
│ │ │ └──────────────┘ │
│ │ │ │
│ │ ③ after_model_callback │
│ │ │ ├── Return LlmResponse → replace response │
│ │ │ └── Return None → use original │
│ │ │ │
│ │ │ If LLM requested a tool call: │
│ │ │ │
│ │ │ ④ before_tool_callback │
│ │ │ │ ├── Return dict → skip tool, use as result │
│ │ │ │ └── Return None → continue │
│ │ │ │ │
│ │ │ │ ┌──────────────┐ │
│ │ │ │ │ Tool runs │ │
│ │ │ │ └──────────────┘ │
│ │ │ │ │
│ │ │ ⑤ after_tool_callback │
│ │ │ ├── Return dict → replace result │
│ │ │ └── Return None → use original │
│ │ │ │
│ │ │ (Loop back to ② if more tool calls needed) │
│ │ │
│ ⑥ after_agent_callback │
│ ├── Return Content → append to response │
│ └── Return None → no change │
└──────────────────────────────────────────────────────────────────┘
```

**Example: Logging + rate limiting callback:**

```python
import time

async def rate_limit_callback(
    callback_context, # Must be named exactly "callback_context"
    llm_request, # The request about to be sent
):
    """Logs every LLM call and enforces rate limiting."""
    last_call = callback_context.state.get("temp:last_llm_call", 0)
    now = time.time()

    if now - last_call < 1.0: # Min 1 second between calls
    await asyncio.sleep(1.0 - (now - last_call))

    callback_context.state["temp:last_llm_call"] = time.time()
    print(f"[LLM Call] {len(llm_request.contents)} messages in context")
    return None # Continue with original request

root_agent = Agent(
    model="gemini-2.5-flash",
    name="my_agent",
    instruction="You are helpful.",
    before_model_callback=rate_limit_callback,
)
```

---

## 11. Putting It All Together: Complete Example

A realistic customer support agent system:

```python
from google.adk import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ─── Tools ─────────────────────────────────────────────

def lookup_order(order_id: str, tool_context: ToolContext) -> str:
    """Look up an order by its ID."""
    orders = {
        "ORD-001": {"status": "shipped", "item": "Laptop", "eta": "March 20"},
        "ORD-002": {"status": "processing", "item": "Keyboard", "eta": "March 25"},
    }
    order = orders.get(order_id)
    if not order:
        return f"Order {order_id} not found."
    tool_context.state["current_order"] = order
    return f"Order {order_id}: {order['item']} — Status: {order['status']}, ETA: {order['eta']}"

def initiate_refund(order_id: str, reason: str) -> str:
    """Initiate a refund for an order."""
    return f"Refund initiated for {order_id}. Reason: {reason}. Ref: REF-{order_id[-3:]}"

def transfer_to_human(summary: str) -> str:
    """Transfer the conversation to a human support agent."""
    return f"Transferred to human agent. Summary: {summary}"

# ─── Agents ────────────────────────────────────────────

order_agent = Agent(
    model="gemini-2.5-flash",
    name="order_agent",
    description="Handles order lookups and status inquiries",
    instruction="Help users check their order status. Use lookup_order to find orders.",
    tools=[lookup_order],
)

refund_agent = Agent(
    model="gemini-2.5-flash",
    name="refund_agent",
    description="Handles refund requests and returns",
    instruction="Process refund requests. Always ask for the reason before initiating.",
    tools=[initiate_refund],
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="support_bot",
    instruction="""You are a customer support assistant.
    Route order questions to order_agent and refund requests to refund_agent.
    If the issue is complex, use transfer_to_human.""",
    tools=[transfer_to_human],
    sub_agents=[order_agent, refund_agent],
)

# ─── Run It ────────────────────────────────────────────

async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="support_app",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="support_app", user_id="user_1"
    )

    for msg in [
        "Hi, I need to check my order ORD-001",
        "Actually, I want a refund for it",
        "The laptop arrived damaged",
    ]:
        content = types.Content(role="user", parts=[types.Part(text=msg)])
        async for event in runner.run_async(
            session_id=session.id, user_id="user_1", new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}]: {part.text}")
```

```
Conversation flow:

User: "Check my order ORD-001"
 │
 ▼
support_bot → transfer_to_agent("order_agent")
 │
 ▼
order_agent → lookup_order("ORD-001")
 → "Order ORD-001: Laptop — shipped, ETA March 20"
 │
User: "I want a refund for it"
 │
 ▼
order_agent → transfer_to_agent("refund_agent") (back to root, then to refund)
 │
 ▼
refund_agent → "What's the reason for the refund?"
 │
User: "The laptop arrived damaged"
 │
 ▼
refund_agent → initiate_refund("ORD-001", "Laptop arrived damaged")
 → "Refund initiated. Ref: REF-001"
```

---

## 12. Quick Reference: Agent Configuration Cheat Sheet

```python
Agent(
    # ─── Required ───────────────────────────────────────
    name="my_agent", # Valid Python identifier, NOT "user"
    model="gemini-2.5-flash", # Or inherit from parent agent

    # ─── Common ─────────────────────────────────────────
    instruction="You are...", # System prompt (supports {state_key} placeholders)
    description="Does X", # Used by parent for transfer decisions
    tools=[func1, func2], # Functions, BaseTool, or BaseToolset instances
    sub_agents=[child1, child2], # Enable agent transfer

    # ─── Output Control ─────────────────────────────────
    output_schema=MyModel, # Force structured JSON output (disables tools!)
    output_key="result", # Save output to session state

    # ─── Transfer Control ────────────────────────────────
    disallow_transfer_to_parent=False, # Can this agent return to parent?
    disallow_transfer_to_peers=False, # Can this agent go to siblings?

    # ─── Callbacks ───────────────────────────────────────
    before_agent_callback=my_fn, # Before agent runs
    after_agent_callback=my_fn, # After agent completes
    before_model_callback=my_fn, # Before each LLM call
    after_model_callback=my_fn, # After each LLM response
    before_tool_callback=my_fn, # Before each tool execution
    after_tool_callback=my_fn, # After each tool execution

    # ─── Advanced ────────────────────────────────────────
    generate_content_config=types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=2048,
    ),
    include_contents='default', # 'default' or 'none' (skip history)
    planner=my_planner, # Planning/thinking support
    code_executor=my_executor, # Code execution sandbox
)
```

---

## 13. Where to Go Next

```
You are here ────────────────────────────────────────────────────┐
│ │
│ ✅ 25-onboarding-guide.md (this file) │
│ │ │
│ ├── Want to avoid common mistakes? │
│ │ → 20-best-practices.md │
│ │ │
│ ├── Want to go deeper into advanced patterns? │
│ │ → 23-advanced-internals.md │
│ │ │
│ ├── Want to understand a specific component? │
│ │ → 07-events.md through 10-apps.md (in order) │
│ │ │
│ ├── Want to see a full traced request? │
│ │ → 01-request-lifecycle.md │
│ │ │
│ └── Need to decide which ADK component to use? │
│ → 02-when-to-build-what.md │
└─────────────────────────────────────────────────────────────────┘
```

### [ ] Learning Paths — Pick Your Track

```
Track 1: Quick Start (1 hour)
 25-onboarding-guide → 01-request-lifecycle → 09-tools → build something!
 You'll know: how to create an agent with tools

Track 2: Core Understanding (half day)
 01-request-lifecycle → 03-runners → 04-agents → 05-flows
 → 07-events → 08-sessions → 09-tools → 10-apps
 You'll know: how every layer works and connects

Track 3: Production Ready (2 days)
 All of Track 2, plus:
 → 11-memory → 13-auth → 16-error-reference → 17-concurrency
 → 20-best-practices → 22-testing
 You'll know: how to build, test, and operate production agents

Track 4: Full Mastery (1 week)
 All 25 files in order
 You'll know: every ADK subsystem, pattern, and edge case
```

---

## Cross-references

- [07-events.md](07-events.md) — Deep dive on the Event class
- [04-agents.md](04-agents.md) — All agent types in detail
- [03-runners.md](03-runners.md) — Runner lifecycle
- [09-tools.md](09-tools.md) — Complete tool system reference
- [08-sessions.md](08-sessions.md) — Session state and storage backends
- [02-when-to-build-what.md](02-when-to-build-what.md) — Decision guide
- [20-best-practices.md](20-best-practices.md) — Best practices and common mistakes
- [23-advanced-internals.md](23-advanced-internals.md) — Advanced patterns and internals
