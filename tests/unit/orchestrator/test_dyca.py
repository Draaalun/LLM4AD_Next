"""Unit tests for DyCA orchestrator components.

Tests cover:
- clustering_utils: pure functions for instance scoring, clustering, ARI, anchor selection
- Pool data structures: ClusterArchive, ClusterUnit, ComplementaryPool
- DyCAOrchestrator: resource allocation, pool registration, sampler loading
"""

import numpy as np
import pytest

from llm4ad.planner.base import Algorithm, EvaluationResult, InsightType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_algorithm(
    algo_id: str,
    score: float | None = None,
    per_instance_scores: dict[str, float] | None = None,
) -> Algorithm:
    """Create an Algorithm with optional evaluation and per-instance scores.

    Args:
        algo_id: Unique identifier for the algorithm.
        score: Aggregate evaluation score (None = unevaluated).
        per_instance_scores: Per-instance score mapping.

    Returns:
        Configured Algorithm instance.
    """
    algo = Algorithm(
        id=algo_id,
        insight_type=InsightType.INITIAL,
        name=f"Algo-{algo_id}",
        description="test",
        generation=0,
    )
    if score is not None:
        algo.evaluation = EvaluationResult(score=score)
    if per_instance_scores is not None:
        algo.custom_metadata["per_instance_scores"] = per_instance_scores
    return algo


# ===========================================================================
# clustering_utils
# ===========================================================================


