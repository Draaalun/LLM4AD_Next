# Provider API

`llm4ad.infra.provider` is the abstraction layer over LLM (and embedding) services. Three providers ship out of the box and any of them can be used by name from the YAML config.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `BaseProvider` | Abstract provider; subclass and call `register_provider("name")` to add new ones | `src/llm4ad/infra/provider/base.py` |
| `OpenAICompatibleProvider` | OpenAI Chat Completions plus any compatible endpoint (Together, Groq, vLLM, DeepSeek, …) | `src/llm4ad/infra/provider/openai_compatible.py` |
| `AnthropicProvider` | Anthropic Messages API (Claude 3+, native tool use, vision) | `src/llm4ad/infra/provider/anthropic.py` |
| `MockProvider` | Deterministic in-memory provider for tests and CI | `src/llm4ad/infra/provider/mock.py` |
| `ChatMessage`, `ContentPart`, `ToolDefinition`, `ToolCall` | Wire-format types shared by every provider | `src/llm4ad/infra/provider/base.py` |
| `ProviderType` | Enum of registry names (`OPENAI`, `ANTHROPIC`, `OPENAI_COMPATIBLE`) | `src/llm4ad/infra/provider/base.py` |

## Creating a provider

```python
from llm4ad.config import ProviderConfig
from llm4ad.infra.provider.base import BaseProvider

BaseProvider.discover("llm4ad.infra.provider")  # populate the registry once

cfg = ProviderConfig(
    name="default",
    type="openai_compatible",
    api_key="sk-...",
    model="gpt-4o-mini",
    base_url=None,            # provider default
)
provider = BaseProvider.create(cfg.type, config=cfg)

response = await provider.chat(
    [ChatMessage(role="user", content="say hi")],
    temperature=0.2,
    max_tokens=64,
)
```

`provider.chat(...)` returns a structured response with the message text, any tool calls, and an `ExecutionTiming` record (see [Infrastructure](infra.md)).

## Multimodal messages

Vision-enabled models accept image content via `ContentPart`:

```python
ChatMessage(role="user", content=[
    ContentPart(type="text", text="What's in this image?"),
    ContentPart(type="image_url", image_url={"url": "data:image/png;base64,..."}),
])
```

Use the multimodal samplers (see [Planner](planner.md)) to plumb behavior images from the evaluator through to the prompt automatically.

## Embeddings

Embedding endpoints are configured separately under `embedding:` in the YAML. The `local` embedding type is a special two-endpoint mode where text and code can target different deployments — see [Embeddings & Trajectory](../guides/embeddings.md).

```python
from llm4ad.orchestrator.embedding_client import EmbeddingClient

client = EmbeddingClient(config.embedding)
vec = await client.embed("text", task="text")
```

## Adding a custom provider

```python
from llm4ad.infra.provider.base import BaseProvider, register_provider

@register_provider("my_provider")
class MyProvider(BaseProvider):
    async def chat(self, messages, **kw): ...
    async def embed(self, texts, **kw): ...
```

After import, set `type: my_provider` in any provider entry in YAML. The same registry powers `llm4ad list provider`.

## See also

- [Providers Guide](../guides/providers.md) — user-facing walkthrough
- [Embeddings & Trajectory](../guides/embeddings.md) — embedding-specific configuration
- Source of truth: `src/llm4ad/infra/provider/`
