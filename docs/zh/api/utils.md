# 工具 API

`llm4ad.utils` 是一个小的横切工具包。多数用户不会直接 import 这里的内容，但有两块 — 注册表模式和 diff 工具 — 在你扩展框架时一定会遇到。

## 公共接口

| 符号 | 职责 | 源码 |
|---|---|---|
| `Registrable` | 给基类加上命名注册表的 mixin（`discover`、`create`、`list`） | `src/llm4ad/utils/registry.py` |
| `register(name)` | 装饰器工厂；被各组件家族使用（`@register_provider`、`@register_evaluator`…） | `src/llm4ad/utils/registry.py` |
| `apply_unified_diff` | 对文件应用 unified diff，返回新内容 | `src/llm4ad/utils/diff_utils.py` |
| `parse_diff_stats` | 统计 diff 中新增/删除/上下文行数（用在运行摘要里） | `src/llm4ad/utils/diff_utils.py` |
| `hash_content` | 稳定的内容哈希，用于追踪 diff 的基版本 | `src/llm4ad/utils/diff_utils.py` |
| `setup_logging`、`get_logger` | 遵循 `LoggingConfig` 的 Loguru 包装 | `src/llm4ad/utils/logging.py` |

## 注册表模式

每个可扩展组件都用同一套范式：

```python
from llm4ad.utils.registry import Registrable

class BaseFoo(Registrable, registry_name="foo"):
    ...

class MyFoo(BaseFoo):
    ...

# 先 discover，再按名实例化：
BaseFoo.discover("my_pkg.foos")     # import 模块，让子类自动注册
foo = BaseFoo.create("my_foo", config=cfg)
print(BaseFoo.list())               # ["my_foo", ...]
```

`discover` 把指定路径下的模块全部 import，让 `class MyFoo(BaseFoo): ...` 这样的定义被加载并自我注册。之后 `create(name, ...)` 就等同于 YAML 中 `type: my_foo` 的运行时形式。

`llm4ad list` 命令以及 provider / planner / coder / evaluator / orchestrator 中的 YAML `type:` 字段都靠它驱动。

## Diff 工具

`CustomCoder`（以及未来任何 diff 模式的 coder）发的是 unified diff，而不是完整文件内容。`diff_utils.py` 提供应用和审计这些 diff 的工具。

```python
from llm4ad.utils.diff_utils import apply_unified_diff, parse_diff_stats

new_content = apply_unified_diff(old_content, diff_text)
stats = parse_diff_stats(diff_text)   # {"added": 12, "removed": 4, ...}
```

`CodeArtifact` 上的 `base_file_hash` 字段让 coder 在写盘前先验证 diff 仍然适用于当前工作树状态。

## 日志

```python
from llm4ad.utils.logging import setup_logging, get_logger

setup_logging(config.logging)        # 遵循 level/format/file/console/json
log = get_logger(__name__)
log.info("provider call duration={:.1f}ms", elapsed)
```

LLM4AD 底层用 [Loguru](https://github.com/Delgan/loguru)，因此任何模块直接 `from loguru import logger` 也会自动接入相同配置。

## 相关链接

- [Provider API](provider.md)、[Evaluator API](evaluator.md)、[Orchestrator API](orchestrator.md) — 注册表实战
- 源码权威：`src/llm4ad/utils/`
