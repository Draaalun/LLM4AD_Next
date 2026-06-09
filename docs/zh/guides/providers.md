# 自定义提供商

本指南解释如何向 LLM4AD 添加自定义 LLM 提供商。

## 概述

LLM4AD 开箱即支持多个 LLM 提供商：
- **OpenAI**: GPT 模型
- **Anthropic**: Claude 模型
- **OpenAI 兼容**: 本地模型或自定义 API

您还可以为其他 LLM 服务创建自定义提供商。

## 创建自定义提供商

### 基础提供商接口

所有提供商都扩展基础提供商接口：

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseProvider(ABC):
    """基础 LLM 提供商接口。"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """从提示生成文本。

        Args:
            prompt: 输入提示
            **kwargs: 附加参数（temperature、max_tokens 等）

        Returns:
            生成的文本
        """
        pass

    @abstractmethod
    async def generate_with_messages(
        self,
        messages: list[dict],
        **kwargs
    ) -> str:
        """从消息历史生成文本。

        Args:
            messages: 带有 'role' 和 'content' 的消息字典列表
            **kwargs: 附加参数

        Returns:
            生成的文本
        """
        pass
```

### 示例：自定义提供商

以下是自定义提供商的示例：

```python
"""自定义 LLM 提供商示例。"""

import aiohttp
from typing import Any

from llm4ad.infra.provider.base import BaseProvider


class CustomProvider(BaseProvider):
    """自定义 LLM 提供商实现。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        **kwargs
    ):
        """初始化自定义提供商。

        Args:
            api_key: 用于身份验证的 API 密钥
            base_url: API 的基础 URL
            model: 模型标识符
            **kwargs: 附加配置
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.session = aiohttp.ClientSession()

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """从提示生成文本。"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with self.session.post(
            f"{self.base_url}/generate",
            json=payload,
            headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data["text"]

    async def generate_with_messages(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """从消息历史生成文本。"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with self.session.post(
            f"{self.base_url}/chat",
            json=payload,
            headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data["choices"][0]["message"]["content"]

    async def close(self):
        """关闭提供商会话。"""
        await self.session.close()
```

## 注册自定义提供商

### 方法 1：使用注册表

在代码中注册您的提供商：

```python
from llm4ad.infra.provider.base import BaseProvider
from llm4ad.utils.registry import Registry

# 获取提供商注册表
provider_registry = Registry("provider", BaseProvider)

# 注册您的提供商
@provider_registry.register("my_custom_provider")
class CustomProvider(BaseProvider):
    # ... 实现
    pass
```

### 方法 2：使用配置

在配置文件中指定提供商类型：

```yaml
providers:
  - name: "custom"
    type: "my_custom_provider"  # 注册名称
    api_key: "${API_KEY}"
    base_url: "https://api.example.com"
    model: "my-model"
```

## 使用自定义提供商

注册后，在配置中使用您的自定义提供商：

```yaml
providers:
  - name: "my_provider"
    type: "my_custom_provider"
    api_key: "${MY_API_KEY}"
    base_url: "https://api.example.com"
    model: "my-model"
    temperature: 0.7
    max_tokens: 4096

planner:
  provider: "my_provider"
coder:
  provider: "my_provider"
```

## 最佳实践

1. **Async/Await**：始终使用异步方法进行 I/O 操作
2. **错误处理**：优雅地处理 API 错误
3. **速率限制**：如需要，实现速率限制
4. **会话管理**：重用 HTTP 会话以提高效率
5. **超时**：为 API 调用设置合理的超时

## 下一步

- [配置指南](configuration.md) - 配置提供商
- [编写评估函数](evaluators.md) - 创建自定义评估器
- [快速入门指南](quickstart.md) - 运行您的第一个实验
