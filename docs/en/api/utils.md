# Utilities API

`llm4ad.utils` is the small grab-bag of cross-cutting helpers. Most users never import from here directly, but two pieces — the registry pattern and the diff helpers — are visible whenever you extend the framework.

## Public surface

| Symbol | Purpose | Source |
|---|---|---|
| `Registrable` | Mixin that gives a base class a named registry (`discover`, `create`, `list`) | `src/llm4ad/utils/registry.py` |
| `register(name)` | Decorator factory used by every component family (`@register_provider`, `@register_evaluator`, …) | `src/llm4ad/utils/registry.py` |
| `apply_unified_diff` | Apply a unified diff to a file, returning the new content | `src/llm4ad/utils/diff_utils.py` |
| `parse_diff_stats` | Count added / removed / context lines in a diff (used in run summaries) | `src/llm4ad/utils/diff_utils.py` |
| `hash_content` | Stable content hash for diff base-version tracking | `src/llm4ad/utils/diff_utils.py` |
| `setup_logging`, `get_logger` | Loguru wrappers honoring `LoggingConfig` | `src/llm4ad/utils/logging.py` |

## The registry pattern

Every extensible component uses the same pattern:

```python
from llm4ad.utils.registry import Registrable

class BaseFoo(Registrable, registry_name="foo"):
    ...

class MyFoo(BaseFoo):
    ...

# Discover, then instantiate by name:
BaseFoo.discover("my_pkg.foos")     # imports modules so subclasses self-register
foo = BaseFoo.create("my_foo", config=cfg)
print(BaseFoo.list())               # ["my_foo", ...]
```

The `discover` step imports every module in the given path so that `class MyFoo(BaseFoo): ...` definitions get loaded and self-register. After that, `create(name, ...)` is the runtime equivalent of YAML's `type: my_foo`.

This is what powers `llm4ad list` and the YAML `type:` field in providers, planners, coders, evaluators, and orchestrators.

## Diff utilities

The `CustomCoder` (and any future diff-mode coder) emits unified diffs rather than full file contents. The helpers in `diff_utils.py` apply and audit those diffs.

```python
from llm4ad.utils.diff_utils import apply_unified_diff, parse_diff_stats

new_content = apply_unified_diff(old_content, diff_text)
stats = parse_diff_stats(diff_text)   # {"added": 12, "removed": 4, ...}
```

`base_file_hash` on a `CodeArtifact` lets the coder verify the diff still applies cleanly to the current worktree state before writing.

## Logging

```python
from llm4ad.utils.logging import setup_logging, get_logger

setup_logging(config.logging)        # honors level/format/file/console/json
log = get_logger(__name__)
log.info("provider call duration={:.1f}ms", elapsed)
```

LLM4AD uses [Loguru](https://github.com/Delgan/loguru) under the hood, so any module that calls `from loguru import logger` directly will also be wired up.

## See also

- [Provider API](provider.md), [Evaluator API](evaluator.md), [Orchestrator API](orchestrator.md) — see the registry pattern in action
- Source of truth: `src/llm4ad/utils/`
