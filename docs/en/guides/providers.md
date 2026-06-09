# Custom Providers

This guide explains how to add custom LLM providers to LLM4AD.

## Overview

LLM4AD supports multiple LLM providers out of the box:
- **OpenAI**: GPT models
- **Anthropic**: Claude models
- **OpenAI-compatible**: Local models or custom APIs

You can also create custom providers for other LLM services.

## Creating a Custom Provider

### Base Provider Interface

All providers extend the base provider interface:

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseProvider(ABC):
    """Base LLM provider interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def generate_with_messages(
        self,
        messages: list[dict],
        **kwargs
    ) -> str:
        """Generate text from message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        pass
```

### Example: Custom Provider

Here's an example of a custom provider:

```python
"""Custom LLM provider example."""

import aiohttp
from typing import Any

from llm4ad.infra.provider.base import BaseProvider


class CustomProvider(BaseProvider):
    """Custom LLM provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        **kwargs
    ):
        """Initialize custom provider.

        Args:
            api_key: API key for authentication
            base_url: Base URL for API
            model: Model identifier
            **kwargs: Additional configuration
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
        """Generate text from prompt."""
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
        """Generate text from message history."""
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
        """Close the provider session."""
        await self.session.close()
```

## Registering Custom Providers

### Method 1: Using Registry

Register your provider in code:

```python
from llm4ad.infra.provider.base import BaseProvider
from llm4ad.utils.registry import Registry

# Get provider registry
provider_registry = Registry("provider", BaseProvider)

# Register your provider
@provider_registry.register("my_custom_provider")
class CustomProvider(BaseProvider):
    # ... implementation
    pass
```

### Method 2: Using Configuration

Specify provider type in config file:

```yaml
providers:
  - name: "custom"
    type: "my_custom_provider"  # Registered name
    api_key: "${API_KEY}"
    base_url: "https://api.example.com"
    model: "my-model"
```

## Using Custom Providers

Once registered, use your custom provider in configuration:

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

## Best Practices

1. **Async/Await**: Always use async methods for I/O operations
2. **Error Handling**: Handle API errors gracefully
3. **Rate Limiting**: Implement rate limiting if needed
4. **Session Management**: Reuse HTTP sessions for efficiency
5. **Timeouts**: Set reasonable timeouts for API calls

## Next Steps

- [Configuration Guide](configuration.md) - Configure providers
- [Writing Evaluators](evaluators.md) - Create custom evaluators
- [Quick Start Guide](quickstart.md) - Run your first experiment
