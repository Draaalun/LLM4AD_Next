# Config API

`llm4ad.config` ships the Pydantic schemas that validate `config.yaml` and the global `~/.llm4ad/settings.yaml`. Every key mentioned in the [Configuration Guide](../guides/configuration.md) corresponds to a field in one of these models.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `AppConfig` | Top-level pipeline config; `from_yaml`/`from_json`/`from_dict` constructors | `src/llm4ad/config/app.py` |
| `ProviderConfig` | LLM provider entry (api_key, model, temperature, max_retries, …) | `src/llm4ad/config/app.py` |
| `EmbeddingConfig` | Embedding provider, including the `local` dual-endpoint mode | `src/llm4ad/config/app.py` |
| `WorkspaceConfig` | Run directory layout (`base_dir/{project_name}/{run_id}/{state,logs,checkpoints,best,…}`) | `src/llm4ad/config/app.py` |
| `LoggingConfig` | Loguru level / format / json toggle | `src/llm4ad/config/app.py` |
| `MultimodalConfig` | Image-bearing prompts and `behavior_storage` mode | `src/llm4ad/config/app.py` |
| `EvolutionConfig` (and `IslandGAConfig`, `DyCAConfig`, `MEoHConfig`) | Discriminated union on `evolution.type` | `src/llm4ad/config/evolution.py` |
| `EvaluatorConfig`, `CustomEvaluatorConfig`, `ExecutableEvaluatorConfig` | Discriminated union on `evaluator.type` | `src/llm4ad/config/evaluator.py` |
| `DatasetConfig`, `MetricPatternConfig`, `EvalContext` | Dataset discovery, metric extraction, runtime context | `src/llm4ad/config/evaluator.py` |
| `CoderConfig`, `ClaudeCodeConfig`, `OpenCodeConfig`, `CustomCoderConfig` | Coder backend selection | `src/llm4ad/config/coder.py` |
| `PlannerConfig`, `SamplerConfig` | Planner and sampler chain configuration | `src/llm4ad/config/planner.py` |
| `MemoryConfig` | Embedding-based memory store | `src/llm4ad/config/memory.py` |
| `load_global_settings`, `merge_with_global_settings`, `load_yaml_with_env_expansion` | Global settings loader and provider merger | `src/llm4ad/config/settings.py` |

## Loading a config

```python
from llm4ad.config import AppConfig

# Loads ~/.llm4ad/settings.yaml first, merges providers by name, then validates.
config = AppConfig.from_yaml("config.yaml")

# Skip global settings (useful for self-contained tests):
config = AppConfig.from_yaml("config.yaml", use_global_settings=False)
```

`${VAR_NAME}` placeholders inside string values are expanded against the process environment. If a referenced variable is unset the loader raises `KeyError` rather than silently substituting an empty string.

## Discriminated unions

`AppConfig` uses Pydantic discriminators on three fields. The discriminator value selects which concrete schema is instantiated:

- `evaluator.type`: `"custom"` → `CustomEvaluatorConfig`, `"executable"` → `ExecutableEvaluatorConfig`. If `type` is missing, `AppConfig.from_dict` infers it from the presence of `module:` (custom) or `executable:` (executable).
- `evolution.type`: `"island_ga"` → `IslandGAConfig`, `"dyca"` → `DyCAConfig`, `"meoh"` → `MEoHConfig`.
- `coder.type`: `"custom"`, `"claude_code"`, `"opencode"`.

## Global settings merge

Provider entries from `~/.llm4ad/settings.yaml` are merged into the task config by name **before** Pydantic validation. Task-level fields override global ones; missing fields in the task config fall back to the global definition. This lets task configs reference providers by name only.

```python
from llm4ad.config.settings import (
    load_global_settings,
    merge_with_global_settings,
)

global_data = load_global_settings()  # ~/.llm4ad/settings.yaml or $LLM4AD_SETTINGS_FILE
merged = merge_with_global_settings(global_data, task_data)
```

## See also

- [Configuration Guide](../guides/configuration.md) — user-facing YAML reference
- [Providers Guide](../guides/providers.md) — adding a new provider
- Source of truth: `src/llm4ad/config/`
