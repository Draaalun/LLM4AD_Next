"""Automated task builder for LLM4AD.

Generates complete LLM4AD application directories from natural language
descriptions or existing codebases.

Config-based API (recommended for multi-user platforms)::

    from llm4ad.builder import generate_build_config, build_from_config_sync

    # Step 1: Generate a config template for the user to fill in
    generate_build_config("build_config.yaml", description="evolve sorting...")

    # Step 2: After user fills in credentials, run the build
    task_dir = build_from_config_sync("build_config.yaml")

Direct API (for programmatic use)::

    from llm4ad.builder import build_task_sync

    task_dir = build_task_sync(
        description="evolve sorting algorithms that minimize comparisons",
        output_dir="./examples/applications/",
        api_key="sk-...",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        on_progress=lambda stage, total, msg: print(f"[{stage}/{total}] {msg}"),
    )
"""

from llm4ad.builder.blueprint import AnalysisResult, TaskBlueprint
from llm4ad.builder.builder_config import (
    BuilderConfig,
    generate_build_config,
    load_build_config,
)
from llm4ad.builder.pipeline import (
    BuildError,
    build_from_config,
    build_from_config_sync,
    build_task,
    build_task_sync,
)

__all__ = [
    "AnalysisResult",
    "BuildError",
    "BuilderConfig",
    "TaskBlueprint",
    "build_from_config",
    "build_from_config_sync",
    "build_task",
    "build_task_sync",
    "generate_build_config",
    "load_build_config",
]
