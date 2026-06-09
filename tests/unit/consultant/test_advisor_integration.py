"""Integration tests for the CLI adapter (LLMAdvisor.run_needs_gathering).

Tests that the refactored advisor correctly drives the stateless core
function with CLI-specific I/O mocked out.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from rich.console import Console

from llm4ad.consultant.advisor import LLMAdvisor
from llm4ad.consultant.state import ConversationState
from llm4ad.infra.provider.base import GenerationResult, StreamResponse, ToolCall


class _FakeStream(StreamResponse):
    """Fake stream yielding pre-defined text."""

    def __init__(self, text: str, tool_calls: list | None = None):
        super().__init__()
        self._chunks = list(text)
        self._index = 0
        if tool_calls:
            self.tool_calls = tool_calls

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk


class TestAdvisorNeedsGathering:
    """Tests for LLMAdvisor.run_needs_gathering using the core function."""

    @pytest.fixture
    def advisor(self):
        """Create an advisor with mocked provider and console."""
        provider = MagicMock()
        console = Console(file=StringIO())
        state = ConversationState(session_id="test")
        return LLMAdvisor(provider=provider, console=console, state=state)

    @pytest.mark.asyncio
    async def test_simple_two_turn_conversation(self, advisor):
        """Advisor completes a two-turn conversation via core function."""
        # Turn 1: LLM asks a question
        stream1 = _FakeStream("What problem do you want to solve?")
        # Turn 2: LLM completes
        stream2 = _FakeStream("Got it, all done.\n\n[NEEDS_COMPLETE]")

        advisor._provider.chat_stream = AsyncMock(side_effect=[stream1, stream2])
        advisor._provider.generate = AsyncMock(
            return_value=GenerationResult(
                text='{"description": "TSP optimization", "language": "python"}'
            )
        )

        # Mock user input
        advisor._get_user_input = AsyncMock(return_value="I want to optimize TSP routes")

        result = await advisor.run_needs_gathering()

        assert result["description"] == "TSP optimization"
        assert result["language"] == "python"
        assert len(advisor._state.messages) >= 4

    @pytest.mark.asyncio
    async def test_choices_trigger_interactive_select(self, advisor):
        """When LLM returns choices, _interactive_select_from_core_choices is called."""
        text_with_choices = (
            "What type?\n\n"
            "  1) optimization — combinatorial\n"
            "  2) regression — fitting\n"
            "  3) Enter your own value\n"
        )
        stream1 = _FakeStream(text_with_choices)
        stream2 = _FakeStream("Perfect.\n\n[NEEDS_COMPLETE]")

        advisor._provider.chat_stream = AsyncMock(side_effect=[stream1, stream2])
        advisor._provider.generate = AsyncMock(
            return_value=GenerationResult(text='{"description": "optimization"}')
        )

        # Mock the choice selector
        async def mock_select(choices):
            assert len(choices) == 3
            assert choices[0].label == "optimization"
            return "optimization"

        advisor._interactive_select_from_core_choices = mock_select

        result = await advisor.run_needs_gathering()

        assert result["description"] == "optimization"

    @pytest.mark.asyncio
    async def test_quit_raises_keyboard_interrupt(self, advisor):
        """User typing 'quit' raises KeyboardInterrupt."""
        stream1 = _FakeStream("What problem?")
        advisor._provider.chat_stream = AsyncMock(return_value=stream1)

        advisor._get_user_input = AsyncMock(return_value="quit")

        with pytest.raises(KeyboardInterrupt):
            await advisor.run_needs_gathering()

    @pytest.mark.asyncio
    async def test_tool_calls_logged(self, advisor):
        """Tool calls from the core are logged to console."""
        tool_call = ToolCall(id="tc1", name="read_file", arguments={"path": "/tmp/x.py"})
        stream1 = _FakeStream("Reading file...", tool_calls=[tool_call])
        stream2 = _FakeStream("I see sorting code.")
        stream3 = _FakeStream("All done.\n\n[NEEDS_COMPLETE]")

        advisor._provider.chat_stream = AsyncMock(
            side_effect=[stream1, stream2, stream3]
        )
        advisor._provider.generate = AsyncMock(
            return_value=GenerationResult(text='{"description": "sort"}')
        )
        advisor._get_user_input = AsyncMock(return_value="yes")

        result = await advisor.run_needs_gathering()

        assert result["description"] == "sort"

    @pytest.mark.asyncio
    async def test_state_messages_updated(self, advisor):
        """State messages are updated after each turn."""
        stream1 = _FakeStream("Question?")
        stream2 = _FakeStream("Done.\n\n[NEEDS_COMPLETE]")

        advisor._provider.chat_stream = AsyncMock(side_effect=[stream1, stream2])
        advisor._provider.generate = AsyncMock(
            return_value=GenerationResult(text='{"description": "x"}')
        )
        advisor._get_user_input = AsyncMock(return_value="answer")

        await advisor.run_needs_gathering()

        # Should have: kickoff user msg, assistant response, user answer, assistant complete
        assert len(advisor._state.messages) == 4
        assert advisor._state.messages[0]["role"] == "user"
        assert advisor._state.messages[1]["role"] == "assistant"
        assert advisor._state.messages[2]["role"] == "user"
        assert advisor._state.messages[2]["content"] == "answer"
        assert advisor._state.messages[3]["role"] == "assistant"
