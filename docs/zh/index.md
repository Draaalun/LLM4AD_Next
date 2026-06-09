# LLM4AD 文档

欢迎使用 **LLM4AD** — 基于大语言模型与进化计算的自动算法设计平台。本站点同时是开源仓库的标准参考，也是 Web 应用内"使用手册"的内容来源。

## LLM4AD 是什么

LLM4AD 把 LLM 当作"提案者"，把进化计算当作"评估与选择者"，二者协同迭代搜索更优算法。它的设计目标是：

- 让 LLM 在你已有的代码库里只编辑特定的 `EVOLVE_START` / `EVOLVE_END` 标记块；
- 通过 git 工作树并行评估多个候选个体，互不污染；
- 把进化策略（Island GA、DyCA、MEoH）、评估方式（Python / 可执行 / Benchmark / LLM-judge）、Provider（OpenAI 兼容、Anthropic、Mock）解耦为可注册组件；
- 一份 YAML 配置驱动整条流水线，CLI、Python API 与 Web UI 三种使用方式共享。

## 核心特性

- **多种编排策略**：[Island GA](guides/island-ga.md) 经典并行；[DyCA](guides/dyca.md) 按问题实例聚类、专家化；[MEoH](guides/meoh.md) 多目标 Pareto 进化。详见[编排方法](guides/orchestration.md)。
- **灵活的评估器层**：自定义 `PythonEvaluator` / `BenchmarkEvaluator`、`ExecutableEvaluator`、`LLMJudgeEvaluator` 自由组合，支持多实例并行与多目标聚合。
- **多模态进化**：评估器返回的图像 / 轨迹可直接进入提示词，让 LLM "看见"算法行为（[Multimodal](guides/multimodal.md)）。
- **嵌入与轨迹可视化**：`local` 双端点模式让代码与文本走不同嵌入；3D HTML 轨迹图把进化历程可视化（[Embeddings 与轨迹](guides/embeddings.md)）。
- **CLI + Web UI**：CLI（`llm4ad run` / `chat` / `advise` / `recommend` / `evolve`）一键完成；同时提供 Docker 化的前后端 Web UI（[Web UI 概览](web-ui/overview.md)）。
- **自动构建（Auto Builder）**：用 `llm4ad chat` 通过自然语言一次性生成评估器、算法模板、YAML 配置（[Auto Builder](guides/auto-builder.md)）。

## 快速开始

5 分钟内跑通你的第一个进化：

```bash
git clone https://github.com/Optima-CityU/LLM4AD_Next.git
cd llm4ad
uv sync

export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o-mini"

llm4ad run examples/applications/sorting_benchmark_python/config.yaml
```

完整流程见[快速入门](guides/quickstart.md)。

## 路径图

| 你想做什么 | 从这里开始 |
|---|---|
| 第一次跑 LLM4AD | [安装](guides/installation.md) → [快速入门](guides/quickstart.md) |
| 看懂一份 YAML 的每个字段 | [配置指南](guides/configuration.md) |
| 把自己的项目接进来 | [评估器指南](guides/evaluators.md) + [Auto Builder](guides/auto-builder.md) |
| 选一个编排器 | [编排方法概览](guides/orchestration.md) |
| 接一个新 LLM 服务 | [Provider 指南](guides/providers.md) |
| 调精细的耗时与并发 | [计时与指标](guides/timing-metrics.md) + [高级配置](guides/advanced.md) |
| 用 Web UI / 自部署 | [Web UI 概览](web-ui/overview.md) + [前端集成](web-ui/frontend-integration.md) |
| 做扩展开发 | [架构概览](architecture/overview.md) → [API 参考](api/index.md) |
| 给项目贡献 | [贡献指南](contributing/guidelines.md) → [开发环境](contributing/development.md) |

## 项目结构

```
LLM4AD/
├── src/llm4ad/             # Python 库
│   ├── config/              # Pydantic schema 与全局设置
│   ├── infra/               # provider / 状态 / 计时 / 仓库分析 / 工作树
│   ├── planner/             # 规划器与采样器（提案生成）
│   ├── coder/               # 代码生成后端（custom / claude_code / opencode）
│   ├── evaluator/           # 评估器基类与分派器
│   ├── orchestrator/        # 进化编排器（island_ga / dyca / meoh）
│   ├── consultant/          # llm4ad chat 后端
│   ├── advisor/             # llm4ad advise / recommend 后端
│   ├── frontend/cli.py      # CLI 入口
│   └── utils/               # 注册表与跨切面辅助
├── src/backend/            # FastAPI Web 后端
├── src/frontend/           # React + Vite 前端
├── examples/applications/  # 17 个可运行示例项目
├── docs/                   # 双语文档（你正在读的这个）
└── pyproject.toml
```

## 最新进展

近期亮点（详见[更新日志](changelog.md)）：

- **`llm4ad chat` / `llm4ad build` 已合并**为统一的三阶段命令。
- **`best/` 稳定快照**在每次运行末态导出（多目标会有 `best/pareto/<idx>/`）。
- **MEoH 编排器**支持真正的多目标 Pareto 前沿。
- **嵌入 `local` 模式**让文本和代码走不同端点。
- **`llm4ad evolve check / clean`** 让 EVOLVE 标记的检查与清理有了 CLI。

## 许可

本项目以 MIT 许可证开源 — 详见 [LICENSE](license.md)。

## 支持

- 📖 [文档站](https://llm4ad.readthedocs.io)
- 💬 [GitHub Discussions](https://github.com/Optima-CityU/LLM4AD_Next/discussions)
- 🐛 [Issue Tracker](https://github.com/Optima-CityU/LLM4AD_Next/issues)
