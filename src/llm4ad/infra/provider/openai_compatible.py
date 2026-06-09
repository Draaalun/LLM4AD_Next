"""OpenAI-compatible API provider for self-hosted LLMs.

Works with any API that implements the OpenAI chat completions protocol,
including local models run with vLLM, Ollama, Llama.cpp, Text Generation WebUI, etc.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger
from openai import APIStatusError, AsyncOpenAI
from pydantic import BaseModel

from llm4ad.infra.provider.base import (
    BaseProvider,
    ChatMessage,
    ContentPart,
    GenerationResult,
    StreamResponse,
    ToolCall,
    ToolDefinition,
)
from llm4ad.infra.timing import ExecutionTiming


@BaseProvider.register("openai")
@BaseProvider.register("openai_compatible")
class OpenAICompatibleProvider(BaseProvider):
    """OpenAI-compatible API provider.

    Supports any self-hosted or third-party API that implements the OpenAI
    chat completions interface.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize OpenAI-compatible provider.

        Args:
            config: Provider configuration:
                - api_key: API key for authentication (use "EMPTY" for unauthenticated endpoints)
                - base_url: API base URL (e.g. "http://localhost:8000/v1")
                - model: Model name to use
                - timeout: Request timeout in seconds (default: 60)
                - max_retries: Maximum retry attempts (default: 3)
                - input_cost_per_million: Cost per million input tokens (USD, default: 0.0)
                - output_cost_per_million: Cost per million output tokens (USD, default: 0.0)
        """
        super().__init__(config)

        # Initialize async OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key or "EMPTY",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        # Cost settings
        self.input_cost_per_million = config.get("input_cost_per_million", 0.0)
        self.output_cost_per_million = config.get("output_cost_per_million", 0.0)

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert internal ChatMessage format to OpenAI format.

        Args:
            messages: List of ChatMessage objects.

        Returns:
            List of OpenAI-format message dicts.
        """
        openai_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "assistant" and msg.tool_calls:
                msg_dict: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
                if msg.reasoning_content:
                    msg_dict["reasoning_content"] = msg.reasoning_content
            elif msg.role == "tool":
                msg_dict = {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                }
            else:
                msg_dict = {"role": msg.role, "content": self._convert_content(msg.content)}
                if msg.name:
                    msg_dict["name"] = msg.name
                if msg.role == "assistant" and msg.reasoning_content:
                    msg_dict["reasoning_content"] = msg.reasoning_content
            openai_messages.append(msg_dict)
        return openai_messages

    @staticmethod
    def _convert_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert ToolDefinition list to OpenAI tools format.

        Args:
            tools: List of ToolDefinition objects.

        Returns:
            List of OpenAI-format tool dicts.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    async def generate(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate text from a simple prompt."""
        messages = [ChatMessage(role="user", content=prompt)]
        return await self.chat(messages, schema=schema, **kwargs)

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Generate streaming text from a simple prompt."""
        messages = [ChatMessage(role="user", content=prompt)]
        stream = await self.chat_stream(messages, **kwargs)
        async for chunk in stream:
            yield chunk

    async def chat(
        self,
        messages: list[ChatMessage],
        schema: type[BaseModel] | None = None,
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> GenerationResult:
        """Chat with messages.

        Args:
            messages: List of chat messages.
            schema: Optional Pydantic BaseModel to parse the response into.
            tools: Optional list of tool definitions the LLM can call.
            **kwargs: Additional generation parameters.
        """
        start_time = time.time()

        # Pop LLM4AD-internal kwargs that must not reach the OpenAI SDK
        request_stage = kwargs.pop("request_stage", "")

        # Convert internal ChatMessage format to OpenAI format
        openai_messages = self._convert_messages(messages)

        # Add output format instruction to the last user message if schema is provided
        format_instruction = ""
        if schema is not None:
            schema_json = schema.model_json_schema()
            format_instruction = (
                f"\n\nRespond in JSON format with the following schema:\n"
                f"{json.dumps(schema_json, indent=2)}\n"
                f"Only output the JSON, no other text."
            )
            # Append format instruction to the last user message
            for msg in reversed(openai_messages):
                if msg["role"] == "user":
                    if isinstance(msg["content"], str):
                        msg["content"] += format_instruction
                    elif isinstance(msg["content"], list):
                        msg["content"].append({"type": "text", "text": format_instruction})
                    break

        # Log prompt at TRACE level
        logger.trace(f"===== PROMPT (model={self.model}) =====\n{openai_messages[-1]['content']}")

        # Build create kwargs
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "stream": False,
            **kwargs,
        }
        if tools:
            create_kwargs["tools"] = self._convert_tools(tools)

        # If no schema, just call API once without retry logic
        if schema is None:
            response = await self.client.chat.completions.create(**create_kwargs)

            latency_ms = (time.time() - start_time) * 1000
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0

            logger.trace(f"===== RESPONSE (model={response.model}) =====\n{response.choices[0].message.content}")

            # Parse tool_calls from response
            result_tool_calls = self._parse_tool_calls(response.choices[0].message)

            return GenerationResult(
                text=response.choices[0].message.content or "",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
                latency_ms=latency_ms,
                model=response.model,
                finish_reason=response.choices[0].finish_reason or "stop",
                request_stage=request_stage,
                metadata={
                    "id": response.id,
                    "created": response.created,
                    "system_fingerprint": response.system_fingerprint,
                },
                parsed=None,
                timing=ExecutionTiming.from_llm_stage(request_stage, latency_ms),
                tool_calls=result_tool_calls,
            )

        # Call API with retry logic for JSON parsing errors
        max_parse_retries = 3

        for attempt in range(max_parse_retries):
            try:
                response = await self.client.chat.completions.create(**create_kwargs)

                latency_ms = (time.time() - start_time) * 1000

                # Extract usage information
                prompt_tokens = response.usage.prompt_tokens if response.usage else 0
                completion_tokens = response.usage.completion_tokens if response.usage else 0
                total_tokens = response.usage.total_tokens if response.usage else 0

                # Log response at TRACE level
                logger.trace(f"===== RESPONSE (model={response.model}) =====\n{response.choices[0].message.content}")

                # Parse response if schema was provided
                parsed_result = None
                if schema is not None:
                    try:
                        content = response.choices[0].message.content or ""
                        # Extract JSON from response (handle potential markdown code blocks)
                        json_str = content.strip()
                        if json_str.startswith("```json"):
                            json_str = json_str[7:]
                        elif json_str.startswith("```"):
                            json_str = json_str[3:]
                        if json_str.endswith("```"):
                            json_str = json_str[:-3]
                        json_str = json_str.strip()

                        parsed_result = schema.model_validate_json(json_str)
                    except Exception as e:
                        logger.warning(f"Failed to parse schema (attempt {attempt + 1}/{max_parse_retries}): {e}")

                        if attempt < max_parse_retries - 1:
                            # Add error feedback to prompt for retry
                            error_feedback = f"\n\nJSON parsing error: {e}\nPlease fix the JSON format and respond again."
                            for msg in reversed(openai_messages):
                                if msg["role"] == "user":
                                    msg["content"] += error_feedback
                                    break
                            logger.info(f"Retrying with error feedback (attempt {attempt + 2}/{max_parse_retries})")
                            continue
                        else:
                            parsed_result = None

                # Parse tool_calls from response
                result_tool_calls = self._parse_tool_calls(response.choices[0].message)

                # Build result
                return GenerationResult(
                    text=response.choices[0].message.content or "",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
                    latency_ms=latency_ms,
                    model=response.model,
                    finish_reason=response.choices[0].finish_reason or "stop",
                    request_stage=request_stage,
                    metadata={
                        "id": response.id,
                        "created": response.created,
                        "system_fingerprint": response.system_fingerprint,
                    },
                    parsed=parsed_result,
                    timing=ExecutionTiming.from_llm_stage(request_stage, latency_ms),
                    tool_calls=result_tool_calls,
                )

            except APIStatusError as e:
                if e.status_code in (429, 502, 503, 529) and attempt < max_parse_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "API returned %d, retrying in %ds (attempt %d/%d): %s",
                        e.status_code, wait, attempt + 1, max_parse_retries, e,
                    )
                    await asyncio.sleep(wait)
                    start_time = time.time()
                    continue
                logger.error(f"API call failed: {e}")
                raise
            except Exception as e:
                logger.error(f"API call failed: {e}")
                raise

        # Fallback: all retries exhausted, return result with parsed=None
        response = await self.client.chat.completions.create(**create_kwargs)

        latency_ms = (time.time() - start_time) * 1000
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = response.usage.total_tokens if response.usage else 0

        logger.trace(f"===== RESPONSE (fallback, model={response.model}) =====\n{response.choices[0].message.content}")

        result_tool_calls = self._parse_tool_calls(response.choices[0].message)

        return GenerationResult(
            text=response.choices[0].message.content or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
            latency_ms=latency_ms,
            model=response.model,
            finish_reason=response.choices[0].finish_reason or "stop",
            request_stage=request_stage,
            metadata={
                "id": response.id,
                "created": response.created,
                "system_fingerprint": response.system_fingerprint,
            },
            parsed=None,
            timing=ExecutionTiming.from_llm_stage(request_stage, latency_ms),
            tool_calls=result_tool_calls,
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> StreamResponse:
        """Chat with streaming response.

        Args:
            messages: List of chat messages.
            tools: Optional list of tool definitions the LLM can call.
            **kwargs: Additional generation parameters.

        Returns:
            StreamResponse that yields text chunks and captures tool calls.
        """
        openai_messages = self._convert_messages(messages)

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "stream": True,
            **kwargs,
        }
        if tools:
            create_kwargs["tools"] = self._convert_tools(tools)

        raw_stream = await self.client.chat.completions.create(**create_kwargs)
        response = StreamResponse()

        async def _generate() -> AsyncIterator[str]:
            tool_call_accum: dict[int, dict[str, str]] = {}
            reasoning_parts: list[str] = []
            async for chunk in raw_stream:
                if chunk.choices and (content := getattr(chunk.choices[0].delta, "content", None)):
                    yield content
                # Accumulate reasoning_content for DeepSeek thinking mode
                if chunk.choices:
                    rc = getattr(chunk.choices[0].delta, "reasoning_content", None)
                    if rc:
                        reasoning_parts.append(rc)
                # Accumulate tool call deltas
                if chunk.choices and getattr(chunk.choices[0].delta, "tool_calls", None):
                    for tc_delta in chunk.choices[0].delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_accum:
                            tool_call_accum[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.id:
                            tool_call_accum[idx]["id"] = tc_delta.id
                        if tc_delta.function and tc_delta.function.name:
                            tool_call_accum[idx]["name"] = tc_delta.function.name
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_call_accum[idx]["arguments"] += tc_delta.function.arguments
            # Capture reasoning_content for DeepSeek thinking mode
            if reasoning_parts:
                response.reasoning_content = "".join(reasoning_parts)
            # Stream exhausted — parse accumulated tool calls
            for idx in sorted(tool_call_accum):
                data = tool_call_accum[idx]
                args = json.loads(data["arguments"]) if data["arguments"] else {}
                response.tool_calls.append(
                    ToolCall(id=data["id"], name=data["name"], arguments=args)
                )

        response._gen = _generate()
        return response

    @staticmethod
    def _parse_tool_calls(message: Any) -> list[ToolCall] | None:
        """Parse tool calls from an OpenAI response message.

        Args:
            message: OpenAI response message object.

        Returns:
            List of ToolCall objects, or None if no tool calls.
        """
        if not message.tool_calls:
            return None
        return [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
            )
            for tc in message.tool_calls
        ]

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text (simple approximation)."""
        # Simple character-based approximation: ~4 characters per token for English
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model."""
        return {
            "name": self.model,
            "provider": "openai_compatible",
            "base_url": self.base_url,
            "input_cost_per_million": self.input_cost_per_million,
            "output_cost_per_million": self.output_cost_per_million,
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost of a request based on configured token prices."""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost

    @staticmethod
    def _convert_content(content: str | list[ContentPart]) -> str | list[dict]:
        """Convert ChatMessage content to OpenAI API format.

        Args:
            content: Plain text string or list of ContentPart objects.

        Returns:
            String for text-only, or list of dicts for multimodal content.
        """
        if isinstance(content, str):
            return content
        parts = []
        for part in content:
            if part.type == "text" and part.text is not None:
                parts.append({"type": "text", "text": part.text})
            elif part.type == "image_url" and part.image_url is not None:
                parts.append({"type": "image_url", "image_url": part.image_url})
        return parts


if __name__ == "__main__":
    import asyncio
    import os

    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    async def main():
        """Main function for debugging the OpenAI-compatible provider."""
        # Configuration - modify these values for debugging
        config = {
            "base_url": os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            "model": os.getenv("OPENAI_MODEL", "glm-4.7-flash"),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "timeout": 120,
            "max_retries": 2,
        }

        print(config)

        provider = OpenAICompatibleProvider(config)

        # Debug: print provider info
        print("Provider configuration:")
        print(provider.get_model_info())
        print("\n" + "=" * 50 + "\n")

        # Test simple generation
        prompt = "Hello, what's your name and what's your hobby?"
        print(f"Prompt: {prompt}")
        print("\nGenerating response...\n")

        class PersonInfo(BaseModel):
            name: str
            hobby: str

        result = await provider.generate(prompt, schema=PersonInfo)

        # Debug: print full result details
        print("Response received:")
        print(f"Text: {result.text}")
        print(
            f"\nUsage: {result.prompt_tokens} input + {result.completion_tokens} "
            f"output = {result.total_tokens} tokens"
        )
        print(f"Cost: ${result.cost_usd:.6f}")
        print(f"Latency: {result.latency_ms:.2f}ms")
        print(f"Finish reason: {result.finish_reason}")
        print(f"Model: {result.model}")

        # Optional: Test streaming
        # print("\n" + "="*50 + "\n")
        # print("Streaming response test:\n")
        # async for chunk in provider.generate_stream("Write a 2 sentence poem about AI:"):
        #     print(chunk, end="", flush=True)
        # print("\n")

    asyncio.run(main())
