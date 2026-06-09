# API Reference

This section documents the public Python API surface of LLM4AD. It is intended for integrators who embed LLM4AD into a larger system, contributors extending the framework with new components, and advanced users who need behaviour beyond the YAML config.

The reference is organized by module. Each page lists the public classes/functions, their responsibility, and a minimal usage snippet, with pointers back to the source of truth in `src/llm4ad/`.

## Module map

| Module | Responsibility | Page |
|---|---|---|
| `llm4ad.config` | Pydantic schemas for the YAML/JSON config and global settings | [Config](config.md) |
| `llm4ad.infra.provider` | LLM and embedding provider abstractions | [Provider](provider.md) |
| `llm4ad.planner` | Algorithm planners and samplers (proposal generation) | [Planner](planner.md) |
| `llm4ad.coder` | Code-generation backends that materialize an algorithm | [Coder](coder.md) |
| `llm4ad.evaluator` | Evaluator base classes, dispatcher, and result types | [Evaluator](evaluator.md) |
| `llm4ad.orchestrator` | Evolution orchestrators (DyCA, Island GA, MEoH) | [Orchestrator](orchestrator.md) |
| `llm4ad.infra` | Cross-cutting infrastructure: state, timing, repo analyzer, version control | [Infrastructure](infra.md) |
| `llm4ad.utils` | Registry, logging helpers, diff utilities | [Utilities](utils.md) |

## Top-level entry point

```python
from llm4ad import LLM4AD

llm4ad = LLM4AD("config.yaml")
result = await llm4ad.run()
print(result.best_individual.score)
```

`LLM4AD` is the single entry point that loads a config, wires the components together, and runs the pipeline. It corresponds to what the `llm4ad run` CLI invokes under the hood.

## Registry pattern

Every extensible component (provider, planner, coder, evaluator, orchestrator) inherits from `Registrable` and registers under a string name via `registry_name`. Components are discovered lazily through `BaseClass.discover("module.path")` before a `BaseClass.create(name, config=...)` call. This is what makes the YAML `type:` field work.

```python
from llm4ad.infra.provider.base import BaseProvider

BaseProvider.discover("llm4ad.infra.provider")
provider = BaseProvider.create("openai_compatible", config=provider_cfg)
```

See [Utilities](utils.md) for the registry implementation details.

## Stability

Public symbols re-exported from a module's `__init__.py` are considered stable across patch releases. Anything imported from a private submodule (a path starting with `_`, or a module not surfaced via `__init__.py`) may change without notice. When in doubt, prefer the imports shown in the per-module pages below.

## See also

- [Configuration Guide](../guides/configuration.md) — YAML schema reference for users
- [Architecture Overview](../architecture/overview.md) — how the modules fit together
