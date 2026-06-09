"""Unit tests for the review phase stateless core and ask_for_path detection."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from llm4ad.consultant.advisor import ParsedChoice, parse_choices
from llm4ad.consultant.core import (
    Choice,
    ReviewAction,
    ReviewContext,
    ReviewResponse,
    process_review_turn,
    process_review_turn_stream,
)
from llm4ad.infra.provider.base import StreamResponse


class _FakeStream(StreamResponse):
    """Fake stream yielding pre-defined text."""

    def __init__(self, text: str):
        super().__init__()
        self._chunks = list(text)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk


def _make_provider(stream_text: str):
    """Create a mock provider returning a fake stream."""
    provider = MagicMock()
    stream = _FakeStream(stream_text)
    provider.chat_stream = AsyncMock(return_value=stream)
    return provider


# ---------------------------------------------------------------------------
# Tests for ask_for_path detection via [PATH] tag
# ---------------------------------------------------------------------------


class TestAskForPathDetection:
    """Tests for [PATH] tag detection in parse_choices."""

    def test_path_tag_detected(self):
        """Choice with [PATH] tag sets ask_for_path=True."""
        response = (
            "Do you have existing code?\n\n"
            "  1) Yes, I have code [PATH] — provide the file path\n"
            "  2) No, start from scratch\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 2
        assert choices[0].ask_for_path is True
        assert choices[0].ask_for_dir is False
        assert choices[1].ask_for_path is False

    def test_path_tag_stripped_from_label(self):
        """[PATH] tag is stripped from the label text."""
        response = (
            "  1) Provide code path [PATH] — your algorithm file\n"
            "  2) Skip\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert "[PATH]" not in choices[0].label
        assert "[PATH]" not in choices[0].full_text
        assert choices[0].label == "Provide code path"

    def test_path_tag_case_insensitive(self):
        """[PATH] detection is case-insensitive."""
        response = (
            "  1) Code file [path] — provide path\n"
            "  2) No code\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_path is True

    def test_no_path_tag_default_false(self):
        """Choices without [PATH] have ask_for_path=False."""
        response = (
            "  1) Python — recommended\n"
            "  2) C++\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert all(c.ask_for_path is False for c in choices)

    def test_multiple_path_tags(self):
        """Multiple choices can have [PATH] tags."""
        response = (
            "  1) Code file [PATH] — algorithm source\n"
            "  2) Data file [PATH] — dataset location\n"
            "  3) Neither\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_path is True
        assert choices[1].ask_for_path is True
        assert choices[2].ask_for_path is False

    def test_path_tag_with_recommended(self):
        """[PATH] works alongside (recommended) marker."""
        response = (
            "  1) Existing code (recommended) [PATH] — provide path\n"
            "  2) Generate new\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_path is True
        assert choices[0].is_recommended is True
        assert choices[0].label == "Existing code"


class TestAskForDirDetection:
    """Tests for [DIR] tag detection in parse_choices."""

    def test_dir_tag_detected(self):
        """Choice with [DIR] tag sets ask_for_dir=True."""
        response = (
            "Do you have a project directory?\n\n"
            "  1) Yes, I have a project folder [DIR] — provide the directory path\n"
            "  2) No, start from scratch\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 2
        assert choices[0].ask_for_dir is True
        assert choices[0].ask_for_path is False
        assert choices[1].ask_for_dir is False

    def test_dir_tag_stripped_from_label(self):
        """[DIR] tag is stripped from the label text."""
        response = (
            "  1) Project directory [DIR] — your project folder\n"
            "  2) Skip\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert "[DIR]" not in choices[0].label
        assert "[DIR]" not in choices[0].full_text
        assert choices[0].label == "Project directory"

    def test_dir_tag_case_insensitive(self):
        """[DIR] detection is case-insensitive."""
        response = (
            "  1) Data folder [dir] — provide directory\n"
            "  2) No data\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_dir is True

    def test_no_dir_tag_default_false(self):
        """Choices without [DIR] have ask_for_dir=False."""
        response = (
            "  1) Python — recommended\n"
            "  2) C++\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert all(c.ask_for_dir is False for c in choices)

    def test_multiple_dir_tags(self):
        """Multiple choices can have [DIR] tags."""
        response = (
            "  1) Source directory [DIR] — algorithm source folder\n"
            "  2) Data directory [DIR] — dataset folder\n"
            "  3) Neither\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_dir is True
        assert choices[1].ask_for_dir is True
        assert choices[2].ask_for_dir is False

    def test_dir_tag_with_recommended(self):
        """[DIR] works alongside (recommended) marker."""
        response = (
            "  1) Existing project (recommended) [DIR] — provide directory\n"
            "  2) Generate new\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_dir is True
        assert choices[0].is_recommended is True
        assert choices[0].label == "Existing project"

    def test_path_and_dir_separate_choices(self):
        """[PATH] and [DIR] on separate choices work independently."""
        response = (
            "  1) Algorithm file [PATH] — provide the file path\n"
            "  2) Project directory [DIR] — provide the folder path\n"
            "  3) Neither\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].ask_for_path is True
        assert choices[0].ask_for_dir is False
        assert choices[1].ask_for_path is False
        assert choices[1].ask_for_dir is True
        assert choices[2].ask_for_path is False
        assert choices[2].ask_for_dir is False


# ---------------------------------------------------------------------------
# Tests for process_review_turn
# ---------------------------------------------------------------------------


class TestProcessReviewTurn:
    """Tests for the stateless review turn function."""

    @pytest.mark.asyncio
    async def test_confirmed_action(self):
        """Response with [CONFIRMED] returns CONFIRMED action."""
        provider = _make_provider(
            "Looks good! Everything is correct.\n\n[CONFIRMED]"
        )
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="You are reviewing code.",
            user_input=None,
            initial_message="Please review this evaluator.",
        )

        response = await process_review_turn(ctx, provider)

        assert response.action == ReviewAction.CONFIRMED
        assert "[CONFIRMED]" not in response.assistant_message
        assert response.modification_text is None

    @pytest.mark.asyncio
    async def test_modify_evaluator_action(self):
        """Response with [MODIFY_EVALUATOR] extracts modification text."""
        provider = _make_provider(
            "I'll modify the scoring.\n\n[MODIFY_EVALUATOR]\n"
            "Add a penalty for solutions exceeding time limit."
        )
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review prompt",
            user_input=None,
            initial_message="Review this code.",
        )

        response = await process_review_turn(ctx, provider)

        assert response.action == ReviewAction.MODIFY_EVALUATOR
        assert response.modification_text is not None
        assert "penalty" in response.modification_text
        assert "[MODIFY_EVALUATOR]" not in response.assistant_message

    @pytest.mark.asyncio
    async def test_regenerate_action(self):
        """Response with [REGENERATE] returns REGENERATE action."""
        provider = _make_provider("Let's start over.\n\n[REGENERATE]")
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review prompt",
            user_input=None,
            initial_message="Review this.",
        )

        response = await process_review_turn(ctx, provider)

        assert response.action == ReviewAction.REGENERATE
        assert response.modification_text is None

    @pytest.mark.asyncio
    async def test_pending_with_choices(self):
        """Response without markers returns PENDING with parsed choices."""
        text = (
            "What would you like to do?\n\n"
            "  1) Confirm and save — everything looks good\n"
            "  2) Modify the evaluator — change scoring\n"
            "  3) Regenerate — start over\n"
        )
        provider = _make_provider(text)
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review prompt",
            user_input=None,
            initial_message="Review this.",
        )

        response = await process_review_turn(ctx, provider)

        assert response.action == ReviewAction.PENDING
        assert response.choices is not None
        assert len(response.choices) == 3
        assert response.choices[0].label == "Confirm and save"

    @pytest.mark.asyncio
    async def test_pending_plain_message(self):
        """Response without markers or choices returns PENDING with no choices."""
        provider = _make_provider("Can you tell me more about what you'd like?")
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review prompt",
            user_input=None,
            initial_message="Review this.",
        )

        response = await process_review_turn(ctx, provider)

        assert response.action == ReviewAction.PENDING
        assert response.choices is None

    @pytest.mark.asyncio
    async def test_user_input_appended(self):
        """User input is appended to phase_messages in updated_messages."""
        provider = _make_provider("Got it.\n\n[CONFIRMED]")
        ctx = ReviewContext(
            phase_messages=[
                {"role": "user", "content": "initial"},
                {"role": "assistant", "content": "what do you think?"},
            ],
            system_prompt="Review prompt",
            user_input="looks good, confirm",
        )

        response = await process_review_turn(ctx, provider)

        assert response.action == ReviewAction.CONFIRMED
        assert len(response.updated_messages) == 4
        assert response.updated_messages[2]["content"] == "looks good, confirm"
        assert response.updated_messages[3]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_initial_message_used_on_first_turn(self):
        """initial_message is used as user message when user_input is None."""
        provider = _make_provider("Here's the explanation.\n\n[CONFIRMED]")
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review prompt",
            user_input=None,
            initial_message="Explain this evaluator code.",
        )

        response = await process_review_turn(ctx, provider)

        assert response.updated_messages[0]["role"] == "user"
        assert response.updated_messages[0]["content"] == "Explain this evaluator code."


class TestProcessReviewTurnStream:
    """Tests for the streaming review turn function."""

    @pytest.mark.asyncio
    async def test_yields_chunks_then_response(self):
        """Stream yields text chunks followed by ReviewResponse."""
        provider = _make_provider("All good.\n\n[CONFIRMED]")
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review",
            user_input=None,
            initial_message="Review this.",
        )

        chunks: list[str] = []
        final: ReviewResponse | None = None
        async for item in process_review_turn_stream(ctx, provider):
            if isinstance(item, str):
                chunks.append(item)
            else:
                final = item

        assert len(chunks) > 0
        assert "".join(chunks) == "All good.\n\n[CONFIRMED]"
        assert final is not None
        assert final.action == ReviewAction.CONFIRMED

    @pytest.mark.asyncio
    async def test_stream_pending_with_choices(self):
        """Streaming with no marker yields PENDING response."""
        text = (
            "Options:\n\n"
            "  1) Confirm — save it\n"
            "  2) Modify — change it\n"
        )
        provider = _make_provider(text)
        ctx = ReviewContext(
            phase_messages=[],
            system_prompt="Review",
            user_input=None,
            initial_message="Review.",
        )

        final = None
        async for item in process_review_turn_stream(ctx, provider):
            if not isinstance(item, str):
                final = item

        assert final is not None
        assert final.action == ReviewAction.PENDING
        assert final.choices is not None
        assert len(final.choices) == 2
