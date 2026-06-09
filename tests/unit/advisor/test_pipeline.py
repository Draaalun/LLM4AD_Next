"""Integration-style test of the full advisor pipeline with a mocked LLM."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from llm4ad.advisor.analyzer import BlockAdvisor, _parse_json_response
from llm4ad.infra.provider.base import GenerationResult
from llm4ad.infra.repo_analyzer.base import EvolveBlock


class _FakeProvider:
    """Minimal provider stub — only implements what BlockAdvisor calls."""

    def __init__(self, text: str):
        self._text = text
        self.calls: list[str] = []

    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        self.calls.append(prompt)
        return GenerationResult(text=self._text)


def _make_block() -> EvolveBlock:
    return EvolveBlock(
        file_path="algo.py",
        absolute_path=Path("algo.py"),
        line_start=10,
        line_end=20,
        comment_style="#",
        block_name="sort",
        original_content="def sort(a):\n    return sorted(a)",
        context_before="import sys",
        context_after="print('done')",
        language="python",
    )


def test_advisor_parses_clean_json_response():
    """End-to-end: provider returns JSON, advisor returns populated BlockAdvice."""
    payload = {
        "block_summary": "Delegates to built-in sorted().",
        "feasibility": "partial",
        "feasibility_reason": "Only the sort is here.",
        "significance": "medium",
        "significance_reason": "Sort is a hot path but bounded.",
        "concerns": ["sorted() is already near-optimal."],
        "suggestions": ["Expand block to include the comparator."],
        "rationale": "Worth trying but consider widening the selection.",
    }
    provider = _FakeProvider(json.dumps(payload))
    advisor = BlockAdvisor(provider)

    advice = asyncio.run(advisor.advise("minimize comparisons", _make_block()))

    assert advice.feasibility == "partial"
    assert advice.significance == "medium"
    assert "sorted()" in advice.concerns[0]
    assert advice.block_ref is not None
    assert advice.block_ref["file_path"] == "algo.py"
    assert len(provider.calls) == 1
    assert "minimize comparisons" in provider.calls[0]
    assert "def sort(a)" in provider.calls[0]


def test_advisor_tolerates_markdown_fenced_json():
    """Responses wrapped in ```json ... ``` must still parse."""
    payload = {"feasibility": "yes", "significance": "high"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    provider = _FakeProvider(fenced)
    advisor = BlockAdvisor(provider)

    advice = asyncio.run(advisor.advise("goal", _make_block()))

    assert advice.feasibility == "yes"
    assert advice.significance == "high"


def test_advisor_falls_back_when_json_unparseable():
    """Garbage responses keep the advisor alive — raw text goes to rationale."""
    provider = _FakeProvider("sorry, i cannot comply")
    advisor = BlockAdvisor(provider)

    advice = asyncio.run(advisor.advise("goal", _make_block()))

    assert advice.feasibility == ""
    assert advice.rationale == "sorry, i cannot comply"
    assert advice.block_ref is not None


@pytest.mark.parametrize(
    "text,expected_key",
    [
        ('{"a": 1}', "a"),
        ('```\n{"b": 2}\n```', "b"),
        ('noise before {"c": 3} noise after', "c"),
    ],
)
def test_parse_json_response_handles_common_shapes(text: str, expected_key: str):
    """The tolerant JSON extractor covers plain, fenced, and prose-wrapped outputs."""
    parsed = _parse_json_response(text)
    assert parsed is not None
    assert expected_key in parsed


def test_parse_json_response_returns_none_on_junk():
    """Non-JSON text must return None, not raise."""
    assert _parse_json_response("just some prose") is None


# ----------------------------------------------------------------------
# Language threading (--lang en|zh)
# ----------------------------------------------------------------------


def test_advisor_default_lang_is_en():
    """advisor.advise() with no lang produces an English prompt and BlockAdvice.lang=='en'."""
    provider = _FakeProvider('{"feasibility": "yes"}')
    advisor = BlockAdvisor(provider)

    advice = asyncio.run(advisor.advise("goal", _make_block()))

    assert "中文" not in provider.calls[0]
    assert "{lang_directive}" not in provider.calls[0]
    assert advice.lang == "en"
    assert advice.to_dict()["lang"] == "en"


def test_advisor_lang_zh_injects_directive():
    """advisor.advise(lang='zh') prepends a Simplified-Chinese directive."""
    provider = _FakeProvider('{"feasibility": "yes"}')
    advisor = BlockAdvisor(provider)

    advice = asyncio.run(advisor.advise("goal", _make_block(), lang="zh"))

    assert "Simplified Chinese" in provider.calls[0]
    assert "中文" in provider.calls[0]
    assert advice.lang == "zh"
    assert advice.to_dict()["lang"] == "zh"


def test_advisor_lang_zh_preserves_json_keys_in_prompt():
    """The directive only constrains free text; JSON keys stay in the prompt."""
    provider = _FakeProvider('{"feasibility": "yes"}')
    advisor = BlockAdvisor(provider)

    asyncio.run(advisor.advise("goal", _make_block(), lang="zh"))

    body = provider.calls[0]
    # Schema keys must still appear so the LLM emits parseable JSON.
    for key in ("block_summary", "feasibility", "significance", "concerns", "suggestions"):
        assert key in body