class TestClusteringUtils:
    """Tests for pure utility functions in clustering_utils."""

    def test_get_set_instance_scores(self):
        """Test round-trip of instance scores through custom_metadata."""
        from llm4ad.orchestrator.clustering_utils import (
            get_instance_scores,
            set_instance_scores,
        )

        algo = make_algorithm("a1")
        assert get_instance_scores(algo) == {}

        scores = {"inst_a": -100.0, "inst_b": -200.0}
        set_instance_scores(algo, scores)
        assert get_instance_scores(algo) == scores

    def test_get_set_cluster_id(self):
        """Test cluster_id metadata read/write."""
        from llm4ad.orchestrator.clustering_utils import (
            get_cluster_id,
            set_cluster_id,
        )

        algo = make_algorithm("a1")
        assert get_cluster_id(algo) is None

        set_cluster_id(algo, 2)
        assert get_cluster_id(algo) == 2

    def test_get_set_pool_type(self):
        """Test pool_type metadata read/write."""
        from llm4ad.orchestrator.clustering_utils import (
            get_pool_type,
            set_pool_type,
        )

        algo = make_algorithm("a1")
        assert get_pool_type(algo) is None

        set_pool_type(algo, "specialist")
        assert get_pool_type(algo) == "specialist"

    def test_cluster_score_basic(self):
        """Test cluster_score computes correct average over cluster instances."""
        from llm4ad.orchestrator.clustering_utils import cluster_score

        algo = make_algorithm(
            "a1",
            per_instance_scores={"i1": -100.0, "i2": -200.0, "i3": -300.0},
        )
        # Cluster has i1 and i3 → average = (-100 + -300) / 2 = -200
        assert cluster_score(algo, ["i1", "i3"]) == pytest.approx(-200.0)

    def test_cluster_score_missing_instances(self):
        """Test cluster_score ignores instances not in per_instance_scores."""
        from llm4ad.orchestrator.clustering_utils import cluster_score

        algo = make_algorithm("a1", per_instance_scores={"i1": -50.0})
        # i2 not in scores → only i1 counted
        assert cluster_score(algo, ["i1", "i2"]) == pytest.approx(-50.0)

    def test_cluster_score_empty(self):
        """Test cluster_score returns -inf when no instances match."""
        from llm4ad.orchestrator.clustering_utils import cluster_score

        algo = make_algorithm("a1", per_instance_scores={})
        assert cluster_score(algo, ["i1"]) == float("-inf")

    def test_build_feature_matrix(self):
        """Test feature matrix shape and content."""
        from llm4ad.orchestrator.clustering_utils import build_feature_matrix

        a1 = make_algorithm("a1", per_instance_scores={"x": 1.0, "y": 2.0})
        a2 = make_algorithm("a2", per_instance_scores={"x": 3.0, "y": 4.0})

        matrix = build_feature_matrix([a1, a2], ["x", "y"])
        assert matrix.shape == (2, 2)
        # row 0 = instance "x": [score_a1, score_a2] = [1.0, 3.0]
        np.testing.assert_array_equal(matrix[0], [1.0, 3.0])
        # row 1 = instance "y": [2.0, 4.0]
        np.testing.assert_array_equal(matrix[1], [2.0, 4.0])

    def test_cluster_instances_kmeans(self):
        """Test KMeans clustering produces correct label dict."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import cluster_instances

        # Two clearly separated groups in 1D feature space
        matrix = np.array([[0.0], [0.1], [0.2], [10.0], [10.1], [10.2]])
        names = ["a", "b", "c", "d", "e", "f"]

        labels = cluster_instances(matrix, names, method="kmeans", n_clusters=2)

        assert set(labels.keys()) == set(names)
        # a/b/c should be in one cluster, d/e/f in another
        assert labels["a"] == labels["b"] == labels["c"]
        assert labels["d"] == labels["e"] == labels["f"]
        assert labels["a"] != labels["d"]

    def test_cluster_instances_clamps_n_clusters(self):
        """Test that n_clusters is clamped to number of samples."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import cluster_instances

        matrix = np.array([[0.0], [10.0]])
        names = ["a", "b"]

        labels = cluster_instances(matrix, names, n_clusters=5)
        assert len(labels) == 2

    def test_compute_ari_identical(self):
        """Test ARI = 1.0 for identical labelings."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import compute_ari

        labels = {"a": 0, "b": 0, "c": 1, "d": 1}
        assert compute_ari(labels, labels) == pytest.approx(1.0)

    def test_compute_ari_different(self):
        """Test ARI < 1.0 for different labelings."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import compute_ari

        l1 = {"a": 0, "b": 0, "c": 1, "d": 1}
        l2 = {"a": 0, "b": 1, "c": 0, "d": 1}
        ari = compute_ari(l1, l2)
        assert ari < 1.0

    def test_compute_ari_too_few_keys(self):
        """Test ARI returns 0.0 when fewer than 2 common keys."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import compute_ari

        assert compute_ari({"a": 0}, {"a": 0}) == 0.0
        assert compute_ari({"a": 0}, {"b": 0}) == 0.0

    def test_find_best_k(self):
        """Test automatic K selection via elbow method."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import find_best_k

        # 3 clearly separated clusters
        matrix = np.array([
            [0, 0], [1, 0], [0, 1],
            [10, 10], [11, 10], [10, 11],
            [20, 0], [21, 0], [20, 1],
        ], dtype=float)
        k = find_best_k(matrix)
        assert 2 <= k <= 5  # Should find ~3 clusters

    def test_find_best_k_few_samples(self):
        """Test find_best_k with very few samples."""
        pytest.importorskip("sklearn")
        from llm4ad.orchestrator.clustering_utils import find_best_k

        # Only 2 samples — upper bound < 2, should return n_samples
        matrix = np.array([[0.0], [10.0]])
        k = find_best_k(matrix)
        assert k == 2

    def test_select_anchor_algorithms(self):
        """Test anchor selection picks diverse high-scorers."""
        from llm4ad.orchestrator.clustering_utils import select_anchor_algorithms

        instances = ["i1", "i2"]
        # a1 good on i1, a2 good on i2, a3 mediocre on both
        a1 = make_algorithm("a1", score=-50.0, per_instance_scores={"i1": -10.0, "i2": -90.0})
        a2 = make_algorithm("a2", score=-50.0, per_instance_scores={"i1": -90.0, "i2": -10.0})
        a3 = make_algorithm("a3", score=-50.0, per_instance_scores={"i1": -50.0, "i2": -50.0})

        anchors = select_anchor_algorithms([a1, a2, a3], instances, n_anchors=2)
        assert len(anchors) == 2
        # Should prefer diverse pair (a1, a2) over including a3
        anchor_ids = {a.id for a in anchors}
        assert "a1" in anchor_ids
        assert "a2" in anchor_ids

    def test_select_anchor_fewer_than_n(self):
        """Test anchor selection returns all when population < n_anchors."""
        from llm4ad.orchestrator.clustering_utils import select_anchor_algorithms

        a1 = make_algorithm("a1", score=-10.0, per_instance_scores={"i1": -10.0})
        anchors = select_anchor_algorithms([a1], ["i1"], n_anchors=5)
        assert len(anchors) == 1

    def test_get_cluster_instance_names(self):
        """Test filtering instance names by cluster ID."""
        from llm4ad.orchestrator.clustering_utils import get_cluster_instance_names

        labels = {"a": 0, "b": 1, "c": 0, "d": 2}
        assert sorted(get_cluster_instance_names(labels, 0)) == ["a", "c"]
        assert get_cluster_instance_names(labels, 1) == ["b"]
        assert get_cluster_instance_names(labels, 3) == []

    def test_get_unique_cluster_ids(self):
        """Test extracting sorted unique cluster IDs."""
        from llm4ad.orchestrator.clustering_utils import get_unique_cluster_ids

        labels = {"a": 2, "b": 0, "c": 1, "d": 0}
        assert get_unique_cluster_ids(labels) == [0, 1, 2]


