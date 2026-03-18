# Models — LLM Adapters

**Source:** [`models/base_llm.py`](../adk-python/src/google/adk/models/base_llm.py) · [`models/registry.py`](../adk-python/src/google/adk/models/registry.py) · [`models/llm_request.py`](../adk-python/src/google/adk/models/llm_request.py) · [`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py)

---

## [ ] What It Is

The `models/` package is a thin adapter layer between ADK's internal types (`LlmRequest`, `LlmResponse`) and various LLM providers (Gemini, Anthropic, any LiteLLM-supported provider). It hides all provider-specific SDK calls behind a single interface.

---

## [ ] Class Hierarchy

```
BaseLlm  (base_llm.py)   — abstract interface
    ├── GeminiLlm         — Gemini models via google-genai SDK (primary)
    ├── GoogleLlm         — Google-hosted Gemini via Vertex AI
    ├── AnthropicLlm      — Claude models via anthropic SDK (optional dep)
    └── LiteLlm           — 100+ providers via litellm (optional dep)
```

---

## [ ] BaseLlm — The Interface

```python
class BaseLlm(BaseModel):
    model: str   # e.g. 'gemini-2.5-flash', 'claude-opus-4-5'

    @classmethod
    def supported_models(cls) -> list[str]:
        # Returns regex patterns that match model names for this adapter.
        # Used by LLMRegistry to auto-select the right class.
        ...

    @abstractmethod
    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        # Unidirectional text/chat generation.
        # Non-streaming: yields exactly one LlmResponse (partial=False).
        # Streaming: yields N partial=True chunks, then one partial=False final.
        ...

    def connect(self, llm_request: LlmRequest) -> BaseLlmConnection:
        # Bidirectional streaming for Live API (audio/video).
        # Not all adapters support this.
        ...
```

---

## [ ] Streaming Contract

`generate_content_async` with `stream=True` yields:

```
LlmResponse(partial=True,  content=[Part(text='The weather')])
LlmResponse(partial=True,  content=[Part(text=' in Tokyo')])
LlmResponse(partial=True,  content=[Part(text=' is sunny.')])
LlmResponse(partial=False, content=[Part(text='The weather in Tokyo is sunny.')])
```

The final `partial=False` chunk is always a complete aggregation. Callers should use the final chunk for storage and use partial chunks only for streaming UI updates.

Function calls, thoughts, and blobs follow the same pattern — they can arrive in separate `partial=True` chunks.

---

## [ ] LLMRegistry — Auto-Dispatch

`LLMRegistry` maps model name strings to the correct `BaseLlm` subclass using regex matching:

```python
# Registration (done at module import time in each adapter):
LLMRegistry.register(GeminiLlm)
# GeminiLlm.supported_models() = [r'gemini-.*', r'learnlm-.*', ...]

# Resolution:
llm = LLMRegistry.new_llm('gemini-2.5-flash')
# → finds GeminiLlm via regex match → returns GeminiLlm(model='gemini-2.5-flash')
```

`resolve()` is `@lru_cache(maxsize=32)` — repeated resolution of the same model name is fast.

**Error messages are helpful:**
- `claude-*` → tells you to `pip install google-adk[extensions]`
- `provider/model` format → tells you to install `litellm`

---

## [ ] LlmRequest

The request object assembled by the flow before calling the model:

```python
class LlmRequest:
    model: str                              # model name to use
    contents: list[types.Content]           # conversation history
    system_instruction: types.Content       # system prompt
    tools: list[types.Tool]                 # tool definitions (FunctionDeclarations)
    config: types.GenerateContentConfig     # temperature, safety, response_schema, etc.
    tools_dict: dict[str, BaseTool]         # name → BaseTool (internal routing map)

    def append_tools(self, tools: list[BaseTool]) -> None:
        # Adds FunctionDeclarations to self.tools and populates tools_dict.
```

---

## [ ] LlmResponse

The response object returned by the model:

```python
class LlmResponse:
    content: Optional[types.Content]     # text, function calls, thoughts, blobs
    partial: Optional[bool]             # True = streaming chunk, False = final
    usage_metadata: ...                  # token counts
    grounding_metadata: ...             # search grounding info
    input_transcription: ...            # Live API: what user said
    output_transcription: ...           # Live API: what model said
    error_code: ...
    error_message: ...
```

`Event` extends `LlmResponse`, so events carry all response fields plus `author`, `invocation_id`, `actions`, and `branch`.

---

## [ ] Default Model

```python
LlmAgent.DEFAULT_MODEL = 'gemini-2.5-flash'
```

If neither the agent nor any ancestor specifies a model, this is used. You can override globally:

```python
LlmAgent.set_default_model('gemini-2.5-pro')
```

Model inheritance: if `model = ''` on an agent, it walks up `parent_agent` until it finds an ancestor with a model set, then falls back to the default.

---

## [ ] Adding a Custom Adapter

```python
from google.adk.models.base_llm import BaseLlm
from google.adk.models.registry import LLMRegistry

class MyLlm(BaseLlm):
    @classmethod
    def supported_models(cls):
        return [r'my-model-.*']

    async def generate_content_async(self, llm_request, stream=False):
        # Call your API here
        yield LlmResponse(content=..., partial=False)

LLMRegistry.register(MyLlm)
# Now 'my-model-v1' will route to MyLlm
```

---

## [ ] Related Files

- [`models/base_llm.py`](../adk-python/src/google/adk/models/base_llm.py) — abstract interface
- [`models/registry.py`](../adk-python/src/google/adk/models/registry.py) — model dispatch
- [`models/llm_request.py`](../adk-python/src/google/adk/models/llm_request.py) — request object
- [`models/llm_response.py`](../adk-python/src/google/adk/models/llm_response.py) — response object
- [`models/gemini_llm.py`](../adk-python/src/google/adk/models/gemini_llm.py) — Gemini adapter
- [`models/google_llm.py`](../adk-python/src/google/adk/models/google_llm.py) — Vertex AI adapter
- [`models/anthropic_llm.py`](../adk-python/src/google/adk/models/anthropic_llm.py) — Anthropic adapter
- [`models/lite_llm.py`](../adk-python/src/google/adk/models/lite_llm.py) — LiteLLM adapter
