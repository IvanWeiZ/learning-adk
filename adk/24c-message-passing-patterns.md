# Message-Passing Patterns: Passing Data Between Agents

> **Official docs:** [Agents](https://google.github.io/adk-docs/agents/) | **Source:** [`agents/`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/) | **Prereqs:** [04-agents.md](04-agents.md), [09-tools.md](09-tools.md)

> **Note:** AI-generated content, human-reviewed. May contain errors — verify against official docs.

*Extracted from [24-faq.md](24-faq.md) Q4.*

---

## What Is the Best Way to Pass Messages Between Agents?

Four mechanisms:

#### Method 1: Session State (Most Common)

Agents in the same session share state via `output_key` or direct writes:

**Pros:** simple, works immediately, persists across turns
**Cons:** global namespace (key collisions), no type safety

```python
# Agent A writes to state
agent_a = Agent(
    name="researcher",
    instruction="Research the topic and save findings.",
    output_key="research_findings", # Auto-saves text output to state
)

# Agent B reads from state
agent_b = Agent(
    name="writer",
    instruction="""Write an article based on state key 'research_findings'.
    Use the pre-researched material.""",
)

# Sequential pipeline: A → B
root = SequentialAgent(
    name="pipeline",
    sub_agents=[agent_a, agent_b],
)
```

```
State-based message passing:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ Agent A runs                                             │
│   │                                                      │
│   │ output_key="research_findings"                       │
│   │ Agent produces text → auto-saved to state            │
│   │                                                      │
│   │ state["research_findings"] = "Quantum computing..."  │
│   │                                                      │
│   ▼                                                      │
│ Agent B runs                                             │
│   │                                                      │
│   │ Instruction references {research_findings}           │
│   │ ADK replaces placeholder with state value            │
│   │                                                      │
│   │ Agent sees: "Write article based on:                 │
│   │   Quantum computing..."                              │
│   │                                                      │
│   ▼                                                      │
│ Final output                                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Method 2: Tool-Based State Writing

For more control over what gets passed:

**Pros:** LLM controls what gets written, natural language interface
**Cons:** unreliable (LLM may forget to call), extra tool call overhead

```python
def save_analysis(
    sentiment: str,
    confidence: float,
    key_themes: list[str],
    tool_context: ToolContext,
) -> str:
    """Save structured analysis results for downstream agents."""
    tool_context.state["analysis"] = {
        "sentiment": sentiment,
        "confidence": confidence,
        "themes": key_themes,
    }
    return "Analysis saved."

# Agent A uses the tool to write structured data
agent_a = Agent(
    name="analyzer",
    instruction="Analyze the text, then call save_analysis with your findings.",
    tools=[save_analysis],
)

# Agent B reads the structured data
agent_b = Agent(
    name="reporter",
    instruction="Read state['analysis'] and generate a report.",
)
```

#### Method 3: Agent Transfer (LLM-Driven Routing)

Transfer carries full session history:

**Pros:** LLM-driven routing, natural conversation flow
**Cons:** no structured data handoff, target sees full history (privacy)

```python
root = Agent(
    name="router",
    instruction="Route to the right specialist.",
    sub_agents=[
        Agent(
            name="billing",
            description="Handles billing and payment questions",
            instruction="Handle billing issues. Transfer back when done.",
        ),
        Agent(
            name="technical",
            description="Handles technical problems and bugs",
            instruction="Handle technical issues. Transfer back when done.",
        ),
    ],
)
```

```
Agent transfer message passing:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ User: "I have a billing question"                        │
│   │                                                      │
│   ▼                                                      │
│ router agent                                             │
│   │ LLM: transfer_to_agent("billing")                    │
│   │                                                      │
│   │ ┌─────────────────────────────────────┐              │
│   │ │ billing agent                       │              │
│   │ │ Sees FULL conversation history      │ ← shared     │
│   │ │ Sees ALL state                      │ ← session    │
│   │ │ Responds in same session            │              │
│   │ └─────────────────────────────────────┘              │
│   │                                                      │
│   │ When billing is done:                                │
│   │   transfer_to_agent("router") ← returns to parent    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Method 4: AgentTool (Isolated Execution)

Isolated execution without shared history:

**Pros:** isolated execution (own branch), structured input_schema
**Cons:** no shared history, heavier setup

```python
from google.adk.tools.agent_tool import AgentTool

helper = Agent(
    name="summarizer",
    instruction="Summarize the given text in 2-3 sentences.",
)

helper_tool = AgentTool(agent=helper)

main_agent = Agent(
    name="main",
    instruction="Use summarizer tool when you need to condense text.",
    tools=[helper_tool],
)
```

```
AgentTool message passing:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│ main_agent                                               │
│   │                                                      │
│   │ LLM calls: summarizer(request="long text here...")   │
│   │   │                                                  │
│   │   ▼                                                  │
│   │   ┌───────────────────────────────────┐              │
│   │   │ summarizer agent (ISOLATED)       │              │
│   │   │ - New session (empty history)     │              │
│   │   │ - Only sees the request text      │              │
│   │   │ - Returns result as tool output   │              │
│   │   └──────────────────┬────────────────┘              │
│   │                      │                               │
│   │                      ▼                               │
│   │   Tool result: "Summary: ..."                        │
│   │   main_agent continues with summary                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### Comparison Table

```
Message passing methods compared:
│
├── Session State (output_key)
│      Shares history: Yes
│      Shares state: Yes
│      Extra LLM call: No
│      Best for: Pipeline stages
│
├── Tool State Write (ToolContext.state)
│      Shares history: Yes
│      Shares state: Yes
│      Extra LLM call: No
│      Best for: Complex data
│
├── Agent Transfer (sub_agents)
│      Shares history: Yes
│      Shares state: Yes
│      Extra LLM call: Yes (route)
│      Best for: Dynamic routing
│
└── AgentTool (tool wrapper)
       Shares history: No (new session)
       Shares state: No (new session)
       Extra LLM call: Yes (child)
       Best for: Isolated helpers
```


---

## Related

- [24-faq.md](24-faq.md) — FAQ overview
- [04-agents.md](04-agents.md) — Agent types deep dive
- [08-sessions.md](08-sessions.md) — Session state reference
- [09-tools.md](09-tools.md) — Tool system reference
