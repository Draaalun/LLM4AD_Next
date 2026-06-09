# CLI 参考

LLM4AD 提供单一 CLI 入口 `llm4ad`，通过 `llm4ad.frontend.cli:main` 控制台脚本注册。本页记录每个命令、参数与退出码。

随时可以用 `llm4ad --help` 查看相同的命令清单。

## 顶层命令

| 命令 | 用途 |
|---|---|
| [`version`](#version) | 打印当前安装的 LLM4AD 版本 |
| [`list`](#list) | 列出注册的组件（providers、planners、coders、evaluators、orchestrators） |
| [`init`](#init) | 把配置模板（minimal / standard / complete）拷到当前目录 |
| [`run`](#run) | 用 YAML/JSON 配置运行算法设计流水线 |
| [`chat`](#chat) | 交互式 consultant + builder：从自然语言描述生成完整的 LLM4AD 应用 |
| [`advise`](#advise) | 把单个用户选中的代码块（或全部块）按进化目标分析 |
| [`advise-init`](#advise-init) | 生成 `advise_config.yaml` 模板 |
| [`recommend`](#recommend) | 扫描仓库，按目标契合度推荐 evolve-block 候选 |
| [`evolve`](#evolve) | 子命令组：检查、清理任务包中的 `EVOLVE` 标记 |

> **迁移提示。** 旧的 `llm4ad build` 与 `llm4ad build-init` 已合入 `llm4ad chat`（见 [#93](https://github.com/llm4ad/llm4ad/pull/93)）。原 build 的 flag（`--prompt`、`--code-path`、`--data-path`、`--non-interactive`、`--max-repair`）现在挂在 `chat` 上。占位的 `llm4ad config` 命令已经从 CLI 移除；查看配置请直接读 `~/.llm4ad/settings.yaml` 与任务配置。

通用约定：

- 全部命令使用 Typer + Rich。错误以 Rich 风格输出到 `stderr`，进程以非零码退出。
- 与 LLM 交互的命令既支持按 flag 配置（`--api-key`、`--model`、`--base-url`、`--provider-type`），也支持 `--provider <name>` 引用 `~/.llm4ad/settings.yaml` 中的命名 provider。
- 产出机器可读输出的命令（`advise`、`recommend`、`evolve check`、`evolve clean`）默认在 stdout 上输出 JSON，或加 `--json`；advise/recommend 还支持 `--pretty` 渲染 Rich 面板。

## version

打印 LLM4AD 版本。

```bash
llm4ad version
```

退出码：始终为 `0`。

## list

列出注册表中的组件。打印前会自动 discover `llm4ad.infra.provider`、`llm4ad.planner`、`llm4ad.coder`、`llm4ad.evaluator`、`llm4ad.orchestrator` 中的组件。

```bash
llm4ad list
llm4ad list --type provider
llm4ad list -t evaluator
```

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--type, -t` | _(全部)_ | 取值之一：`provider`、`planner`、`coder`、`evaluator`、`orchestrator` |

退出码：成功 `0`；`--type` 未知时 `1`。

## init

把内置配置模板拷到当前目录，编辑后用 `llm4ad run` 运行。

```bash
llm4ad init                       # 写出 minimal.yaml
llm4ad init standard
llm4ad init complete -o my.yaml
```

| 参数 / 选项 | 默认值 | 说明 |
|---|---|---|
| `level`（位置参数） | `minimal` | `minimal` / `standard` / `complete` 之一 |
| `--output, -o` | `<level>.yaml` | 输出文件名 |

行为：

- 目标文件已存在时会询问是否覆盖。
- 写出后打印下一步命令。

退出码：成功 `0`；level 未知或模板缺失 `1`；用户拒绝覆盖也是 `0`。

## run

跑一条算法设计流水线。加载 YAML/JSON 配置，构造 `LLM4AD` 实例，异步执行流水线，并打印摘要（含最佳个体；多目标运行时还会列精英存档）。

```bash
llm4ad run config.yaml
llm4ad run config.yaml --output-dir ./runs
llm4ad run config.yaml -r ./runs/proj/run-2026-05-13/checkpoints/last.json
```

| 参数 / 选项 | 默认值 | 说明 |
|---|---|---|
| `config`（位置参数，必填） | — | 流水线配置路径 |
| `--output-dir, -o` | _(从配置)_ | 覆盖配置中的 `base_dir` |
| `--resume, -r` | _(无)_ | 从指定路径的检查点续跑 |

输出：

- 运行前打印每条流水线摘要（`print_run_summary`）。
- 完成后打印最佳分数（或多目标的每目标最优）以及精英存档。
- coder 产生 worktree 时显示其名字。
- 末尾以 `Best snapshot:` 行指向运行结束时写入的稳定 `best/` 目录（详见[架构数据流 § 运行目录](../architecture/data-flow.md#运行目录布局)）。

退出码：完成（含未改进）`0`；任何流水线错误 `1`（打印完整 traceback）。

## chat

多轮交互式 consultant + builder。引导用户描述问题，自动生成评估器、算法模板、流水线配置，并可选立即启动运行。

此命令吸收了旧的 `llm4ad build` / `llm4ad build-init`（PR #93）。下表中的 flag 可让它非交互运行。

```bash
llm4ad chat                                                # 完整交互
llm4ad chat --provider my-deepseek -o ./my_task/
llm4ad chat --resume <session-id>
llm4ad chat --list-sessions

# 跳过多轮对话：直接给描述
llm4ad chat --prompt "进化排序算法，最小化比较次数"

# 在已有代码上改造
llm4ad chat --prompt "改进这个启发式" \
  --code-path ./solver/ --data-path ./data/

# 完全非交互（CI / 批处理）；需要 --prompt
llm4ad chat --prompt "进化排序" --non-interactive
```

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--provider, -p` | 全局设置中的第一个 provider | `~/.llm4ad/settings.yaml` 中的 provider 名 |
| `--resume, -r` | _(无)_ | 通过 session ID 或 state 文件路径恢复会话 |
| `--output, -o` | `./` | 生成应用输出目录 |
| `--list-sessions, -l` | `false` | 列出已保存会话并退出 |
| `--max-repair` | `3` | 校验阶段最大自动修复次数 |
| `--prompt` | _(无)_ | 直接给完整问题描述（跳过 Phase 1 对话） |
| `--non-interactive` | `false` | 跳过所有交互（需要 `--prompt`） |
| `--code-path` | _(无)_ | 现有算法代码路径（用于在其上改造） |
| `--data-path` | _(无)_ | 数据集目录或文件路径 |

行为：

- 要求 `~/.llm4ad/settings.yaml` 至少配置一个 provider，否则带提示退出。
- 用户完成咨询后可选直接启动生成的流水线。
- 生成文件落到 `{output}/{project_name}/`；目录结构与校验流水线见[自动构建](auto-builder.md)。

退出码：成功 `0`；Ctrl-C / EOF `130`；provider 解析或运行错误 `1`。

## advise

将一个用户选中的 EVOLVE 块（或仓库内全部块）按进化目标分析，返回结构化建议（summary、feasibility、significance、concerns、suggestions、rationale）。

命令**始终**返回相同信封 `{goal, repo_path, lang, count, results, errors}`，前端无需区分单块 / 多块。默认以 stdout JSON 形式输出，便于后端集成；`--pretty` 渲染 Rich 面板（每条结果一面板）。

```bash
llm4ad advise -g "minimize comparisons" -r ./solver --file algo.py --range 42:87
llm4ad advise -g "reduce tour length" -r ./solver           # 自动定位仓库内唯一的 EVOLVE 块
llm4ad advise -g "minimize sort comparisons" -r ./solver --block-id 'algo/sort.py#12-162'
llm4ad advise -g "tune all heuristics" -r ./solver --all --max-concurrency 8
llm4ad advise --config advise_config.yaml
llm4ad advise -g "improve policy" --code "$(cat snippet.py)"
```

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--goal, -g` | _(`--config` 缺省时必填)_ | 进化目标 |
| `--config, -f` | _(无)_ | advisor 配置 YAML 路径（替代各 flag） |
| `--repo, -r` | _(无)_ | 包含 block(s) 的仓库路径 |
| `--file` | _(无)_ | 含目标块的文件路径（相对 `--repo` 或绝对） |
| `--range` | _(无)_ | 1-based 闭区间行号，格式 `START:END`（如 `42:87`） |
| `--code` | _(无)_ | 直接分析的代码片段（替代 repo 路径） |
| `--block-id` | _(无)_ | `llm4ad evolve check` 输出的稳定 id（如 `algo/sort.py#12-162`），从 `--repo` 中选定唯一块 |
| `--all` | `false` | 并发分析 `--repo` 中所有合规 EVOLVE 块（标记有问题的文件会被跳过 — 先跑 `evolve check`） |
| `--max-concurrency` | `5` | `--all` 时最大并发 LLM 调用数 |
| `--api-key` | env `LLM4AD_ADVISE_API_KEY` | LLM API key |
| `--model` | `gpt-4o` | LLM 模型名 |
| `--base-url` | _(provider 默认)_ | LLM base URL |
| `--provider-type` | `openai_compatible` | `openai` / `anthropic` / `openai_compatible` 之一 |
| `--provider, -p` | _(无)_ | `~/.llm4ad/settings.yaml` 中的命名 provider |
| `--lang` | `en` | LLM 自由文本回答语言：`en` / `zh`，并写入信封的 `lang` |
| `--pretty` | `false` | 渲染 Rich 面板而非 JSON |

**互斥规则：** `--all` 与 `--code`/`--file`/`--range`/`--block-id` 互斥；`--block-id` 与 `--file`/`--range`/`--code` 互斥；`--code` 与 `--repo`/`--file`/`--range`/`--block-id`/`--all` 互斥。

**单块解析顺序：** `--code` → 显式 `--repo --file --range` → `--repo --block-id` → 自动定位 `--repo` 中唯一的 `EVOLVE` 块。

**输出信封：**

```json
{
  "goal": "...",
  "repo_path": "/abs/path",
  "lang": "en",
  "count": 1,
  "results": [ /* 每个分析过的块一个 BlockAdvice */ ],
  "errors":  [ /* 每块的失败信息，仅 --all 时填充 */ ]
}
```

`--all` 时：`results` 装载成功的块，`errors` 装载 LLM 调用失败的块（运行不会因此终止）。单块路径恒为 `count==1`、`errors==[]`。

退出码：成功 `0`；`AdvisorError`、`--range` 格式错误、`--goal`/`--config` 缺失、`--lang` 未知、互斥违规等 `1`。

## advise-init

生成 `advise_config.yaml` 模板供 `llm4ad advise --config <file>` 使用。

```bash
llm4ad advise-init
llm4ad advise-init -o my_advise.yaml
llm4ad advise-init -g "minimize sort comparisons"
```

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--output, -o` | `advise_config.yaml` | 目标路径 |
| `--goal, -g` | `""` | 预填 goal 字段 |

退出码：成功 `0`。

## recommend

按目标扫描仓库，分三档返回 evolve-block 候选：**core** 块（最小推荐）、可选 **expanded**（core 块的扩展变体）、可选 **alternatives**（仓库其他位置）。LLM4AD 当前一次只进化一个块 — 这三档是**可选项**，不是协同进化目标。

```bash
llm4ad recommend -g "reduce TSP tour length" -r ./solver
llm4ad recommend -g "improve policy reward" -r ./lander --pretty
llm4ad recommend -g "..." -r ./repo --max-concurrency 8 --include-raw
```

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--goal, -g` | _(必填)_ | 进化目标 |
| `--repo, -r` | _(必填)_ | 待扫描仓库 |
| `--api-key` | env `LLM4AD_ADVISE_API_KEY` | LLM API key |
| `--model` | `gpt-4o` | LLM 模型名 |
| `--base-url` | _(provider 默认)_ | LLM base URL |
| `--provider-type` | `openai_compatible` | `openai` / `anthropic` / `openai_compatible` 之一 |
| `--provider, -p` | _(无)_ | `~/.llm4ad/settings.yaml` 中的命名 provider |
| `--max-concurrency` | `5` | 富化阶段最大并发 advice 调用数 |
| `--include-raw` | `false` | 在输出中包含 discovery LLM 的原始文本（调试用） |
| `--lang` | `en` | LLM 自由文本回答语言：`en` / `zh`，会贯穿 discovery 和每块的 advice 调用，并写入输出 JSON 的 `lang` |
| `--pretty` | `false` | 渲染 Rich 面板而非 JSON |

输出：

- JSON 模式（默认）：完整的 `RepoRecommendations.to_dict()`，含 `core`、`expanded`、`alternatives`、`dropped_candidates`、`unreadable_files`、`lang`。
- `--pretty`：Rich 面板栈，含位置、推荐理由、advice（feasibility、significance、concerns、suggestions、rationale）。

退出码：成功 `0`；`--goal`/`--repo` 缺失、`--lang` 未知、`AdvisorError` 等 `1`。

## evolve

检查与清理任务包中 `EVOLVE` 标记的子命令组。

"标记行"指**注释行**：去掉注释起始符（`#`、`//`、`/*`、`<!--`）后，文本以 `EVOLVE_START` 或 `EVOLVE_END` 开头。docstring / 字符串字面量里出现的 `EVOLVE_START` 文本**不**算标记。

这两个命令背后的 Python API 在 `llm4ad.infra.repo_analyzer` 暴露：

```python
from llm4ad.infra.repo_analyzer import inspect_path, clean_path

inspect_path("path/to/pkg").to_dict()
clean_path("path/to/pkg", apply=True).to_dict()
```

### evolve check

检查任务包中的标记：统计合规块数、检测 nested / unbalanced 标记，并标出**当前活动块**（planner 当前以 `evolvable_blocks[0]` 喂给 coder 的那个）。

```bash
llm4ad evolve check                                    # 检查当前目录
llm4ad evolve check ./examples/applications/sorting_benchmark_python
llm4ad evolve check ./pkg --json                        # 机器可读
llm4ad evolve check ./pkg -i "*.py" -e "tests/**"
```

| 参数 / 选项 | 默认值 | 说明 |
|---|---|---|
| `path`（位置参数） | `.` | 任务包目录 |
| `--include, -i` | _(默认 detector 包含)_ | 要包含的 glob（可重复） |
| `--exclude, -e` | _(默认 detector 排除)_ | 要排除的 glob（可重复） |
| `--json` | `false` | 在 stdout 输出 `InspectResult.to_dict()` |

人类可读模式打印三个 Rich 表：

1. **Inspection summary** — root、files scanned、files with blocks、total blocks、total issues、active block id。
2. **Discovered blocks** — `Active` 列以 `*` 标出当前活动块。
3. **Issues** — 每个 `nested`、`unbalanced_start`、`unbalanced_end`、`unreadable` 异常一行。

JSON 模式输出同样数据：

```json
{
  "ok": true,
  "root": "/abs/path",
  "summary": {"files_scanned": 4, "files_with_blocks": 1, "blocks": 1,
              "issues": 0, "active_block_id": "policy/choose_action.py#27-87"},
  "files": [
    {"path": "policy/choose_action.py", "language": "python",
     "blocks": [{"line_start": 27, "line_end": 87, "comment_style": "#",
                 "block_name": "", "block_id": "policy/choose_action.py#27-87",
                 "active": true}],
     "issues": []}
  ]
}
```

`block_id` 形如 `f"{rel_posix_path}#{line_start}-{line_end}"`，跨运行稳定。

退出码：`ok=true`（无异常）`0`；存在异常或路径不存在 `1`。

### evolve clean

从任务包中删除所有 `EVOLVE_START` / `EVOLVE_END` 标记行，保留块体和上下文。**默认 dry-run**：不写盘，但报告会列出会被删除的行。

```bash
llm4ad evolve clean ./pkg                  # 干跑（不写盘）
llm4ad evolve clean ./pkg --apply          # 真正改写文件
llm4ad evolve clean ./pkg --apply --json
```

| 参数 / 选项 | 默认值 | 说明 |
|---|---|---|
| `path`（位置参数） | `.` | 任务包目录 |
| `--apply` | `false` | 真正改写文件；不带就只 dry-run |
| `--include, -i` | _(默认 detector 包含)_ | 要包含的 glob（可重复） |
| `--exclude, -e` | _(默认 detector 排除)_ | 要排除的 glob（可重复） |
| `--json` | `false` | 在 stdout 输出 `CleanResult.to_dict()` |

人类可读模式打印一个汇总表（mode、files changed、lines removed、errors）和一个按文件的表（被删除 / 将被删除的行号、`Written` 列）。JSON 模式输出同样数据：

```json
{
  "ok": true,
  "applied": true,
  "root": "/abs/path",
  "summary": {"files_changed": 1, "lines_removed": 2, "errors": 0},
  "files": [
    {"path": "algo/sort.py", "removed_lines": [2, 4], "written": true}
  ]
}
```

注意：

- 文件遍历遵循与 `EvolveDetector` 相同的默认 include / exclude，让清理器与分析器看到的文件集完全一致。
- 读写错误会按文件记录在 `error` 字段，并把 `ok` 翻为 `false`，但其他文件继续处理。

退出码：成功 `0`；任何文件出错或路径不存在 `1`。

## 相关链接

- [快速开始](quickstart.md) — 你的第一次端到端运行
- [配置](configuration.md) — YAML schema 参考
- [自动构建](auto-builder.md) — `llm4ad chat` 的端到端流程
- [Advisor](advisor.md)、[Recommender](recommender.md) — `advise` / `recommend` 的深入背景
