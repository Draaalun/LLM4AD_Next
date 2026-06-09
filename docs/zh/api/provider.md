# 提供商 API

`llm4ad.infra.provider` 是 LLM（和嵌入）服务的抽象层。框架内置了三种 provider，YAML 配置中可按名称引用。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `BaseProvider` | 抽象 provider；继承并调用 `register_provider("name")` 即可新增 | `src/llm4ad/infra/provider/base.py` |
| `OpenAICompatibleProvider` | OpenAI Chat Completions 及任何兼容端点（Together、Groq、vLLM、DeepSeek 等） | `src/llm4ad/infra/provider/openai_compatible.py` |
| `AnthropicProvider` | Anthropic Messages API（Claude 3+、原生工具调用、视觉） | `src/llm4ad/infra/provider/anthropic.py` |
| `MockProvider` | 测试和 CI 用的确定性内存 provider | `src/llm4ad/infra/provider/mock.py` |
| `ChatMessage`、`ContentPart`、`ToolDefinition`、`ToolCall` | 所有 provider 共用的传输格式类型 | `src/llm4ad/infra/provider/base.py` |
| `ProviderType` | 注册名称枚举（`OPENAI`、`ANTHROPIC`、`OPENAI_COMPATIBLE`） | `src/llm4ad/infra/provider/base.py` |

## 创建一个 provider

```python
from llm4ad.config import ProviderConfig
from llm4ad.infra.provider.base import BaseProvider

BaseProvider.discover("llm4ad.infra.provider")  # 仅需调用一次，填充注册表

cfg = ProviderConfig(
    name="default",
    type="openai_compatible",
    api_key="sk-...",
    model="gpt-4o-mini",
    base_url=None,            # 使用 provider 默认值
)
provider = BaseProvider.create(cfg.type, config=cfg)

response = await provider.chat(
    [ChatMessage(role="user", content="say hi")],
    temperature=0.2,
    max_tokens=64,
)
```

`provider.chat(...)` 返回结构化响应，包含消息文本、可能的工具调用，以及一个 `ExecutionTiming` 记录（详见[基础设施](infra.md)）。

## 多模态消息

支持视觉的模型通过 `ContentPart` 接收图像内容：

```python
ChatMessage(role="user", content=[
    ContentPart(type="text", text="这张图里是什么？"),
    ContentPart(type="image_url", image_url={"url": "data:image/png;base64,..."}),
])
```

使用多模态采样器（参见[规划器](planner.md)）可以将评估器产出的行为图像自动接入提示词。

## 嵌入

嵌入端点在 YAML 的 `embedding:` 下单独配置。`local` 嵌入类型是一个特殊的双端点模式，可以让文本和代码指向不同的部署 — 详见 [Embeddings 与轨迹](../guides/embeddings.md)。

```python
from llm4ad.orchestrator.embedding_client import EmbeddingClient

client = EmbeddingClient(config.embedding)
vec = await client.embed("text", task="text")
```

## 新增自定义 provider

```python
from llm4ad.infra.provider.base import BaseProvider, register_provider

@register_provider("my_provider")
class MyProvider(BaseProvider):
    async def chat(self, messages, **kw): ...
    async def embed(self, texts, **kw): ...
```

import 完成后，YAML 任意 provider 条目下设 `type: my_provider` 即可使用。`llm4ad list provider` 也由同一注册表驱动。

## 相关链接

- [提供商指南](../guides/providers.md) — 面向用户的实操
- [Embeddings 与轨迹](../guides/embeddings.md) — 嵌入相关配置
- 源码权威：`src/llm4ad/infra/provider/`
