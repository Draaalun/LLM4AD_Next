# 配置 API

`llm4ad.config` 提供了校验 `config.yaml` 和全局 `~/.llm4ad/settings.yaml` 的 Pydantic 模型。[配置指南](../guides/configuration.md)中提到的每个键，都对应这些模型中的一个字段。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `AppConfig` | 顶层流水线配置；`from_yaml`/`from_json`/`from_dict` 构造器 | `src/llm4ad/config/app.py` |
| `ProviderConfig` | LLM 提供者条目（api_key、model、temperature、max_retries 等） | `src/llm4ad/config/app.py` |
| `EmbeddingConfig` | 嵌入提供者，含 `local` 双端点模式 | `src/llm4ad/config/app.py` |
| `WorkspaceConfig` | 运行目录布局（`base_dir/{project_name}/{run_id}/{state,logs,checkpoints,best,…}`） | `src/llm4ad/config/app.py` |
| `LoggingConfig` | Loguru 级别 / 格式 / json 开关 | `src/llm4ad/config/app.py` |
| `MultimodalConfig` | 含图像的提示词和 `behavior_storage` 模式 | `src/llm4ad/config/app.py` |
| `EvolutionConfig`（及 `IslandGAConfig`、`DyCAConfig`、`MEoHConfig`） | 基于 `evolution.type` 的鉴别联合 | `src/llm4ad/config/evolution.py` |
| `EvaluatorConfig`、`CustomEvaluatorConfig`、`ExecutableEvaluatorConfig` | 基于 `evaluator.type` 的鉴别联合 | `src/llm4ad/config/evaluator.py` |
| `DatasetConfig`、`MetricPatternConfig`、`EvalContext` | 数据集发现、指标提取、运行时上下文 | `src/llm4ad/config/evaluator.py` |
| `CoderConfig`、`ClaudeCodeConfig`、`OpenCodeConfig`、`CustomCoderConfig` | 代码生成后端选择 | `src/llm4ad/config/coder.py` |
| `PlannerConfig`、`SamplerConfig` | 规划器及采样器链配置 | `src/llm4ad/config/planner.py` |
| `MemoryConfig` | 基于嵌入的记忆存储 | `src/llm4ad/config/memory.py` |
| `load_global_settings`、`merge_with_global_settings`、`load_yaml_with_env_expansion` | 全局设置加载与提供者合并 | `src/llm4ad/config/settings.py` |

## 加载配置

```python
from llm4ad.config import AppConfig

# 先加载 ~/.llm4ad/settings.yaml，按名称合并 providers，然后校验。
config = AppConfig.from_yaml("config.yaml")

# 跳过全局设置（适合做自包含测试）：
config = AppConfig.from_yaml("config.yaml", use_global_settings=False)
```

字符串值中的 `${VAR_NAME}` 占位符会用进程环境变量展开。被引用的变量若未设置，加载器会抛 `KeyError`，而不是静默替换为空串。

## 鉴别联合

`AppConfig` 在三个字段上使用 Pydantic 鉴别器。鉴别值决定具体子模型：

- `evaluator.type`：`"custom"` → `CustomEvaluatorConfig`，`"executable"` → `ExecutableEvaluatorConfig`。`type` 缺失时，`AppConfig.from_dict` 会按是否存在 `module:`（custom）或 `executable:`（executable）键来推断。
- `evolution.type`：`"island_ga"` → `IslandGAConfig`，`"dyca"` → `DyCAConfig`，`"meoh"` → `MEoHConfig`。
- `coder.type`：`"custom"`、`"claude_code"`、`"opencode"`。

## 全局设置合并

`~/.llm4ad/settings.yaml` 中的 provider 条目，会在 Pydantic 校验**之前**按名称合并进任务配置。任务级字段覆盖全局字段；任务配置中缺失的字段回退到全局定义。这样任务配置就可以仅按名称引用 provider。

```python
from llm4ad.config.settings import (
    load_global_settings,
    merge_with_global_settings,
)

global_data = load_global_settings()  # ~/.llm4ad/settings.yaml 或 $LLM4AD_SETTINGS_FILE
merged = merge_with_global_settings(global_data, task_data)
```

## 相关链接

- [配置指南](../guides/configuration.md) — 面向用户的 YAML 参考
- [提供商指南](../guides/providers.md) — 新增 provider
- 源码权威：`src/llm4ad/config/`
