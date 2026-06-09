# 编码器 API

`llm4ad.coder` 把规划器提出的算法落地为可运行代码。编码器在工作树（worktree）中编辑文件、调用底层 LLM 后端，并把结果交给评估器。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `BaseCoder` | 抽象编码器；继承并调用 `register_coder("name")` | `src/llm4ad/coder/base.py` |
| `ClaudeCodeCoder` | 用 Anthropic Claude Code CLI 进行 agent 式编辑 | `src/llm4ad/coder/claude_code.py` |
| `OpenCodeCoder` | 用 OpenCode CLI 进行 agent 式编辑 | `src/llm4ad/coder/opencode.py` |
| `CustomCoder` | 朴素 LLM 编码器；通过 unified-diff 直接编辑 EVOLVE 块 | `src/llm4ad/coder/custom_naive_coder.py` |
| `GenerateResult`、`GenerateStatus` | 编码器调用的返回信封（`SUCCESS`、`FAILED`、`TIMEOUT`、`PARTIAL`） | `src/llm4ad/coder/base.py` |

## 工作树集成

每次编码调用都对一个新建的 git 工作树执行，由 `llm4ad.infra.version_control` 管理（详见[基础设施](infra.md)）。这样多个并发个体之间可以隔离，无需污染主仓库；评估完成后工作树被回收，但 `best/` 目录保留最佳的副本（cli.py:184）。

`GenerateResult.working_dir` 始终指向工作树根，`generated_files` 是相对路径。把工作树路径传给评估器作为 `EvalContext.project_root`：

```python
from llm4ad.coder.base import BaseCoder
from llm4ad.config.schema import EvalContext

BaseCoder.discover("llm4ad.coder")
coder = BaseCoder.create("custom", config=app_config.coder, provider=provider)

result = await coder.generate(algorithm, working_dir=str(worktree.path))
if result.is_success:
    ctx = EvalContext(project_root=result.working_dir, data_path="...", timeout=60.0)
```

## EVOLVE 块替换

编码器只编辑标记在 `# EVOLVE_START` / `# EVOLVE_END` 之间的代码区域。检测、清理与活动块解析由 `llm4ad.infra.repo_analyzer` 处理（参见 [Infrastructure](infra.md) 与 [`llm4ad evolve check`/`evolve clean`](../guides/cli.md#evolve)）。

`CustomCoder` 使用 unified-diff 内容模式：`Algorithm.code_artifacts[i].content_mode == "diff"` 时，diff 通过 `apply_unified_diff` 应用到当前工作树文件（详见[工具](utils.md)），便于审计和回滚。

## 选择编码器

| 任务 | 推荐 | 原因 |
|---|---|---|
| 单文件、明确的 EVOLVE 块 | `custom` | 最快、最便宜、可解释（unified-diff） |
| 多文件 / agent 式编辑 / 自由风格重写 | `claude_code` 或 `opencode` | 让 agent 自主决策跨文件编辑 |
| 测试 / CI / 快速迭代提示词 | 任意 + `MockProvider` | 端到端可重现，无需真实 LLM 调用 |

agent 式编码器是单独的安装 extra；详见 [安装](../guides/installation.md)。

## 相关链接

- [编码器配置](../guides/configuration.md#coder) — `coder:` 配置块
- [CLI 参考](../guides/cli.md#evolve) — 标记块工具
- 源码权威：`src/llm4ad/coder/`
