"""Unit tests for the stateless needs gathering core module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from llm4ad.consultant.core import (
    Choice,
    NeedsGatheringContext,
    NeedsGatheringResponse,
    ResponseType,
    default_file_reader,
    extract_needs_profile,
    process_needs_gathering_turn,
    process_needs_gathering_turn_stream,
)
from llm4ad.infra.provider.base import GenerationResult, StreamResponse


class _FakeStreamResponse(StreamResponse):
    """Fake stream that yields pre-defined chunks."""

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


def _make_provider(stream_text: str, tool_calls: list | None = None):
    """Create a mock provider that returns a fake stream."""
    provider = MagicMock()
    stream = _FakeStreamResponse(stream_text, tool_calls=tool_calls)
    provider.chat_stream = AsyncMock(return_value=stream)
    provider.generate = AsyncMock(
        return_value=GenerationResult(text='{"description": "test problem"}')
    )
    return provider


class TestProcessNeedsGatheringTurn:
    """Tests for the stateless process_needs_gathering_turn function."""

    @pytest.mark.asyncio
    async def test_kickoff_turn_returns_message(self):
        """First turn (no user_input) sends kickoff and returns LLM response."""
        provider = _make_provider("What problem would you like to solve?")
        ctx = NeedsGatheringContext(
            phase_messages=[],
            user_context=None,
            user_input=None,
        )

        response = await process_needs_gathering_turn(ctx, provider)

        assert response.response_type == ResponseType.MESSAGE
        assert "What problem" in response.assistant_message
        assert response.choices is None
        assert response.needs_profile is None
        assert len(response.updated_messages) == 2
        assert response.updated_messages[0]["role"] == "user"
        assert response.updated_messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_choices_detected_in_response(self):
        """Response with numbered choices returns CHOICES type."""
        text = (
            "What type of problem?\n\n"
            "  1) optimization — combinatorial\n"
            "  2) regression — curve fitting\n"
            "  3) Enter your own value\n"
        )
        provider = _make_provider(text)
        ctx = NeedsGatheringContext(
            phase_messages=[
                {"role": "user", "content": "kickoff"},
                {"role": "assistant", "content": "first response"},
            ],
            user_context=None,
            user_input="I want to design an algorithm",
        )

        response = await process_needs_gathering_turn(ctx, provider)

        assert response.response_type == ResponseType.CHOICES
        assert response.choices is not None
        assert len(response.choices) == 3
        assert response.choices[0].label == "optimization"
        assert response.choices[0].description == "combinatorial"
        assert response.choices[2].is_custom is True

    @pytest.mark.asyncio
    async def test_complete_marker_triggers_extraction(self):
        """Response with [NEEDS_COMPLETE] triggers extraction and returns COMPLETE."""
        text = "Great, I have everything I need.\n\n[NEEDS_COMPLETE]"
        provider = _make_provider(text)
        provider.generate = AsyncMock(
            return_value=GenerationResult(
                text='{"description": "TSP optimization", "language": "python"}'
            )
        )
        ctx = NeedsGatheringContext(
            phase_messages=[
                {"role": "user", "content": "kickoff"},
                {"role": "assistant", "content": "question"},
                {"role": "user", "content": "answer"},
            ],
            user_context=None,
            user_input="yes, that's correct",
        )

        response = await process_needs_gathering_turn(ctx, provider)

        assert response.response_type == ResponseType.COMPLETE
        assert response.needs_profile is not None
        assert response.needs_profile["description"] == "TSP optimization"
        assert "[NEEDS_COMPLETE]" not in response.assistant_message

    @pytest.mark.asyncio
    async def test_user_context_passed_to_prompt(self):
        """user_context is included in the system prompt."""
        provider = _make_provider("Got it, you're working on TSP.")
        ctx = NeedsGatheringContext(
            phase_messages=[],
            user_context="User has a TSP codebase at ./tsp/",
            user_input=None,
        )

        await process_needs_gathering_turn(ctx, provider)

        call_args = provider.chat_stream.call_args
        messages = call_args[0][0]
        system_msg = messages[0].content
        assert "User has a TSP codebase" in system_msg

    @pytest.mark.asyncio
    async def test_updated_messages_include_user_input(self):
        """updated_messages includes the user's input for this turn."""
        provider = _make_provider("Thanks for that info.")
        ctx = NeedsGatheringContext(
            phase_messages=[
                {"role": "user", "content": "kickoff"},
                {"role": "assistant", "content": "question"},
            ],
            user_context=None,
            user_input="my answer",
        )

        response = await process_needs_gathering_turn(ctx, provider)

        assert len(response.updated_messages) == 4
        assert response.updated_messages[2] == {"role": "user", "content": "my answer"}
        assert response.updated_messages[3]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_file_reader_called_on_tool_use(self):
        """Custom file_reader is called when LLM uses read_file tool."""
        from llm4ad.infra.provider.base import ToolCall

        tool_call = ToolCall(id="tc1", name="read_file", arguments={"path": "/tmp/test.py"})

        # First stream returns text + tool call, second returns final text
        first_stream = _FakeStreamResponse("Let me read that file.", tool_calls=[tool_call])
        second_stream = _FakeStreamResponse("I see it's a sorting algorithm.")

        provider = MagicMock()
        provider.chat_stream = AsyncMock(side_effect=[first_stream, second_stream])

        file_reader = MagicMock(return_value="def sort(arr): pass")

        ctx = NeedsGatheringContext(
            phase_messages=[],
            user_context=None,
            user_input=None,
        )

        response = await process_needs_gathering_turn(
            ctx, provider, file_reader=file_reader
        )

        file_reader.assert_called_once_with("/tmp/test.py")
        assert len(response.tool_calls_executed) == 1
        assert response.tool_calls_executed[0]["path"] == "/tmp/test.py"