# ===========================================================================
# Pool data structures
# ===========================================================================


class TestClusterArchive:
    """Tests for ClusterArchive elite/failure waterfall."""

    def test_adds_to_elite_when_not_full(self):
        """Test that algorithms go to elite when archive is not full."""
        from llm4ad.orchestrator.dyca import ClusterArchive

        archive = ClusterArchive(cluster_id=0, instance_names=["i1"], elite_size=3)
        algo = make_algorithm("a1", score=-100.0, per_instance_scores={"i1": -100.0})

        archive.update(algo)
        assert len(archive.elite) == 1
        assert len(archive.failure) == 0

    def test_demotes_worst_elite(self):
        """Test that adding a better algorithm demotes the worst elite."""
        from llm4ad.orchestrator.dyca import ClusterArchive

        archive = ClusterArchive(cluster_id=0, instance_names=["i1"], elite_size=2)

        a1 = make_algorithm("a1", per_instance_scores={"i1": -300.0})
        a2 = make_algorithm("a2", per_instance_scores={"i1": -200.0})
        a3 = make_algorithm("a3", per_instance_scores={"i1": -100.0})  # best

        archive.update(a1)
        archive.update(a2)
        assert len(archive.elite) == 2

        archive.update(a3)
        # a3 and a2 in elite, a1 demoted to failure
        assert len(archive.elite) == 2
        elite_ids = {a.id for a in archive.elite}
        assert "a3" in elite_ids
        assert "a2" in elite_ids
        assert len(archive.failure) == 1
        assert archive.failure[0].id == "a1"

    def test_worse_goes_to_failure(self):
        """Test that an algorithm worse than all elites goes to failure."""
        from llm4ad.orchestrator.dyca import ClusterArchive

        archive = ClusterArchive(cluster_id=0, instance_names=["i1"], elite_size=1)

        good = make_algorithm("good", per_instance_scores={"i1": -10.0})
        bad = make_algorithm("bad", per_instance_scores={"i1": -999.0})

        archive.update(good)
        archive.update(bad)

        assert len(archive.elite) == 1
        assert archive.elite[0].id == "good"
        assert len(archive.failure) == 1
        assert archive.failure[0].id == "bad"

    def test_get_elite_best(self):
        """Test get_elite_best returns the top algorithm."""
        from llm4ad.orchestrator.dyca import ClusterArchive

        archive = ClusterArchive(cluster_id=0, instance_names=["i1"], elite_size=3)
        assert archive.get_elite_best() is None

        a1 = make_algorithm("a1", per_instance_scores={"i1": -200.0})
        a2 = make_algorithm("a2", per_instance_scores={"i1": -100.0})  # better (higher)

        archive.update(a1)
        archive.update(a2)
        assert archive.get_elite_best().id == "a2"


