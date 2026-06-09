"""Configuration management for LLM4AD.

Handles loading, validation, and schema definition for all configuration.
"""

from llm4ad.config.app import (
    AppConfig,
    LoggingConfig,
    ProviderConfig,
    RepoAnalyzerConfig,
    WorkspaceConfig,
)
from llm4ad.config.coder import (
    ClaudeCodeConfig,
    CoderConfig,
    CustomCoderConfig,
    OpenCodeConfig,
)
from llm4ad.config.evaluator import (
    CustomEvaluatorConfig,
    DatasetConfig,
    EvalContext,
    EvaluatorConfig,
    ExecutableEvaluatorConfig,
    MetricPatternConfig,
)
from llm4ad.config.evolution import (
    DyCAConfig,
    EvolutionConfig,
    IslandGAConfig,
    MEoHConfig,
)
from llm4ad.config.memory import (
    AutoExtractionConfig,
    MemoryCardConfig,
    MemoryConfig,
)
from llm4ad.config.planner import (
    BuildConfig,
    PlannerConfig,
    SamplerConfig,
)
from llm4ad.config.settings import (
    get_default_settings_path,
    load_global_settings,
    load_yaml_with_env_expansion,
    merge_with_global_settings,
)

__all__ = [
    # app
    "AppConfig",
    "ProviderConfig",
    "WorkspaceConfig",
    "LoggingConfig",
    "RepoAnalyzerConfig",
    # evaluator
    "DatasetConfig",
    "MetricPatternConfig",
    "EvaluatorConfig",
    "CustomEvaluatorConfig",
    "ExecutableEvaluatorConfig",
    "EvalContext",
    # coder
    "CoderConfig",
    "ClaudeCodeConfig",
    "OpenCodeConfig",
    "CustomCoderConfig",
    # memory
    "MemoryCardConfig",
    "AutoExtractionConfig",
    "MemoryConfig",
    # planner
    "SamplerConfig",
    "BuildConfig",
    "PlannerConfig",
    # evolution
    "EvolutionConfig",
    "DyCAConfig",
    "IslandGAConfig",
    # settings
    "MEoHConfig",
    "get_default_settings_path",
    "load_global_settings",
    "load_yaml_with_env_expansion",
    "merge_with_global_settings",
]
