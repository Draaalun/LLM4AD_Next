# 更新日志

LLM4AD 的所有重要变更都记录在这里。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 前缀（`feat:`、`fix:`、`ref:`）。

LLM4AD 目前处于 alpha 阶段（`0.1.x`），尚未发布带 tag 的版本。下面的章节按合并到 `main` 的月份分组。一旦发布版本号，会回填对应的版本块。

## [未发布] — 2026 年 5 月

### Web UI
- **feat**：文件创建/重命名 API、确认对话框、UX 改进 ([#106](https://github.com/llm4ad/llm4ad/pull/106))
- **fix**：快速进化分析支持多窗口 ([#104](https://github.com/llm4ad/llm4ad/pull/104))
- **fix**：nginx 现在会刷新上游服务的 DNS ([#107](https://github.com/llm4ad/llm4ad/pull/107))
- **fix**：构建阶段移到 common 块以避免构建错误 ([#103](https://github.com/llm4ad/llm4ad/pull/103))
- **fix**：AI 推荐不再返回空结果 ([#105](https://github.com/llm4ad/llm4ad/pull/105))

### CLI 与工具
- **feat（破坏性）**：`llm4ad chat` 与 `llm4ad build` 合并为单条三阶段命令（consult → build → run）([#93](https://github.com/llm4ad/llm4ad/pull/93))。原 `llm4ad build` / `llm4ad build-init` 的调用应迁移到 `llm4ad chat` 及对应 flag。详见[自动构建](guides/auto-builder.md)。
- **feat**：`llm4ad advise` 新增 `--all` 与 `--block-id`，统一返回信封，前端无需区分单块/批量 ([#94](https://github.com/llm4ad/llm4ad/pull/94))。
- **feat**：`llm4ad evolve check` 与 `llm4ad evolve clean`，用于检查和清理任务包中的 EVOLVE 标记 ([#89](https://github.com/llm4ad/llm4ad/pull/89))。
- **feat**：`llm4ad recommend` / `llm4ad advise` 新增 `--lang`，可本地化 LLM 自由文本输出 (`en` / `zh`) ([#92](https://github.com/llm4ad/llm4ad/pull/92))。

### Provider 与嵌入
- **feat**：DeepSeek thinking-mode 的 `reasoning_content` 在多轮对话中得以保留 ([#98](https://github.com/llm4ad/llm4ad/pull/98))。
- **feat（embeddings）**：通过新的 `local` provider 模式实现按任务路由，文本与代码可走不同端点 ([#90](https://github.com/llm4ad/llm4ad/pull/90))。详见 [Embeddings 与轨迹](guides/embeddings.md)。
- **feat**：批量嵌入请求 + 确定性 mock provider ([#88](https://github.com/llm4ad/llm4ad/pull/88))。

### 编排与运行
- **feat**：运行结束自动把最佳个体导出到稳定的 `best/` 目录（多目标运行还会按存档项产出 `best/pareto/<idx>/`）([#95](https://github.com/llm4ad/llm4ad/pull/95))。
- **fix**：worktree 创建时的 "invalid reference: HEAD" 错误已修复 ([#99](https://github.com/llm4ad/llm4ad/pull/99))。
- **fix**：lunarlander 评估器以 `episode_reward` 作为评分 ([#96](https://github.com/llm4ad/llm4ad/pull/96))。
- **fix/perf**：符号回归任务的双层搜索效率提升 ([#97](https://github.com/llm4ad/llm4ad/pull/97))。

## 2026 年 4 月

### CLI 与工具
- **feat**：`llm4ad recommend`（evolve-block 推荐器）— 扫描仓库，按目标推荐 core / expanded / alternative 三档候选 ([#74](https://github.com/llm4ad/llm4ad/pull/74))。
- **feat**：`llm4ad advise`（evolve-block 顾问）— 分析单个块对进化目标的契合度 ([#73](https://github.com/llm4ad/llm4ad/pull/73))。
- **feat**：自动化的 LLM4AD 应用构建器，含运行时校验 ([#46](https://github.com/llm4ad/llm4ad/pull/46))，后续被并入 `llm4ad chat` ([#93](https://github.com/llm4ad/llm4ad/pull/93))。
- **feat**：智能 EVOLVE 块分析与 driver 抽取 ([#52](https://github.com/llm4ad/llm4ad/pull/52))。
- **ref**：简化 EvolveDetector ([#54](https://github.com/llm4ad/llm4ad/pull/54))。

### Web UI
- **feat**：前后端代码首次落地 ([#58](https://github.com/llm4ad/llm4ad/pull/58))。
- **feat**：研究页 + Insights 报告生成 ([#68](https://github.com/llm4ad/llm4ad/pull/68))。
- **feat**：进化块选择、advisor 服务、轨迹可视化 ([#84](https://github.com/llm4ad/llm4ad/pull/84))。
- **feat**：3D HTML 轨迹可视化与算法嵌入流水线 ([#78](https://github.com/llm4ad/llm4ad/pull/78)、[#79](https://github.com/llm4ad/llm4ad/pull/79))。
- **feat**：暗色模式 + 自定义重试 + 异步嵌入 ([#80](https://github.com/llm4ad/llm4ad/pull/80))。

### 编排
- **feat**：MEoH（多目标启发式进化）作为新的编排器登场 ([#65](https://github.com/llm4ad/llm4ad/pull/65))。
- **feat**：DyCA 2.0 — 改进聚类与多池资源分配 ([#37](https://github.com/llm4ad/llm4ad/pull/37))。
- **feat**：评估与 LLM 流水线的并发控制 ([#35](https://github.com/llm4ad/llm4ad/pull/35))。

### 评估器与示例
- **feat**：`LLMJudgeEvaluator` 基类 + `life_planning` 示例 ([#32](https://github.com/llm4ad/llm4ad/pull/32)、[#44](https://github.com/llm4ad/llm4ad/pull/44)、[#49](https://github.com/llm4ad/llm4ad/pull/49)、[#55](https://github.com/llm4ad/llm4ad/pull/55))。
- **add**：ICM-MCM 2024D 与 2025D 应用 ([#48](https://github.com/llm4ad/llm4ad/pull/48)、[#51](https://github.com/llm4ad/llm4ad/pull/51))。
- **add**：ML 基准示例 ([#36](https://github.com/llm4ad/llm4ad/pull/36))。
- **feat**：符号回归的双层搜索方法 ([#33](https://github.com/llm4ad/llm4ad/pull/33))。
- **ref**：所有示例 `config.yaml` 统一对齐 `config.complete.yaml` ([#70](https://github.com/llm4ad/llm4ad/pull/70))。

### 框架
- **feat**：拆分 config schema、memory 抽取、可读时间格式、按代 token 日志 ([#31](https://github.com/llm4ad/llm4ad/pull/31))。
- **feat**：评估器模块重构（鉴别配置、build 系统、`EvalContext` 改名）([#20](https://github.com/llm4ad/llm4ad/pull/20))。
- **fix**：补回 `EvalContext` 缺失的 `behavior_storage` 字段 ([#43](https://github.com/llm4ad/llm4ad/pull/43))。

## 2026 年 3 月

平台首期工作 — 初版多目标 MEoH、DyCA、多模态进化（MLES）、交互式 consultant、mock provider 等。亮点：

- **feat**：交互式 consultant、全局设置、provider 流式输出 ([#22](https://github.com/llm4ad/llm4ad/pull/22))。
- **feat**：DyCA 编排器，用于多分布进化 ([#18](https://github.com/llm4ad/llm4ad/pull/18))。
- **feat**：多模态 LLM 进化策略（MLES）— 初版实现。
- **feat**：mock LLM provider + `tsp_benchmark_python_mock` 示例。
- **feat**：opencode coder ([#12](https://github.com/llm4ad/llm4ad/pull/12))。
- **feat**：可配置采样器选择 + 动态权重调整 ([#10](https://github.com/llm4ad/llm4ad/pull/10))。
- **feat**：TSP 示例、sorting benchmark 改为 Python 实现 ([#9](https://github.com/llm4ad/llm4ad/pull/9))。
- **feat**：首版实现，包含 custom naive coder、Island GA 编排器、运行摘要、日志框架 ([#2](https://github.com/llm4ad/llm4ad/pull/2)–[#7](https://github.com/llm4ad/llm4ad/pull/7))。

## 相关链接

- [贡献指南](https://github.com/Optima-CityU/LLM4AD_Next/blob/main/docs/zh/contributing/guidelines.md) — 驱动本日志的提交格式
- [GitHub 上的最新提交](https://github.com/Optima-CityU/LLM4AD_Next/commits/main) — 完整事实源
