"""Tests for PlannerConfig and SamplerConfig."""

from llm4ad.config.schema import AppConfig, CustomEvaluatorConfig, DatasetConfig, PlannerConfig, SamplerConfig


class TestSamplerConfig:
    """Tests for SamplerConfig."""

    def test_sampler_config_creation(self):
        """Test creating a SamplerConfig."""
        config = SamplerConfig(
            name="init_sampler",
            config={"temperature": 0.7}
        )

        assert config.name == "init_sampler"
        assert config.config == {"temperature": 0.7}

    def test_sampler_config_defaults(self):
        """Test SamplerConfig with defaults."""
        config = SamplerConfig(name="mutation_sampler")

        assert config.name == "mutation_sampler"
        assert config.config == {}


class TestPlannerConfig:
    """Tests for PlannerConfig."""

    def test_planner_config_creation(self):
        """Test creating a PlannerConfig."""
        config = PlannerConfig(
            type="llm_evolution",
            samplers=[
                SamplerConfig(name="init_sampler"),
                SamplerConfig(name="mutation_sampler"),
            ],
            selection_strategy="weighted"
        )

        assert config.type == "llm_evolution"
        assert len(config.samplers) == 2
        assert config.selection_strategy == "weighted"

    def test_planner_config_defaults(self):
        """Test PlannerConfig with defaults."""
        config = PlannerConfig()

        assert config.type == "llm_evolution"
        assert config.samplers == []
        assert config.selection_strategy == "weighted"


class TestAppConfigWithPlanner:
    """Tests for AppConfig with planner field."""

    def _create_minimal_app_config(self, **kwargs):
        """Create a minimal AppConfig with required fields."""
        return AppConfig(
            project_name="test_project",
            evaluator=CustomEvaluatorConfig(
                module="test_module:TestEvaluator",
                dataset=DatasetConfig(mode="files", files=["test.json"]),
            ),
            **kwargs,
        )

    def test_app_config_with_planner(self):
        """Test AppConfig includes planner field."""
        config = self._create_minimal_app_config(
            planner=PlannerConfig(
                type="llm_evolution",
                samplers=[
                    SamplerConfig(name="init_sampler"),
                ],
            ),
        )

        assert config.planner is not None
        assert config.planner.type == "llm_evolution"
        assert len(config.planner.samplers) == 1

    def test_app_config_planner_from_dict(self):
        """Test creating AppConfig from dict with planner."""
        data = {
            "project_name": "test_project",
            "evaluator": {
                "type": "custom",
                "module": "test_module:TestEvaluator",
                "dataset": {"mode": "files", "files": ["test.json"]},
            },
            "planner": {
                "type": "llm_evolution",
                "samplers": [
                    {"name": "init_sampler"},
                    {"name": "mutation_sampler", "config": {"temperature": 0.5}},
                ],
                "selection_strategy": "random",
            },
        }

        config = AppConfig.from_dict(data)

        assert config.planner is not None
        assert config.planner.type == "llm_evolution"
        assert len(config.planner.samplers) == 2
        assert config.planner.samplers[0].name == "init_sampler"
        assert config.planner.samplers[1].name == "mutation_sampler"
        assert config.planner.samplers[1].config == {"temperature": 0.5}
        assert config.planner.selection_strategy == "random"

    def test_app_config_to_dict_with_planner(self):
        """Test converting AppConfig with planner to dict."""
        config = self._create_minimal_app_config(
            planner=PlannerConfig(
                type="llm_evolution",
                samplers=[SamplerConfig(name="init_sampler")],
            ),
        )

        data = config.to_dict()

        assert "planner" in data
        assert data["planner"]["type"] == "llm_evolution"
        assert len(data["planner"]["samplers"]) == 1
