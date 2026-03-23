# 00 — Onboarding: Zero to First Agent

> **Official docs:** [Quickstart](https://google.github.io/adk-docs/get-started/quickstart/) | **Source:** all ADK modules | **Prereqs:** none

## An Agent Is Just Three Things

```
An ADK agent = prompt + model + tools

That's it.

├── prompt
│      "You are a helpful weather assistant."
│      tells the LLM what to do
│
├── model
│      "gemini-2.5-flash"
│      which LLM to use
│
└── tools
       [get_weather]
       Python functions the LLM can call
```

Everything else — Runner, Session, Events, Flows — is infrastructure that ADK handles for you. You define **what** the agent does. ADK handles **how** it runs.

---

## 1. Create an Agent (5 Lines)

```python
from google.adk import Agent

agent = Agent(
    name="greeter",
    model="gemini-2.5-flash",
    instruction="You are a friendly assistant. Greet users warmly.",
)
```

That's a working AI agent. No tools, no configuration, no boilerplate. ADK wraps this into a full pipeline: session management, LLM calls, event streaming — all handled automatically.

---

## 2. Add a Tool (It's Just a Function)

Any Python function becomes an LLM-callable tool:

```python
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"22C, clear skies in {city}"

agent = Agent(
    name="weather_bot",
    model="gemini-2.5-flash",
    instruction="Help users check the weather.",
    tools=[get_weather],
)
```

That's it. ADK reads the function signature and docstring, generates a tool schema, and the LLM knows how to call it. No registration, no decorators, no configuration.

```
What happens when the user asks "What's the weather in Tokyo?":
│
├── LLM reads the tool schema
│      name: "get_weather"
│      parameters: {"city": "string"}
│      description: "Get current weather for a city."
│
├── LLM decides to call the tool
│      FunctionCall(name="get_weather", args={"city": "Tokyo"})
│
├── ADK executes your Python function
│      get_weather("Tokyo") → "22C, clear skies in Tokyo"
│
├── ADK feeds the result back to the LLM
│      FunctionResponse(result="22C, clear skies in Tokyo")
│
└── LLM generates the final answer
       "The weather in Tokyo is 22C with clear skies!"
```

---

## 3. Run It

To run an agent, you need a Runner (orchestrates requests) and a SessionService (stores conversation history).

```python
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="my_app", session_service=session_service)

async def main():
    session = await session_service.create_session(app_name="my_app", user_id="user_1")
    async for event in runner.run_async(
        user_id="user_1",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="What's the weather in Tokyo?")]),  # the user's message
    ):
        if event.is_final_response():  # stream ends when final_response is True
            print(event.content.parts[0].text)

asyncio.run(main())
```

Three pieces: **Agent** (what to do) + **Runner** (how to run) + **Session** (where to store). Everything else is optional.

---

## 4. What ADK Handles for You

You don't need to understand any of this to get started — but it's there when you need it:

```
What you write:                    What ADK handles:
│                                  │
├── Agent                          ├── Runner
│      prompt + model + tools      │      orchestrates the full request lifecycle
│                                  │
├── Tools                          ├── Session & State
│      plain Python functions      │      persists conversation history automatically
│                                  │
└── That's it                      ├── Flows
                                   │      reason-act loop (call LLM → run tools → repeat)
                                   │
                                   ├── Events
                                   │      every action becomes a trackable event
                                   │
                                   ├── MCP
                                   │      connect to external tool servers
                                   │
                                   └── Multi-Agent
                                          transfer, parallel, sequential, loop
```

---

## 5. The Full Architecture (Don't Worry — We'll Explain Each Layer)

```
┌─────────────────────────────────────────────────────────────────┐
│                        User / CLI / API                         │
│                    cli/ · fast_api.py · a2a/                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ new_message
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         runners.py                              │
│  1. fetch/create Session   2. build InvocationContext           │
│  3. call agent.run_async() 4. stream Events back                │
│  5. compact events (optional)                                   │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│       agents/            │    │          sessions/              │
│  LlmAgent (primary)      │    │  Session (data model)           │
│  LoopAgent               │◄──►│  InMemorySessionService         │
│  ParallelAgent           │    │  DatabaseSessionService         │
│  SequentialAgent         │    │  VertexAiSessionService          │
│  base_agent.py           │    │                                 │
└──────────────┬───────────┘    └─────────────────────────────────┘
               │ run_async()
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     flows/llm_flows/                            │
│  BaseLlmFlow.run_async() — the reason-act loop:                 │
│    preprocess → call LLM → postprocess → repeat if tool calls   │
└──────────────┬─────────────────────────────┬────────────────────┘
               │                             │
               ▼                             ▼
┌──────────────────────────┐    ┌────────────────────────────────┐
│        models/           │    │           tools/               │
│  LLMRegistry             │    │  BaseTool / BaseToolset        │
│  Gemini (primary)        │    │  50+ tools: BigQuery, MCP,     │
│  AnthropicLlm            │    │  OpenAPI, LangChain, CrewAI,   │
│  LiteLlm adapter         │    │  code_executors, bash, etc.    │
│  LlmRequest/Response     │    └────────────────────────────────┘
└──────────────────────────┘
               │  all layers emit/share
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          events/                                │
│  Event — the universal unit: user msg, LLM response,           │
│           function call, function response, tool result         │
└─────────────────────────────────────────────────────────────────┘
               │  cross-cutting services
               ▼
┌──────────────┬──────────────┬──────────────┬────────────────────┐
│   memory/    │  artifacts/  │    auth/     │   telemetry/       │
│ (long-term)  │  (files)     │  (OAuth etc) │  (OTel tracing)    │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

This looks like a lot — but you already touched the two most important boxes: **Agent** and **Runner**. The deep-dive files explain each layer one by one.

---

## 6. Where to Go Next

Now that you can build an agent with tools, explore these topics:

| Want to... | Read |
|---|---|
| Trace what happens inside a request | [01-request-lifecycle.md](01-request-lifecycle.md) |
| Use ToolContext (state, artifacts, memory) | [09-tools.md](09-tools.md) |
| Build multi-agent systems | [04-agents.md](04-agents.md) |
| Understand events | [07-events.md](07-events.md) |
| Persist conversations | [08-sessions.md](08-sessions.md) |
| Connect MCP tool servers | [09-tools.md](09-tools.md) (MCP section) |
| Avoid common mistakes | [20-best-practices.md](20-best-practices.md) |
| Decide which ADK component to use | [02-when-to-build-what.md](02-when-to-build-what.md) |
| Try ADK 2.0 (graph workflows) | [25-adk-2.0-preview.md](25-adk-2.0-preview.md) |