class TestClusterUnit:
    """Tests for ClusterUnit specialist pool."""

    def test_add_algorithm_sets_metadata(self):
        """Test that add_algorithm sets cluster_id and pool_type."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(cluster_id=1, instance_names=["i1"], max_size=5)
        algo = make_algorithm("a1", score=-100.0, per_instance_scores={"i1": -100.0})

        cu.add_algorithm(algo)
        assert algo.custom_metadata["cluster_id"] == 1
        assert algo.custom_metadata["pool_type"] == "specialist"
        assert len(cu.population) == 1

    def test_best_score_with_negative_values(self):
        """Test that best_score tracks correctly with negative scores (the bug fix)."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(cluster_id=0, instance_names=["i1"], max_size=5)
        assert cu.best_score == float("-inf")

        # First algorithm: score -500
        a1 = make_algorithm("a1", per_instance_scores={"i1": -500.0})
        cu.add_algorithm(a1)
        assert cu.best_score == -500.0
        assert cu.stagnation_count == 0

        # Worse algorithm: score -600 (lower is worse for maximization)
        a2 = make_algorithm("a2", per_instance_scores={"i1": -600.0})
        cu.add_algorithm(a2)
        assert cu.best_score == -500.0
        assert cu.stagnation_count == 1

        # Better algorithm: score -100
        a3 = make_algorithm("a3", per_instance_scores={"i1": -100.0})
        cu.add_algorithm(a3)
        assert cu.best_score == -100.0
        assert cu.stagnation_count == 0

    def test_trims_population(self):
        """Test that population is trimmed when exceeding max_size."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(cluster_id=0, instance_names=["i1"], max_size=2)

        a1 = make_algorithm("a1", per_instance_scores={"i1": -300.0})
        a2 = make_algorithm("a2", per_instance_scores={"i1": -100.0})
        a3 = make_algorithm("a3", per_instance_scores={"i1": -200.0})

        cu.add_algorithm(a1)
        cu.add_algorithm(a2)
        cu.add_algorithm(a3)

        assert len(cu.population) == 2
        # Should keep the best two: a2 (-100) and a3 (-200)
        pop_ids = {a.id for a in cu.population}
        assert "a2" in pop_ids
        assert "a3" in pop_ids

    def test_select_parent_from_population(self):
        """Test tournament selection returns a valid parent."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(cluster_id=0, instance_names=["i1"], max_size=5)
        a1 = make_algorithm("a1", score=-100.0, per_instance_scores={"i1": -100.0})
        a2 = make_algorithm("a2", score=-200.0, per_instance_scores={"i1": -200.0})

        cu.add_algorithm(a1)
        cu.add_algorithm(a2)

        parent = cu.select_parent(tournament_size=2)
        assert parent is not None
        assert parent.id in {"a1", "a2"}

    def test_select_parent_empty_population(self):
        """Test select_parent returns None when population is empty."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(cluster_id=0, instance_names=["i1"], max_size=5)
        assert cu.select_parent() is None

    def test_needs_sos(self):
        """Test SOS detection based on stagnation count."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(
            cluster_id=0, instance_names=["i1"],
            max_size=5, sos_stagnation_threshold=2,
        )
        a_best = make_algorithm("best", per_instance_scores={"i1": -100.0})
        cu.add_algorithm(a_best)
        assert not cu.needs_sos()

        # Two stagnating additions
        for i in range(2):
            bad = make_algorithm(f"bad{i}", per_instance_scores={"i1": -999.0})
            cu.add_algorithm(bad)

        assert cu.needs_sos()

    def test_update_gap(self):
        """Test gap metric update using absolute distance formula."""
        from llm4ad.orchestrator.dyca import ClusterUnit

        cu = ClusterUnit(cluster_id=0, instance_names=["i1"], max_size=5)
        a1 = make_algorithm("a1", per_instance_scores={"i1": 80.0})
        cu.add_algorithm(a1)

        cu.update_gap(global_best_score=100.0)
        # gap = max(0, 100 - 80) = 20.0
        assert cu.gap == pytest.approx(20.0)


