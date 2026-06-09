"""Tests for BlockAdvice serialization and LLM-response parsing."""

from __future__ import annotations

from llm4ad.advisor.advice import BlockAdvice


def test_from_llm_json_minimal():
    """from_llm_json copes with a minimal, well-formed response."""
    data = {
        "block_summary": "Sorts by repeated comparison.",
        "feasibility": "yes",
        "feasibility_reason": "This is the hot path.",
        "significance": "high",
        "significance_reason": "The goal is measured here.",
        "concerns": ["Side effect on shared buffer."],
        "suggestions": ["Narrow the block to the compare() helper."],
        "rationale": "Solid candidate; narrow the selection first.",
    }
    advice = BlockAdvice.from_llm_json(data)

    assert advice.feasibility == "yes"
    assert advice.significance == "high"
    assert advice.concerns == ["Side effect on shared buffer."]
    assert advice.suggestions == ["Narrow the block to the compare() helper."]
    assert advice.block_ref is None


def test_from_llm_json_normalizes_case_and_whitespace():
    """Feasibility/significance are lowercased and invalid values dropped."""
    data = {
        "feasibility": "  YES ",
        "significance": "MEDIUM",
        "concerns": None,
        "suggestions": "   ",
    }
    advice = BlockAdvice.from_llm_json(data)

    assert advice.feasibility == "yes"
    assert advice.significance == "medium"
    assert advice.concerns == []
    assert advice.suggestions == []


def test_from_llm_json_drops_invalid_enum_values():
    """Values outside the allowed vocab become empty strings, not exceptions."""
    data = {
        "feasibility": "maybe",
        "significance": "enormous",
    }
    advice = BlockAdvice.from_llm_json(data)
    assert advice.feasibility == ""
    assert advice.significance == ""


def test_from_llm_json_attaches_block_ref():
    """block_ref is carried through unchanged."""
    ref = {"file_path": "algo.py", "line_start": 1, "line_end": 10}
    advice = BlockAdvice.from_llm_json({"feasibility": "yes"}, block_ref=ref)
    assert advice.block_ref == ref


def test_from_llm_json_string_concerns_become_one_item_list():
    """A stray string in list-shaped fields is coerced to a single-item list."""
    advice = BlockAdvice.from_llm_json(
        {"concerns": "Only one concern, as a string."}
    )
    assert advice.concerns == ["Only one concern, as a string."]


def test_to_dict_round_trip_is_json_safe():
    """to_dict returns JSON-serializable data."""
    import json

    advice = BlockAdvice(
        block_summary="s",
        feasibility="partial",
        significance="low",
        concerns=["c1"],
        suggestions=["s1"],
        rationale="r",
        block_ref={"file_path": "a.py", "line_start": 1, "line_end": 2},
    )
    # Round-tripping through json must not raise and must preserve shape.
    reloaded = json.loads(json.dumps(advice.to_dict()))
    assert reloaded["feasibility"] == "partial"
    assert reloaded["block_ref"]["file_path"] == "a.py"
