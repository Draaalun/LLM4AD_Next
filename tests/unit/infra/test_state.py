"""Unit tests for the StateTracker class."""



from llm4ad.infra.state import (
    EvolutionState,
    GenerationMetrics,
    ModuleTiming,
    ResourceUsage,
    StateTracker,
    StateTrackerConfig,
)


class TestModuleTiming:
    """Test cases for ModuleTiming class."""

    def test_initial_state(self):
        """Test initial state is correctly set."""
        timing = ModuleTiming()
        assert timing.total_time_ms == 0.0
        assert timing.call_count == 0
        assert timing.average_time_ms == 0.0
        assert timing.min_time_ms == float("inf")
        assert timing.max_time_ms == 0.0

    def test_update_multiple_calls(self):
        """Test that statistics are updated correctly across multiple calls."""
        timing = ModuleTiming()
        # This class is used by StateTracker, we just test its data structure
        # since updates are done by StateTracker.record_timing
        timing.total_time_ms = 100.0
        timing.call_count = 2
        timing.average_time_ms = 50.0
        timing.min_time_ms = 40.0
        timing.max_time_ms = 60.0
        timing.last_time_ms = 60.0

        assert timing.total_time_ms == 100.0
        assert timing.call_count == 2
        assert timing.average_time_ms == 50.0


class TestResourceUsage:
    """Test cases for ResourceUsage class."""

    def test_create_with_defaults(self):
        """Test creating ResourceUsage with defaults."""
        usage = ResourceUsage()
        assert usage.memory_usage_mb == 0.0
        assert usage.cpu_usage_percent == 0.0
        assert usage.worktree_count == 0
        assert usage.timestamp > 0

    def test_create_custom_values(self):
        """Test creating ResourceUsage with custom values."""
        usage = ResourceUsage(
            memory_usage_mb=123.5,
            cpu_usage_percent=45.2,
            worktree_count=10,
        )
        assert usage.memory_usage_mb == 123.5
        assert usage.cpu_usage_percent == 45.2
        assert usage.worktree_count == 10


class TestGenerationMetrics:
    """Test cases for GenerationMetrics class."""

    def test_create(self):
        """Test creating GenerationMetrics."""
        metrics = GenerationMetrics(
            generation=10,
            best_score=100.0,
            average_score=50.0,
            worst_score=10.0,
            total_evaluations=20,
            successful_evaluations=18,
            failed_evaluations=2,
            island_best_scores={0: 90.0, 1: 100.0},
        )
        assert metrics.generation == 10
        assert metrics.best_score == 100.0
        assert metrics.average_score == 50.0
        assert metrics.total_evaluations == 20
        assert metrics.successful_evaluations == 18
        assert metrics.failed_evaluations == 2
        assert metrics.island_best_scores == {0: 90.0, 1: 100.0}


class TestStateTrackerConfig:
    """Test cases for StateTrackerConfig class."""

    def test_defaults(self):
        """Test default configuration values."""
        config = StateTrackerConfig()
        assert config.enable_resource_tracking is True
        assert config.resource_tracking_interval_seconds == 5.0
        assert config.enable_detailed_timing is True
        assert config.max_history_entries == 1000