class TestComplementaryPool:
    """Tests for ComplementaryPool cross-cluster diversity pool."""

    def test_add_algorithm(self):
        """Test basic add."""
        from llm4ad.orchestrator.dyca import ComplementaryPool

        pool = ComplementaryPool(max_size=5)
        algo = make_algorithm("a1", score=-100.0)
        pool.add_algorithm(algo)

        assert len(pool.population) == 1
        assert algo.custom_metadata["pool_type"] == "complementary"

    def test_survival_selection_trims(self):
        """Test that pool is trimmed to max_size."""
        from llm4ad.orchestrator.dyca import ComplementaryPool

        pool = ComplementaryPool(max_size=2)
        for i in range(5):
            algo = make_algorithm(f"a{i}", score=float(-i))
            pool.add_algorithm(algo)

        assert len(pool.population) <= 2

    def test_select_pair_insufficient(self):
        """Test select_pair returns None with < 2 evaluated algorithms."""
        from llm4ad.orchestrator.dyca import ComplementaryPool

        pool = ComplementaryPool(max_size=5)
        assert pool.select_pair() is None

        pool.add_algorithm(make_algorithm("a1", score=-100.0))
        assert pool.select_pair() is None

    def test_select_pair_returns_different_algorithms(self):
        """Test select_pair returns two different algorithms."""
        from llm4ad.orchestrator.dyca import ComplementaryPool

        pool = ComplementaryPool(max_size=5)
        a1 = make_algorithm(
            "a1", score=-100.0,
            per_instance_scores={"i1": -10.0, "i2": -200.0},
        )
        a2 = make_algorithm(
            "a2", score=-100.0,
            per_instance_scores={"i1": -200.0, "i2": -10.0},
        )

        pool.add_algorithm(a1)
        pool.add_algorithm(a2)

        pair = pool.select_pair()
        assert pair is not None
        assert pair[0].id != pair[1].id


# ===========================================================================
# DyCAOrchestrator logic (no LLM calls)
# ===========================================================================


