"""End-to-end test of the repo recommender with a mocked LLM."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from llm4ad.advisor.recommendation import BlockRecommendation, RepoRecommendations
from llm4ad.advisor.recommender import RepoRecommender
from llm4ad.infra.provider.base import GenerationResult


class _FakeProvider:
    """Minimal provider stub — one canned response per call, in order."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[str] = []

    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        self.calls.append(prompt)
        if not self._responses:
            return GenerationResult(text="{}")
        return GenerationResult(text=self._responses.pop(0))


def _write_repo(root: Path) -> None:
    """Create a tiny fake repo the LLM (fake) can reason about."""
    (root / "README.md").write_text(
        "# Sample TSP solver\n\nMinimize total tour length.\n",
        encoding="utf-8",
    )
    algo = root / "algo.py"
    algo.write_text(
        "\n".join(
            [
                "import random",                # 1
                "",                              # 2
                "def distance(a, b):",           # 3
                "    return abs(a - b)",         # 4
                "",                              # 5
                "def nearest_neighbor(nodes):",  # 6
                "    tour = [nodes[0]]",         # 7
                "    remaining = set(nodes[1:])",# 8
                "    while remaining:",          # 9
                "        last = tour[-1]",       # 10
                "        nxt = min(remaining, key=lambda n: distance(last, n))",  # 11
                "        tour.append(nxt)",     # 12
                "        remaining.discard(nxt)",# 13
                "    return tour",               # 14
                "",                              # 15
                "def main():",                   # 16
                "    print(nearest_neighbor([1, 5, 3, 9, 2]))",  # 17
            ]
        ),
        encoding="utf-8",
    )


def _advice_json(feasibility: str = "yes", significance: str = "high") -> str:
    return json.dumps({
        "block_summary": "Iteratively picks the nearest unvisited node.",
        "feasibility": feasibility,
        "feasibility_reason": "This is the hot path for tour length.",
        "significance": significance,
        "significance_reason": "Replacing the greedy heuristic has direct impact.",
        "concerns": ["assumes nodes are integers"],
        "suggestions": ["consider 2-opt swap"],
        "rationale": "Strong candidate.",
    })


# ----------------------------------------------------------------------
# Happy path
# ----------------------------------------------------------------------

def test_recommender_happy_path(tmp_path: Path):
    """Discovery returns core+expanded+alternative, each is advised, tiers populated."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {
            "file_path": "algo.py",
            "line_start": 6,
            "line_end": 14,
            "rationale": "This is the greedy solver.",
        },
        "expanded": [
            {
                "file_path": "algo.py",
                "line_start": 3,
                "line_end": 14,
                "rationale": "Include the helper distance().",
            }
        ],
        "alternatives": [
            {
                "file_path": "algo.py",
                "line_start": 16,
                "line_end": 17,
                "rationale": "Pick main() to control inputs.",
            }
        ],
    })
    # 1 discovery call + 3 advice calls.
    provider = _FakeProvider([discovery] + [_advice_json()] * 3)
    recommender = RepoRecommender(provider, max_concurrency=3)

    result = asyncio.run(recommender.recommend("Minimize TSP tour length", tmp_path))

    assert isinstance(result, RepoRecommendations)
    assert result.core is not None
    assert result.core.tier == "core"
    assert result.core.file_path == "algo.py"
    assert result.core.line_start == 6 and result.core.line_end == 14
    assert result.core.size_lines == 9
    assert result.core.advice is not None
    assert result.core.advice.feasibility == "yes"

    assert len(result.expanded) == 1
    assert result.expanded[0].tier == "expanded"
    assert result.expanded[0].variant_index == 0
    assert result.expanded[0].line_start == 3
    assert result.expanded[0].line_end == 14

    assert len(result.alternatives) == 1
    assert result.alternatives[0].tier == "alternative"
    assert result.alternatives[0].line_start == 16

    assert result.dropped_candidates == []
    # First call is discovery, remaining are advice.
    assert len(provider.calls) == 4


def test_recommender_json_roundtrip(tmp_path: Path):
    """Result.to_dict() should be JSON-serializable end to end."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    payload = json.dumps(result.to_dict())
    parsed = json.loads(payload)
    assert parsed["core"]["file_path"] == "algo.py"
    assert parsed["core"]["advice"]["feasibility"] == "yes"


# ----------------------------------------------------------------------
# Validation: each drop reason
# ----------------------------------------------------------------------

def test_drops_file_not_found(tmp_path: Path):
    """Candidate pointing at a non-existent file is dropped with the right reason."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [
            {"file_path": "missing.py", "line_start": 1, "line_end": 5, "rationale": "y"}
        ],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.alternatives == []
    assert len(result.dropped_candidates) == 1
    assert result.dropped_candidates[0]["reason"] == "file_not_found"
    assert result.dropped_candidates[0]["tier"] == "alternative"


def test_drops_range_out_of_bounds(tmp_path: Path):
    """Line range exceeding file length drops with range_out_of_bounds."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [
            {"file_path": "algo.py", "line_start": 50, "line_end": 99, "rationale": "y"}
        ],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.alternatives == []
    assert result.dropped_candidates[0]["reason"] == "range_out_of_bounds"