class TestStateTracker:
    """Test cases for StateTracker class."""

    def test_initial_state(self):
        """Test initial state is correctly set."""
        tracker = StateTracker()
        assert tracker.state == EvolutionState.IDLE
        assert tracker.current_generation == 0
        assert tracker.total_generations == 0
        assert tracker.end_time is None
        assert len(tracker.metrics_history) == 0
        assert len(tracker.module_timing) == 0
        assert len(tracker.resource_history) == 0
        assert tracker.global_best_score == float("-inf")
        assert tracker.total_evaluations == 0
        assert tracker.total_migrations == 0

    def test_start_run(self):
        """Test starting a new run."""
        tracker = StateTracker()
        tracker.start_run(100)

        assert tracker.state == EvolutionState.RUNNING
        assert tracker.total_generations == 100
        assert tracker.current_generation == 0
        assert tracker.end_time is None
        assert tracker.start_time > 0
        assert len(tracker.metrics_history) == 0
        assert tracker.global_best_score == float("-inf")
        assert tracker.total_evaluations == 0

    def test_end_run(self):
        """Test ending a run."""
        tracker = StateTracker()
        tracker.start_run(100)
        tracker.end_run(EvolutionState.COMPLETED)

        assert tracker.state == EvolutionState.COMPLETED
        assert tracker.end_time is not None

    def test_record_timing(self):
        """Test recording module timing."""
        tracker = StateTracker()

        # First call
        tracker.record_timing("test.module", 100.0)
        assert "test.module" in tracker.module_timing
        timing = tracker.module_timing["test.module"]
        assert timing.total_time_ms == 100.0
        assert timing.call_count == 1
        assert timing.average_time_ms == 100.0
        assert timing.min_time_ms == 100.0
        assert timing.max_time_ms == 100.0

        # Second call
        tracker.record_timing("test.module", 50.0)
        timing = tracker.module_timing["test.module"]
        assert timing.total_time_ms == 150.0
        assert timing.call_count == 2
        assert timing.average_time_ms == 75.0
        assert timing.min_time_ms == 50.0
        assert timing.max_time_ms == 100.0
        assert timing.last_time_ms == 50.0

    def test_record_timing_disabled(self):
        """Test that timing is not recorded when disabled in config."""
        config = StateTrackerConfig(enable_detailed_timing=False)
        tracker = StateTracker(config=config)

        tracker.record_timing("test.module", 100.0)
        assert "test.module" not in tracker.module_timing

    def test_update_generation(self):
        """Test updating with new generation metrics."""
        tracker = StateTracker()
        tracker.start_run(10)

        metrics = GenerationMetrics(
            generation=1,
            best_score=80.0,
            average_score=40.0,
            worst_score=10.0,
            total_evaluations=10,
            successful_evaluations=9,
            failed_evaluations=1,
        )

        tracker.update_generation(1, metrics)
        assert tracker.current_generation == 1
        assert len(tracker.metrics_history) == 1
        assert tracker.global_best_score == 80.0
        assert tracker.total_evaluations == 10

        # Second generation
        metrics2 = GenerationMetrics(
            generation=2,
            best_score=90.0,
            average_score=45.0,
            worst_score=15.0,
            total_evaluations=10,
            successful_evaluations=10,
            failed_evaluations=0,
        )
        tracker.update_generation(2, metrics2)
        assert tracker.current_generation == 2
        assert len(tracker.metrics_history) == 2
        assert tracker.global_best_score == 90.0
        assert tracker.total_evaluations == 20

    def test_truncate_history(self):
        """Test that history is truncated when max entries exceeded."""
        config = StateTrackerConfig(max_history_entries=3)
        tracker = StateTracker(config=config)

        for i in range(5):
            metrics = GenerationMetrics(
                generation=i,
                best_score=float(i),
                average_score=float(i) / 2,
                worst_score=0.0,
                total_evaluations=1,
                successful_evaluations=1,
                failed_evaluations=0,
            )
            tracker.update_generation(i, metrics)

        assert len(tracker.metrics_history) == 3
        # Should have the last 3 entries: generations 2, 3, 4
        assert [m.generation for m in tracker.metrics_history] == [2, 3, 4]

    def test_increment_migration_count(self):
        """Test incrementing migration count."""
        tracker = StateTracker()
        assert tracker.total_migrations == 0

        tracker.increment_migration_count()
        assert tracker.total_migrations == 1

        tracker.increment_migration_count()
        assert tracker.total_migrations == 2

    def test_record_resource_usage(self):
        """Test recording resource usage."""
        tracker = StateTracker()

        usage = ResourceUsage(memory_usage_mb=100.0, cpu_usage_percent=50.0, worktree_count=5)
        tracker.record_resource_usage(usage)
        assert len(tracker.resource_history) == 1
        assert tracker.resource_history[0].memory_usage_mb == 100.0

    def test_record_resource_usage_disabled(self):
        """Test that resource usage is not recorded when disabled."""
        config = StateTrackerConfig(enable_resource_tracking=False)
        tracker = StateTracker(config=config)

        usage = ResourceUsage(memory_usage_mb=100.0, cpu_usage_percent=50.0, worktree_count=5)
        tracker.record_resource_usage(usage)
        assert len(tracker.resource_history) == 0

    def test_get_status_summary(self):
        """Test getting status summary."""
        tracker = StateTracker()
        tracker.start_run(100)

        summary = tracker.get_status_summary()
        assert summary["state"] == "running"
        assert summary["current_generation"] == 0
        assert summary["total_generations"] == 100
        assert summary["progress_percent"] == 0.0
        assert "duration_seconds" in summary

    def test_export_for_visualization(self):
        """Test exporting for visualization."""
        tracker = StateTracker()
        tracker.start_run(10)

        # Add some data
        tracker.record_timing("coder.generate", 1000.0)
        metrics = GenerationMetrics(
            generation=1,
            best_score=90.0,
            average_score=45.0,
            worst_score=10.0,
            total_evaluations=10,
            successful_evaluations=9,
            failed_evaluations=1,
        )
        tracker.update_generation(1, metrics)
        tracker.increment_migration_count()

        exported = tracker.export_for_visualization()
        assert exported["run_id"] == tracker.run_id
        assert exported["state"] == "running"
        assert exported["current_generation"] == 1
        assert "metrics_history" in exported
        assert "module_timing" in exported
        assert "resource_history" in exported
        assert "coder.generate" in exported["module_timing"]
        assert len(exported["metrics_history"]) == 1
        assert exported["total_migrations"] == 1

    def test_to_checkpoint_and_from_checkpoint(self):
        """Test checkpoint serialization and deserialization."""
        tracker = StateTracker()
        tracker.start_run(10)
        tracker.global_best_score = 95.0
        tracker.total_evaluations = 50
        tracker.total_migrations = 2

        for i in range(3):
            metrics = GenerationMetrics(
                generation=i,
                best_score=float(i * 10),
                average_score=float(i * 5),
                worst_score=0.0,
                total_evaluations=10,
                successful_evaluations=9 + i,
                failed_evaluations=1 - i,
            )
            tracker.update_generation(i, metrics)

        checkpoint_data = tracker.to_checkpoint()
        restored = StateTracker.from_checkpoint(checkpoint_data)

        assert restored.run_id == tracker.run_id
        assert restored.state == tracker.state
        assert restored.current_generation == tracker.current_generation
        assert restored.total_generations == tracker.total_generations
        assert restored.global_best_score == tracker.global_best_score
        assert restored.total_evaluations == tracker.total_evaluations
        assert restored.total_migrations == tracker.total_migrations
        assert len(restored.metrics_history) == 3

        # Check metrics match
        for original, restored_m in zip(tracker.metrics_history, restored.metrics_history, strict=True):
            assert original.generation == restored_m.generation
            assert original.best_score == restored_m.best_score