class TestDyCAResourceAllocation:
    """Tests for DyCA resource allocation logic."""

    def _make_orchestrator_for_allocation(self):
        """Create a minimal DyCAOrchestrator with mocked dependencies.

        Returns:
            DyCAOrchestrator configured for resource allocation testing.
        """
        from unittest.mock import MagicMock

        from llm4ad.orchestrator.dyca import (
            ClusterUnit,
            ComplementaryPool,
            DyCAConfig,
            DyCAOrchestrator,
        )

        config = DyCAConfig(
            type="dyca",
            max_generations=10,
            population_size=5,
            offspring_per_generation=6,
            n_clusters=3,
            base_complementary_ratio=0.2,
            ari_threshold=0.8,
            sos_stagnation_threshold=2,
        )

        # Mock all dependencies
        planner = MagicMock()
        planner.sampler_map = {}
        planner.samplers = []
        planner.provider = MagicMock()
        planner.memory = MagicMock()
        planner.analyzed_repository = MagicMock()

        coder = MagicMock()
        dispatcher = MagicMock()
        dispatcher._data_files = ["i1", "i2", "i3"]
        monitor = MagicMock()
        version_control = MagicMock()
        state_tracker = MagicMock()
        state_tracker.generated_dir = None

        orch = DyCAOrchestrator(
            planner=planner,
            coder=coder,
            dispatcher=dispatcher,
            monitor=monitor,
            config=config,
            version_control=version_control,
            state_tracker=state_tracker,
        )

        # Setup specialist pools
        for cid in range(3):
            cu = ClusterUnit(
                cluster_id=cid,
                instance_names=[f"i{cid + 1}"],
                max_size=5,
                sos_stagnation_threshold=2,
            )
            orch.specialist_pools[cid] = cu

        orch.complementary_pool = ComplementaryPool(max_size=5)

        return orch

    def test_allocate_resources_produces_tasks(self):
        """Test _allocate_resources returns non-empty task list."""
        orch = self._make_orchestrator_for_allocation()
        tasks = orch._allocate_resources()

        assert len(tasks) > 0
        # Rounding may cause slight deviation from offspring_per_generation
        assert abs(len(tasks) - orch.config.offspring_per_generation) <= 2

    def test_allocate_resources_has_complementary(self):
        """Test that at least one complementary task is allocated."""
        orch = self._make_orchestrator_for_allocation()
        tasks = orch._allocate_resources()

        comp_tasks = [t for t in tasks if t["pool"] == "complementary"]
        assert len(comp_tasks) >= 1

    def test_allocate_resources_sos_on_stagnation(self):
        """Test SOS tasks appear when a cluster is stagnating."""
        orch = self._make_orchestrator_for_allocation()

        # Force cluster 0 to stagnate
        cu = orch.specialist_pools[0]
        a = make_algorithm("a1", per_instance_scores={"i1": -100.0})
        cu.add_algorithm(a)
        cu.stagnation_count = 10  # Well past threshold of 2

        tasks = orch._allocate_resources()
        sos_tasks = [t for t in tasks if t.get("operator") == "sos"]
        assert len(sos_tasks) >= 1
        assert sos_tasks[0]["cluster_id"] == 0

    def test_allocate_more_complementary_when_low_ari(self):
        """Test that low ARI increases complementary allocation."""
        orch = self._make_orchestrator_for_allocation()

        orch.current_ari = 1.0  # Stable
        tasks_stable = orch._allocate_resources()
        n_comp_stable = len([t for t in tasks_stable if t["pool"] == "complementary"])

        orch.current_ari = 0.3  # Unstable
        tasks_unstable = orch._allocate_resources()
        n_comp_unstable = len([t for t in tasks_unstable if t["pool"] == "complementary"])

        assert n_comp_unstable >= n_comp_stable


class TestDyCAPoolRegistration:
    """Tests for pool registration logic."""

    def _make_orchestrator_with_clusters(self):
        """Create DyCAOrchestrator with pre-configured clusters.

        Returns:
            DyCAOrchestrator configured with 2 clusters.
        """
        from unittest.mock import MagicMock

        from llm4ad.orchestrator.dyca import (
            ClusterUnit,
            ComplementaryPool,
            DyCAConfig,
            DyCAOrchestrator,
        )

        config = DyCAConfig(
            type="dyca",
            max_generations=10,
            population_size=5,
            generalist_pool_size=3,
            complementary_pool_size=5,
            specialist_pool_size=5,
        )

        planner = MagicMock()
        planner.sampler_map = {}
        planner.samplers = []
        planner.provider = MagicMock()
        planner.memory = MagicMock()
        planner.analyzed_repository = MagicMock()

        dispatcher = MagicMock()
        dispatcher._data_files = ["i1", "i2"]

        orch = DyCAOrchestrator(
            planner=planner,
            coder=MagicMock(),
            dispatcher=dispatcher,
            monitor=MagicMock(),
            config=config,
            version_control=MagicMock(),
            state_tracker=MagicMock(),
        )

        orch.cluster_labels = {"i1": 0, "i2": 1}
        orch.specialist_pools = {
            0: ClusterUnit(cluster_id=0, instance_names=["i1"], max_size=5),
            1: ClusterUnit(cluster_id=1, instance_names=["i2"], max_size=5),
        }
        orch.complementary_pool = ComplementaryPool(
            max_size=5, cluster_labels={"i1": 0, "i2": 1},
        )

        return orch

    def test_register_evaluated_algorithm(self):
        """Test that an evaluated algorithm enters all three pools."""
        orch = self._make_orchestrator_with_clusters()

        algo = make_algorithm(
            "a1", score=-100.0,
            per_instance_scores={"i1": -50.0, "i2": -150.0},
        )
        orch._register_to_pools(algo)

        assert len(orch.generalist_pool) == 1
        assert len(orch.complementary_pool.population) == 1
        assert orch.global_best is not None
        assert orch.global_best.id == "a1"

    def test_register_unevaluated_skipped(self):
        """Test that unevaluated algorithms are not registered."""
        orch = self._make_orchestrator_with_clusters()

        algo = make_algorithm("a1")  # No evaluation
        orch._register_to_pools(algo)

        assert len(orch.generalist_pool) == 0
        assert len(orch.all_algorithms) == 0

    def test_generalist_pool_trimmed(self):
        """Test that generalist pool respects max size."""
        orch = self._make_orchestrator_with_clusters()

        for i in range(5):
            algo = make_algorithm(
                f"a{i}", score=float(-i * 100),
                per_instance_scores={"i1": float(-i * 100)},
            )
            orch._register_to_pools(algo)

        assert len(orch.generalist_pool) <= orch.config.generalist_pool_size

    def test_global_best_updates(self):
        """Test that global_best tracks the highest-scoring algorithm."""
        orch = self._make_orchestrator_with_clusters()

        a1 = make_algorithm("a1", score=-200.0, per_instance_scores={"i1": -200.0})
        a2 = make_algorithm("a2", score=-100.0, per_instance_scores={"i1": -100.0})

        orch._register_to_pools(a1)
        assert orch.global_best.id == "a1"

        orch._register_to_pools(a2)
        assert orch.global_best.id == "a2"  # -100 > -200


