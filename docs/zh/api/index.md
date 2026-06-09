# API 参考

本节记录 LLM4AD 的 Python 公共 API。目标读者是将 LLM4AD 嵌入更大系统的集成者、扩展框架的贡献者，以及需要超越 YAML 配置能力的高级用户。

参考按模块组织。每个页面列出公开的类/函数及其职责，给出最小可运行示例，并指向 `src/llm4ad/` 中的源码作为权威依据。

## 模块映射

| 模块 | 职责 | 页面 |
|---|---|---|
| `llm4ad.config` | YAML/JSON 配置和全局设置的 Pydantic 模型 | [配置](config.md) |
| `llm4ad.infra.provider` | LLM 与嵌入提供者抽象 | [提供商](provider.md) |
| `llm4ad.planner` | 算法规划器与采样器（提案生成） | [规划器](planner.md) |
| `llm4ad.coder` | 将算法落地为代码的代码生成后端 | [编码器](coder.md) |
| `llm4ad.evaluator` | 评估器基类、分派器与结果类型 | [评估器](evaluator.md) |
| `llm4ad.orchestrator` | 进化编排器（DyCA、Island GA、MEoH） | [编排器](orchestrator.md) |
| `llm4ad.infra` | 跨切面基础设施：状态、计时、仓库分析、版本控制 | [基础设施](infra.md) |
| `llm4ad.utils` | 注册表、日志辅助、差异工具 | [工具](utils.md) |

## 顶层入口

```python
from llm4ad import LLM4AD

llm4ad = LLM4AD("config.yaml")
result = await llm4ad.run()
print(result.best_individual.score)
```

`LLM4AD` 是唯一的顶层入口，负责加载配置、装配组件、运行流水线。`llm4ad run` 命令的底层调用的就是它。

## 注册表模式

每个可扩展组件（provider、planner、coder、evaluator、orchestrator）都继承 `Registrable`，通过 `registry_name` 以字符串名称注册。组件通过 `BaseClass.discover("module.path")` 懒加载发现，再通过 `BaseClass.create(name, config=...)` 创建实例。这就是 YAML 中 `type:` 字段背后的机制。

```python
from llm4ad.infra.provider.base import BaseProvider

BaseProvider.discover("llm4ad.infra.provider")
provider = BaseProvider.create("openai_compatible", config=provider_cfg)
```

注册表实现细节参见[工具](utils.md)。

## 稳定性

每个模块 `__init__.py` 中重导出的公共符号在 patch 版本间保持稳定。任何从私有子模块（路径以 `_` 开头，或未通过 `__init__.py` 暴露的模块）导入的内容可能在不通知的情况下变更。如有疑问，请优先使用各模块页面中展示的 import 形式。

## 相关链接

- [配置指南](../guides/configuration.md) — 面向用户的 YAML 参考
- [架构概览](../architecture/overview.md) — 模块之间如何协作
