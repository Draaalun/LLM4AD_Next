"""Tests for planner memory extraction."""

from types import SimpleNamespace

import pytest

from llm4ad.config.memory import AutoExtractionConfig
from llm4ad.planner.memory import MemoryExtractor, MemoryType


class _ProviderReturningDeepSeekStyleSchema:
    async def generate(self, prompt, *, schema, **kwargs):
        parsed = schema.model_validate({
            "name": "Nearest Neighbor Insight",
            "description": "Prefer nearest-neighbor construction followed by local improvement.",
        })
        return SimpleNamespace(parsed=parsed)


def _algorithm(name: str, score: float):
    return SimpleNamespace(
        id=name.lower().replace(" ", "-"),
        name=name,
        score=score,
        description="A simple heuristic.",
        evaluation=None,
        is_evaluated=lambda: True,
    )


@pytest.mark.asyncio
async def test_extract_from_good_accepts_name_description_schema_aliases():
    extractor = MemoryExtractor(
        _ProviderReturningDeepSeekStyleSchema(),
        AutoExtractionConfig(good_relative_threshold=0.5),
    )
    algorithm = _algorithm("Nearest Neighbor", 10.0)
    population = [algorithm, _algorithm("Baseline", 1.0)]

    card = await extractor.extract_from_good(algorithm, population, generation=3)

    assert card is not None
    assert card.type is MemoryType.GOOD_ALGORITHM
    assert card.title == "Nearest Neighbor Insight"
    assert card.content == "Prefer nearest-neighbor construction followed by local improvement."


@pytest.mark.asyncio
async def test_extract_from_bad_accepts_name_description_schema_aliases():
    extractor = MemoryExtractor(
        _ProviderReturningDeepSeekStyleSchema(),
        AutoExtractionConfig(bad_relative_threshold=0.5),
    )
    algorithm = _algorithm("Centroid Start", 1.0)
    population = [algorithm, _algorithm("Better", 10.0)]

    card = await extractor.extract_from_bad(algorithm, population, generation=3)

    assert card is not None
    assert card.type is MemoryType.ERROR_REFLECTION
    assert card.title == "Nearest Neighbor Insight"
    assert card.content == "Prefer nearest-neighbor construction followed by local improvement."