def test_drops_invalid_range(tmp_path: Path):
    """Ranges with start < 1 or end < start drop with invalid_range."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [
            {"file_path": "algo.py", "line_start": 10, "line_end": 5, "rationale": "y"}
        ],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.alternatives == []
    assert result.dropped_candidates[0]["reason"] == "invalid_range"


def test_drops_escaped_repo(tmp_path: Path):
    """Paths that resolve outside the repo are dropped as escaped_repo."""
    _write_repo(tmp_path)
    # ``..`` resolves outside root → escape.
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [
            {"file_path": "../outside.py", "line_start": 1, "line_end": 5, "rationale": "y"}
        ],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.alternatives == []
    assert result.dropped_candidates[0]["reason"] == "escaped_repo"


def test_tolerates_repo_name_prefix_in_path(tmp_path: Path):
    """LLM output that prefixes paths with the repo's root name is accepted, not dropped."""
    _write_repo(tmp_path)
    prefixed = f"{tmp_path.name}/algo.py"   # e.g. "pytest-tmp-0/algo.py"
    discovery = json.dumps({
        "core": {
            "file_path": prefixed,
            "line_start": 6,
            "line_end": 14,
            "rationale": "LLM hallucinated the repo-name prefix",
        },
        "expanded": [],
        "alternatives": [],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.core is not None
    # The stored path is the cleaned version without the prefix.
    assert result.core.file_path == "algo.py"
    assert result.dropped_candidates == []


def test_drops_expanded_not_superset(tmp_path: Path):
    """Expanded variants must strictly contain core's range or be dropped."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [
            {"file_path": "algo.py", "line_start": 16, "line_end": 17, "rationale": "not superset"}
        ],
        "alternatives": [],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.expanded == []
    assert result.dropped_candidates[0]["reason"] == "not_superset_of_core"


def test_drops_alternative_overlapping_core(tmp_path: Path):
    """Alternatives overlapping core's range are dropped as overlaps_core."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [
            {"file_path": "algo.py", "line_start": 8, "line_end": 12, "rationale": "overlaps"}
        ],
    })
    provider = _FakeProvider([discovery, _advice_json()])
    recommender = RepoRecommender(provider)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert result.alternatives == []
    assert result.dropped_candidates[0]["reason"] == "overlaps_core"


# ----------------------------------------------------------------------
# Error paths
# ----------------------------------------------------------------------

def test_raises_when_core_itself_invalid(tmp_path: Path):
    """If core itself fails validation the recommender raises AdvisorError."""
    _write_repo(tmp_path)
    from llm4ad.advisor.pipeline import AdvisorError

    discovery = json.dumps({
        "core": {"file_path": "missing.py", "line_start": 1, "line_end": 5, "rationale": "x"},
        "expanded": [],
        "alternatives": [],
    })
    provider = _FakeProvider([discovery])
    recommender = RepoRecommender(provider)

    with pytest.raises(AdvisorError, match="Core candidate failed validation"):
        asyncio.run(recommender.recommend("goal", tmp_path))


def test_raises_when_discovery_unparseable(tmp_path: Path):
    """Unparseable discovery output should raise AdvisorError."""
    _write_repo(tmp_path)
    from llm4ad.advisor.pipeline import AdvisorError

    provider = _FakeProvider(["this is not json"])
    recommender = RepoRecommender(provider)

    with pytest.raises(AdvisorError, match="unparseable"):
        asyncio.run(recommender.recommend("goal", tmp_path))


def test_raises_when_core_missing(tmp_path: Path):
    """Missing core key in discovery response raises AdvisorError."""
    _write_repo(tmp_path)
    from llm4ad.advisor.pipeline import AdvisorError

    # Valid JSON but no "core" key.
    provider = _FakeProvider([json.dumps({"expanded": [], "alternatives": []})])
    recommender = RepoRecommender(provider)

    with pytest.raises(AdvisorError, match="missing a 'core'"):
        asyncio.run(recommender.recommend("goal", tmp_path))


def test_repo_path_missing_raises(tmp_path: Path):
    """A non-existent repo_path raises AdvisorError before any LLM call."""
    from llm4ad.advisor.pipeline import AdvisorError

    provider = _FakeProvider([])
    recommender = RepoRecommender(provider)

    with pytest.raises(AdvisorError, match="does not exist"):
        asyncio.run(recommender.recommend("goal", tmp_path / "nope"))


# ----------------------------------------------------------------------
# Partial failure: one per-block advice call raises; others succeed.
# ----------------------------------------------------------------------