class TestDyCAEnsureSamplersLoaded:
    """Tests for _ensure_dyca_samplers_loaded fix."""

    def test_loads_missing_samplers(self):
        """Test that missing DyCA samplers are loaded into planner.sampler_map."""
        from unittest.mock import MagicMock

        from llm4ad.orchestrator.dyca import DyCAConfig, DyCAOrchestrator

        config = DyCAConfig(type="dyca", max_generations=1, population_size=2)

        planner = MagicMock()
        planner.sampler_map = {"init_sampler": MagicMock()}
        planner.samplers = []
        planner.provider = MagicMock()
        planner.memory = MagicMock()
        planner.analyzed_repository = MagicMock()
        planner.analyzed_repository.evolvable_blocks = []

        dispatcher = MagicMock()
        dispatcher._data_files = []

        orch = DyCAOrchestrator(
            planner=planner,
            coder=MagicMock(),
            dispatcher=dispatcher,
            monitor=MagicMock(),
            config=config,
            version_control=MagicMock(),
            state_tracker=MagicMock(),
        )

        expected_samplers = [
            "e1_sampler", "e2_sampler", "m1_sampler",
            "m2_sampler", "summary_sampler", "complementary_cross_sampler",
        ]
        for name in expected_samplers:
            assert name in orch.planner.sampler_map, f"{name} not loaded"

    def test_skips_already_loaded(self):
        """Test that already-present samplers are not re-created."""
        from unittest.mock import MagicMock

        from llm4ad.orchestrator.dyca import DyCAConfig, DyCAOrchestrator

        config = DyCAConfig(type="dyca", max_generations=1, population_size=2)

        existing_sampler = MagicMock()
        planner = MagicMock()
        planner.sampler_map = {
            "init_sampler": MagicMock(),
            "e1_sampler": existing_sampler,
            "e2_sampler": MagicMock(),
            "m1_sampler": MagicMock(),
            "m2_sampler": MagicMock(),
            "summary_sampler": MagicMock(),
            "complementary_cross_sampler": MagicMock(),
        }
        planner.samplers = []
        planner.provider = MagicMock()
        planner.memory = MagicMock()
        planner.analyzed_repository = MagicMock()

        dispatcher = MagicMock()
        dispatcher._data_files = []

        orch = DyCAOrchestrator(
            planner=planner,
            coder=MagicMock(),
            dispatcher=dispatcher,
            monitor=MagicMock(),
            config=config,
            version_control=MagicMock(),
            state_tracker=MagicMock(),
        )

        # e1_sampler should still be the original mock, not replaced
        assert orch.planner.sampler_map["e1_sampler"] is existing_sampler