class TestProcessNeedsGatheringTurnStream:
    """Tests for the streaming variant."""

    @pytest.mark.asyncio
    async def test_yields_chunks_then_response(self):
        """Stream yields text chunks followed by a NeedsGatheringResponse."""
        provider = _make_provider("Hello there!")
        ctx = NeedsGatheringContext(
            phase_messages=[],
            user_context=None,
            user_input=None,
        )

        chunks: list[str] = []
        final_response: NeedsGatheringResponse | None = None

        async for item in process_needs_gathering_turn_stream(ctx, provider):
            if isinstance(item, str):
                chunks.append(item)
            else:
                final_response = item

        assert len(chunks) == len("Hello there!")
        assert "".join(chunks) == "Hello there!"
        assert final_response is not None
        assert final_response.response_type == ResponseType.MESSAGE
        assert final_response.assistant_message == "Hello there!"

    @pytest.mark.asyncio
    async def test_stream_complete_yields_profile(self):
        """Stream with COMPLETE marker yields response with needs_profile."""
        text = "All done. [NEEDS_COMPLETE]"
        provider = _make_provider(text)
        provider.generate = AsyncMock(
            return_value=GenerationResult(
                text='{"description": "test", "language": "python"}'
            )
        )
        ctx = NeedsGatheringContext(
            phase_messages=[
                {"role": "user", "content": "kickoff"},
                {"role": "assistant", "content": "q"},
            ],
            user_context=None,
            user_input="confirmed",
        )

        final_response = None
        async for item in process_needs_gathering_turn_stream(ctx, provider):
            if isinstance(item, NeedsGatheringResponse):
                final_response = item

        assert final_response is not None
        assert final_response.response_type == ResponseType.COMPLETE
        assert final_response.needs_profile == {"description": "test", "language": "python"}


class TestExtractNeedsProfile:
    """Tests for the extract_needs_profile function."""

    @pytest.mark.asyncio
    async def test_extracts_json_from_response(self):
        """Extracts valid JSON from provider response."""
        provider = MagicMock()
        provider.generate = AsyncMock(
            return_value=GenerationResult(
                text='{"description": "TSP", "code_path": null, "language": "python"}'
            )
        )
        messages = [
            {"role": "user", "content": "I want TSP"},
            {"role": "assistant", "content": "Got it"},
        ]

        result = await extract_needs_profile(messages, provider)

        assert result["description"] == "TSP"
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_extracts_json_from_markdown_block(self):
        """Handles JSON wrapped in markdown code block."""
        provider = MagicMock()
        provider.generate = AsyncMock(
            return_value=GenerationResult(
                text='```json\n{"description": "sorting"}\n```'
            )
        )
        messages = [{"role": "user", "content": "sort"}]

        result = await extract_needs_profile(messages, provider)

        assert result["description"] == "sorting"

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self):
        """Returns fallback dict when JSON parsing fails."""
        provider = MagicMock()
        provider.generate = AsyncMock(
            return_value=GenerationResult(text="not valid json at all")
        )
        messages = [{"role": "user", "content": "x"}]

        result = await extract_needs_profile(messages, provider)

        assert result == {"description": ""}


class TestDefaultFileReader:
    """Tests for the default_file_reader function."""

    def test_reads_existing_file(self, tmp_path):
        """Reads content from an existing file."""
        f = tmp_path / "test.py"
        f.write_text("print('hello')")

        result = default_file_reader(str(f))

        assert result == "print('hello')"

    def test_returns_error_for_missing_file(self):
        """Returns error message for non-existent file."""
        result = default_file_reader("/nonexistent/path.py")

        assert "Error: File not found" in result

    def test_truncates_long_files(self, tmp_path):
        """Truncates files longer than 500 lines."""
        f = tmp_path / "long.py"
        f.write_text("\n".join(f"line {i}" for i in range(600)))

        result = default_file_reader(str(f))

        assert "truncated" in result
        assert "600 total lines" in result


class TestChoiceDataclass:
    """Tests for the Choice dataclass."""

    def test_choice_defaults(self):
        """Choice has correct defaults."""
        c = Choice(number=1, label="test", description="desc", full_text="test — desc")

        assert c.is_custom is False
        assert c.is_recommended is False

    def test_choice_custom_flag(self):
        """Choice can be marked as custom."""
        c = Choice(
            number=3, label="Other", description="",
            full_text="Other", is_custom=True,
        )

        assert c.is_custom is True


class TestNeedsGatheringContext:
    """Tests for the NeedsGatheringContext dataclass."""

    def test_empty_context(self):
        """Empty context has correct defaults."""
        ctx = NeedsGatheringContext()

        assert ctx.phase_messages == []
        assert ctx.user_context is None
        assert ctx.user_input is None

    def test_context_with_messages(self):
        """Context preserves messages."""
        msgs = [{"role": "user", "content": "hello"}]
        ctx = NeedsGatheringContext(phase_messages=msgs)

        assert ctx.phase_messages == msgs


class TestNeedsGatheringResponse:
    """Tests for the NeedsGatheringResponse dataclass."""

    def test_message_response(self):
        """MESSAGE response has no choices or profile."""
        r = NeedsGatheringResponse(
            response_type=ResponseType.MESSAGE,
            assistant_message="hello",
            updated_messages=[],
        )

        assert r.choices is None
        assert r.needs_profile is None
        assert r.tool_calls_executed == []

    def test_complete_response(self):
        """COMPLETE response has needs_profile."""
        r = NeedsGatheringResponse(
            response_type=ResponseType.COMPLETE,
            assistant_message="done",
            needs_profile={"description": "test"},
            updated_messages=[],
        )

        assert r.needs_profile == {"description": "test"}