def test_partial_advice_failure_does_not_crash(tmp_path: Path):
    """One block's advice call failing should not kill the whole recommend request."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "x"},
        "expanded": [],
        "alternatives": [
            {"file_path": "algo.py", "line_start": 16, "line_end": 17, "rationale": "y"}
        ],
    })

    class _FlakyProvider:
        def __init__(self):
            self.n = 0

        async def generate(self, prompt: str, **kwargs) -> GenerationResult:
            self.n += 1
            if self.n == 1:
                return GenerationResult(text=discovery)
            if self.n == 2:
                return GenerationResult(text=_advice_json())
            raise RuntimeError("boom")

    recommender = RepoRecommender(_FlakyProvider())
    result = asyncio.run(recommender.recommend("goal", tmp_path))

    # Core survived; alternative has advice_error.
    assert result.core is not None
    assert result.core.advice is not None
    assert len(result.alternatives) == 1
    assert result.alternatives[0].advice is None
    assert result.alternatives[0].advice_error is not None
    assert "boom" in result.alternatives[0].advice_error


# ----------------------------------------------------------------------
# Expanded tier ordering: sorted by size ascending.
# ----------------------------------------------------------------------

def test_expanded_sorted_by_size_ascending(tmp_path: Path):
    """Expanded variants are returned sorted by size_lines ascending."""
    _write_repo(tmp_path)
    discovery = json.dumps({
        "core": {"file_path": "algo.py", "line_start": 6, "line_end": 14, "rationale": "c"},
        "expanded": [
            {"file_path": "algo.py", "line_start": 1, "line_end": 14, "rationale": "big"},
            {"file_path": "algo.py", "line_start": 3, "line_end": 14, "rationale": "small"},
        ],
        "alternatives": [],
    })
    provider = _FakeProvider([discovery] + [_advice_json()] * 3)
    recommender = RepoRecommender(provider, max_concurrency=3)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    assert len(result.expanded) == 2
    sizes = [r.size_lines for r in result.expanded]
    assert sizes == sorted(sizes)
    # variant_index reflects sorted order
    assert result.expanded[0].variant_index == 0
    assert result.expanded[1].variant_index == 1


# ----------------------------------------------------------------------
# BlockRecommendation.to_dict shape
# ----------------------------------------------------------------------

def test_block_recommendation_to_dict_shape():
    """BlockRecommendation.to_dict() returns a flat, JSON-serializable shape."""
    rec = BlockRecommendation(
        file_path="a.py",
        line_start=1,
        line_end=3,
        tier="core",
        variant_index=None,
        size_lines=3,
        discovery_rationale="r",
    )
    d = rec.to_dict()
    assert d["file_path"] == "a.py"
    assert d["tier"] == "core"
    assert d["advice"] is None


# ----------------------------------------------------------------------
# Language threading (--lang en|zh)
# ----------------------------------------------------------------------


def _minimal_discovery() -> str:
    return json.dumps({
        "core": {
            "file_path": "algo.py",
            "line_start": 6,
            "line_end": 14,
            "rationale": "Greedy solver.",
        }
    })


def test_recommender_default_lang_is_en(tmp_path: Path):
    """No --lang means en; no Chinese directive injected, output records 'en'."""
    _write_repo(tmp_path)
    provider = _FakeProvider([_minimal_discovery(), _advice_json()])
    recommender = RepoRecommender(provider, max_concurrency=1)

    result = asyncio.run(recommender.recommend("goal", tmp_path))

    # Discovery prompt has no Chinese instruction.
    discovery_prompt = provider.calls[0]
    assert "中文" not in discovery_prompt
    assert "Simplified Chinese" not in discovery_prompt
    # Advice prompt is also English.
    advice_prompt = provider.calls[1]
    assert "中文" not in advice_prompt
    # Result records the language for frontend rendering.
    assert result.lang == "en"
    assert result.to_dict()["lang"] == "en"
    if result.core is not None and result.core.advice is not None:
        assert result.core.advice.lang == "en"


def test_recommender_lang_zh_injects_directive(tmp_path: Path):
    """--lang zh prepends a Chinese directive to BOTH discovery and advice prompts."""
    _write_repo(tmp_path)
    provider = _FakeProvider([_minimal_discovery(), _advice_json()])
    recommender = RepoRecommender(provider, max_concurrency=1)

    result = asyncio.run(recommender.recommend("goal", tmp_path, lang="zh"))

    # Both prompts carry the directive.
    assert "中文" in provider.calls[0]
    assert "Simplified Chinese" in provider.calls[0]
    assert "中文" in provider.calls[1]
    # Result records 'zh'.
    assert result.lang == "zh"
    assert result.to_dict()["lang"] == "zh"
    if result.core is not None and result.core.advice is not None:
        assert result.core.advice.lang == "zh"


def test_recommender_lang_en_directive_is_empty(tmp_path: Path):
    """For lang='en' the prompt body is byte-identical to the un-directive form."""
    _write_repo(tmp_path)
    provider = _FakeProvider([_minimal_discovery(), _advice_json()])
    recommender = RepoRecommender(provider, max_concurrency=1)

    asyncio.run(recommender.recommend("goal", tmp_path, lang="en"))

    # The prompt must NOT start with whitespace from a stripped directive,
    # and must NOT contain a placeholder leak.
    assert "{lang_directive}" not in provider.calls[0]
    assert provider.calls[0].lstrip() == provider.calls[0]
    assert "{lang_directive}" not in provider.calls[1]
