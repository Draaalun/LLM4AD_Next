"""Unit tests for the MEoH population helper."""

import pytest

from llm4ad.evaluator.base import MetricType
from llm4ad.orchestrator.meoh_population import MEoHPopulation
from llm4ad.planner.base import Algorithm, InsightType


def _algorithm(identifier: str, score: float, distance: float, runtime: float) -> Algorithm:
    algorithm = Algorithm(
        id=identifier,
        insight_type=InsightType.INITIAL,
        name=identifier,
        description=identifier,
    )
    algorithm.set_evaluation_result(score=score, metrics={"distance": distance, "candidate_runtime_ms": runtime})
    algorithm.add_code_artifact("solve.py", f"def solve(): return '{identifier}'")
    return algorithm


def test_meoh_population_survival(monkeypatch):
    """Survival should update archive, active population, and generation."""
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.compute_codebleu_similarity", lambda _a, _b: 0.1)
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.get_non_dominated_indices", lambda matrix: [0, 1])
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.get_domination_relation", lambda _a, _b: 0)
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.compute_hypervolume", lambda _m, _r: 0.42)
    population = MEoHPopulation(
        pop_size=2,
        num_operators=2,
        objective_metrics=["distance", "candidate_runtime_ms"],
        metric_directions={"distance": MetricType.MINIMIZE, "candidate_runtime_ms": MetricType.MINIMIZE},
    )

    for algorithm in [
        _algorithm("a", 10.0, 10.0, 5.0),
        _algorithm("b", 8.0, 8.0, 4.0),
        _algorithm("c", 6.0, 6.0, 7.0),
        _algorithm("d", 9.0, 9.0, 3.0),
    ]:
        population.register_individual(algorithm)

    assert population.generation == 1
    assert len(population.population) == 2
    assert population.elitist_archive
    assert population.last_hv > 0.0


def test_meoh_population_selection_excludes_invalid(monkeypatch):
    """Selection should only sample evaluated individuals."""
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.compute_codebleu_similarity", lambda _a, _b: 0.1)
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.get_non_dominated_indices", lambda matrix: [0])
    monkeypatch.setattr("llm4ad.orchestrator.meoh_population.get_domination_relation", lambda _a, _b: 0)
    population = MEoHPopulation(
        pop_size=4,
        num_operators=2,
        objective_metrics=["distance"],
        metric_directions={"distance": MetricType.MINIMIZE},
    )
    valid = _algorithm("valid", 1.0, 1.0, 1.0)
    invalid = Algorithm(id="invalid", insight_type=InsightType.INITIAL, description="invalid")
    population.population = [valid, invalid]

    selected = population.selection(3)

    assert selected
    assert all(algorithm.id == "valid" for algorithm in selected)


def test_meoh_population_hv_returns_zero_for_small_archive():
    """HV should be zero when fewer than two valid archive individuals exist."""
    population = MEoHPopulation(
        objective_metrics=["distance", "candidate_runtime_ms"],
        metric_directions={"distance": MetricType.MINIMIZE, "candidate_runtime_ms": MetricType.MINIMIZE},
    )
    population.elitist_archive = [_algorithm("solo", 1.0, 1.0, 1.0)]

    assert population._compute_hypervolume() == 0.0


def test_meoh_population_hv_returns_zero_for_flat_dimension():
    """HV should be zero when any objective cannot be normalized."""
    population = MEoHPopulation(
        objective_metrics=["distance", "candidate_runtime_ms"],
        metric_directions={"distance": MetricType.MINIMIZE, "candidate_runtime_ms": MetricType.MINIMIZE},
    )
    population.elitist_archive = [
        _algorithm("a", 2.0, 5.0, 1.0),
        _algorithm("b", 1.0, 5.0, 2.0),
    ]

    assert population._compute_hypervolume() == 0.0
