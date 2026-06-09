"""Integration tests for multimodal prompt construction pipeline.

Tests that build_multimodal_*_prompt() produces correct ContentPart lists
with text + image parts from real Algorithm + BehaviorData objects.
No LLM calls, no subprocess, no gymnasium — just data flow verification.
"""

from llm4ad.evaluator.behavior import BehaviorData, BehaviorVisualization
from llm4ad.infra.provider.base import ContentPart
from llm4ad.planner.base import Algorithm, EvaluationResult, InsightType
from llm4ad.planner.sampler.prompt_templates import (
    build_multimodal_crossover_prompt,
    build_multimodal_mutation_prompt,
)

# 1x1 red pixel PNG encoded as base64
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
)

MULTIMODAL_CONFIG = {
    "max_images_per_prompt": 3,
    "image_max_size_kb": 512,
    "include_observation_text": True,
}


def _make_algorithm(
    alg_id: str,
    score: float,
    observation: str,
    instance_id: str = "inst_1",
) -> Algorithm:
    """Create an Algorithm with behavior data."""
    return Algorithm(
        id=alg_id,
        insight_type=InsightType.INITIAL,
        name="TestAlg",
        description="A test algorithm",
        generation=0,
        evaluation=EvaluationResult(score=score),
        behavior_data=[
            BehaviorData(
                observation=observation,
                visualizations=[
                    BehaviorVisualization(
                        label="Trajectory",
                        media_type="image/png",
                        data_base64=_TINY_PNG_B64,
                    )
                ],
                instance_id=instance_id,
            )
        ],
    )


class TestMultimodalMutationPrompt:
    """Tests for build_multimodal_mutation_prompt."""

    def test_returns_content_parts_list(self):
        """Should return a list of ContentPart objects."""
        parent = _make_algorithm("p1", 0.8, "Seed=6 | Crashed")

        parts = build_multimodal_mutation_prompt(
            background="Test problem",
            parent=parent,
            block=None,
            multimodal_config=MULTIMODAL_CONFIG,
        )

        assert isinstance(parts, list)
        assert all(isinstance(p, ContentPart) for p in parts)

    def test_contains_text_and_image_parts(self):
        """Should have both text and image content parts."""
        parent = _make_algorithm("p1", 0.8, "Seed=6 | Crashed")

        parts = build_multimodal_mutation_prompt(
            background="Test problem",
            parent=parent,
            block=None,
            multimodal_config=MULTIMODAL_CONFIG,
        )

        text_parts = [p for p in parts if p.type == "text"]
        image_parts = [p for p in parts if p.type == "image_url"]

        assert len(text_parts) >= 2  # prompt + observation + instruction
        assert len(image_parts) >= 1  # at least one trajectory image

    def test_observation_text_included(self):
        """Observation text should appear in a text part."""
        parent = _make_algorithm("p1", 0.8, "Seed=6 | Reward=172.7 | Crashed")

        parts = build_multimodal_mutation_prompt(
            background="Test problem",
            parent=parent,
            block=None,
            multimodal_config=MULTIMODAL_CONFIG,
        )

        all_text = " ".join(p.text for p in parts if p.type == "text" and p.text)
        assert "Seed=6" in all_text
        assert "172.7" in all_text

    def test_image_is_data_url(self):
        """Image parts should have data: URL format."""
        parent = _make_algorithm("p1", 0.8, "obs")

        parts = build_multimodal_mutation_prompt(
            background="Test problem",
            parent=parent,
            block=None,
            multimodal_config=MULTIMODAL_CONFIG,
        )

        image_parts = [p for p in parts if p.type == "image_url"]
        assert len(image_parts) > 0
        url = image_parts[0].image_url["url"]
        assert url.startswith("data:image/png;base64,")

    def test_observation_text_excluded_when_disabled(self):
        """When include_observation_text=False, observation should be omitted."""
        parent = _make_algorithm("p1", 0.8, "THIS_SHOULD_NOT_APPEAR")

        config = {**MULTIMODAL_CONFIG, "include_observation_text": False}
        parts = build_multimodal_mutation_prompt(
            background="Test problem",
            parent=parent,
            block=None,
            multimodal_config=config,
        )

        all_text = " ".join(p.text for p in parts if p.type == "text" and p.text)
        assert "THIS_SHOULD_NOT_APPEAR" not in all_text


class TestMultimodalCrossoverPrompt:
    """Tests for build_multimodal_crossover_prompt."""

    def test_includes_both_parents(self):
        """Should include behavior from both parents."""
        p1 = _make_algorithm("p1", 0.8, "Parent1 obs")
        p2 = _make_algorithm("p2", 0.9, "Parent2 obs")

        parts = build_multimodal_crossover_prompt(
            background="Test problem",
            parent1=p1,
            parent2=p2,
            multimodal_config=MULTIMODAL_CONFIG,
        )

        all_text = " ".join(p.text for p in parts if p.type == "text" and p.text)
        assert "Parent1 obs" in all_text
        assert "Parent2 obs" in all_text

        image_parts = [p for p in parts if p.type == "image_url"]
        assert len(image_parts) >= 2  # one from each parent

    def test_max_images_respected(self):
        """Should not exceed max_images_per_prompt."""
        # Create algorithm with 3 visualizations
        alg = Algorithm(
            id="many-viz",
            insight_type=InsightType.INITIAL,
            name="MultiViz",
            description="Has many visualizations",
            generation=0,
            evaluation=EvaluationResult(score=0.8),
            behavior_data=[
                BehaviorData(
                    observation="obs",
                    visualizations=[
                        BehaviorVisualization(
                            label=f"Viz {i}",
                            media_type="image/png",
                            data_base64=_TINY_PNG_B64,
                        )
                        for i in range(5)
                    ],
                    instance_id="inst",
                )
            ],
        )

        config = {**MULTIMODAL_CONFIG, "max_images_per_prompt": 2}
        parts = build_multimodal_mutation_prompt(
            background="Test",
            parent=alg,
            block=None,
            multimodal_config=config,
        )

        image_parts = [p for p in parts if p.type == "image_url"]
        assert len(image_parts) == 2
