"""Tests for SamplerSelector."""

import pytest

from llm4ad.planner.selector.sampler_selector import SamplerSelector


# Create specific mock classes to have proper __class__.__name__
class S1Sampler:
    """Mock sampler 1 for testing."""

    @property
    def n_parents(self):
        return 0

    @property
    def name(self):
        return "S1"


class S2Sampler:
    """Mock sampler 2 for testing."""

    @property
    def n_parents(self):
        return 0

    @property
    def name(self):
        return "S2"


class S3Sampler:
    """Mock sampler 3 for testing."""

    @property
    def n_parents(self):
        return 0

    @property
    def name(self):
        return "S3"


class S0Sampler:
    """Mock sampler 0 for testing."""

    @property
    def n_parents(self):
        return 0

    @property
    def name(self):
        return "S0"


class TestSamplerSelector:
    """Tests for SamplerSelector."""

    def test_initialization(self):
        """Test SamplerSelector initialization."""
        samplers = [S1Sampler(), S2Sampler(), S3Sampler()]
        selector = SamplerSelector(samplers=samplers, config={"selection_strategy": "random"})

        assert len(selector.samplers) == 3
        assert selector.selection_strategy == "random"
        # All weights should be equal initially
        assert all(w == 1.0 for w in selector.weights.values())

    def test_weighted_select(self):
        """Test weighted selection."""
        samplers = [S1Sampler(), S2Sampler()]
        selector = SamplerSelector(samplers=samplers, config={"selection_strategy": "weighted"})

        # Set different weights
        selector.weights["S1Sampler"] = 10.0
        selector.weights["S2Sampler"] = 1.0

        # Run selection many times - s1 should be selected more often
        results = [selector.select(1) for _ in range(100)]
        s1_count = sum(1 for r in results if isinstance(r[0], S1Sampler))

        # s1 should be selected more often (at least 70% of the time)
        assert s1_count > 70

    def test_tournament_select(self):
        """Test tournament selection."""
        samplers = [S0Sampler(), S1Sampler(), S2Sampler(), S3Sampler(), S3Sampler()]
        selector = SamplerSelector(samplers=samplers, config={"selection_strategy": "tournament", "tournament_size": 3})

        # Set different weights
        selector.weights["S0Sampler"] = 10.0  # Highest weight
        selector.weights["S1Sampler"] = 1.0
        selector.weights["S2Sampler"] = 1.0
        selector.weights["S3Sampler"] = 1.0

        # Run selection - s0 should be selected most often
        results = [selector.select(1) for _ in range(100)]
        s0_count = sum(1 for r in results if isinstance(r[0], S0Sampler))

        # s0 should be selected most often due to highest weight in tournament
        assert s0_count > 20

    def test_random_select(self):
        """Test random selection."""
        samplers = [S1Sampler(), S2Sampler()]
        selector = SamplerSelector(samplers=samplers, config={"selection_strategy": "random"})

        # Run selection - both should be selected roughly equally
        results = [selector.select(1) for _ in range(100)]
        s1_count = sum(1 for r in results if isinstance(r[0], S1Sampler))
        s2_count = sum(1 for r in results if isinstance(r[0], S2Sampler))

        # Should be roughly 50/50
        assert 30 <= s1_count <= 70
        assert 30 <= s2_count <= 70

    def test_update_weight(self):
        """Test weight update with fitness."""
        samplers = [S1Sampler(), S2Sampler()]
        selector = SamplerSelector(samplers=samplers, config={"ema_alpha": 0.5})

        # Initial weight is 1.0
        assert selector.weights["S1Sampler"] == 1.0

        # Update with fitness 10.0
        # new_weight = alpha * fitness + (1 - alpha) * old_weight
        # = 0.5 * 10.0 + 0.5 * 1.0 = 5.5
        selector.update_weight(samplers[0], 10.0)
        assert selector.weights["S1Sampler"] == 5.5

        # Update again with fitness 10.0
        # new_weight = 0.5 * 10.0 + 0.5 * 5.5 = 7.75
        selector.update_weight(samplers[0], 10.0)
        assert selector.weights["S1Sampler"] == 7.75

    def test_get_best_sampler(self):
        """Test get_best_sampler method."""
        samplers = [S1Sampler(), S2Sampler()]
        selector = SamplerSelector(samplers=samplers)

        # Initially all weights equal - any is best
        best = selector.get_best_sampler()
        assert best in samplers

        # Set s2 to have higher weight
        selector.weights["S2Sampler"] = 10.0
        selector.weights["S1Sampler"] = 1.0

        best = selector.get_best_sampler()
        assert isinstance(best, S2Sampler)

    def test_reset_weights(self):
        """Test reset_weights method."""
        samplers = [S1Sampler(), S2Sampler()]
        selector = SamplerSelector(samplers=samplers)

        # Change weights
        selector.weights["S1Sampler"] = 10.0
        selector.weights["S2Sampler"] = 5.0

        # Reset
        selector.reset_weights()

        # All weights should be back to default
        assert all(w == 1.0 for w in selector.weights.values())

    def test_select_with_no_samplers(self):
        """Test that select raises error with no samplers."""
        selector = SamplerSelector(samplers=[])

        with pytest.raises(ValueError, match="No samplers available"):
            selector.select(1)

    def test_fitness_history_tracking(self):
        """Test that fitness history is tracked."""
        samplers = [S1Sampler()]
        selector = SamplerSelector(samplers=samplers)

        selector.update_weight(samplers[0], 5.0)
        selector.update_weight(samplers[0], 10.0)
        selector.update_weight(samplers[0], 8.0)

        history = selector.fitness_history["S1Sampler"]
        assert history == [5.0, 10.0, 8.0]
