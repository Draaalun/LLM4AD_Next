# Evaluation Patterns: Subprocess Isolation

This document explains the subprocess evaluation architecture in LLM4AD,
analyzes parallelism characteristics, and discusses multi-algorithm evaluation.

## 1. Why Subprocess?

LLM-generated algorithm code is **untrusted**. It may segfault, deadlock, call
`sys.exit()`, corrupt global state, or leak memory. Running evaluations in a
subprocess ensures the main orchestrator process is protected.

| Fault | Without subprocess | With subprocess |
|-------|-------------------|-----------------|
| Segfault | Main process crashes | `returncode != 0` -> score=0 |
| `sys.exit()` | Main process exits | `returncode != 0` -> score=0 |
| Infinite loop | Main process hangs | `asyncio.wait_for` timeout -> `proc.kill()` |
| Memory leak | Accumulates to OOM | OS reclaims on process exit |
| `sys.modules` pollution | Later evaluations get wrong code | Complete isolation |

## 2. Two Subprocess Variants

Both use `asyncio.create_subprocess_exec()` for async parallelism.
The **only** difference is what the evaluator spawns as the subprocess.

### Variant A: Separate Script (TSP, Sorting)

```
evaluate() call:
  1. Load instance JSON from cfg.data_path
  2. await asyncio.create_subprocess_exec("python", "solve.py", input_json)
  3. await proc.communicate()    <- yields control to event loop
  4. Parse JSON from stdout
  5. Return EvaluationResult
```

The algorithm file has its own `main()` + `if __name__ == "__main__"` that reads
JSON from argv and prints JSON to stdout.

**When to use:** Algorithm is a stateless function (one call per evaluation).

### Variant B: Self-Spawning Evaluator (LunarLander)

```
evaluate() call:
  1. Load instance JSON from cfg.data_path
  2. await asyncio.create_subprocess_exec("python", "evaluator.py", config_json)
  3. await proc.communicate()    <- yields control to event loop
  4. Parse JSON from stdout
  5. Return EvaluationResult

Subprocess (__main__ block):
  1. Parse config from sys.argv[1]
  2. Load algorithm module via importlib.util.spec_from_file_location()
  3. Run simulation/loop calling algorithm function ~200 times
  4. print(json.dumps(result))
```

The evaluator spawns **itself** as a subprocess. The `__main__` block at the
bottom of the evaluator file handles the actual execution.

**When to use:** Evaluator needs to orchestrate the algorithm (simulation loop,
environment setup, multiple function calls per evaluation).

### Variant Comparison

| Aspect | Separate Script (A) | Self-Spawning (B) |
|--------|--------------------|--------------------|
| Subprocess target | `python solve.py` | `python evaluator.py` |
| Algorithm loading | Script loads itself | `__main__` loads via importlib |
| Calls per eval | 1 | Many (~200 for RL) |
| Extra code needed | Algorithm has `main()` | Evaluator has `__main__` |
| Use case | TSP, Sorting | LunarLander, RL tasks |

## 3. Parallelism Analysis

### How the dispatcher parallelizes (one algorithm, N instances)

```python
# dispatcher.py -- parallel mode
if self._parallel:
    tasks = [evaluator.evaluate(cfg) for cfg in instance_configs]
    raw_results = await asyncio.gather(*tasks)
```

`asyncio.gather()` runs coroutines concurrently. It switches between them
at `await` points. Both subprocess variants yield at `await proc.communicate()`,
so all instances run as true parallel OS processes.

**Benchmark (TSP, 5 instances on 10-node problems):**
```
Serial:   0.538s
Parallel: 0.118s
Speedup:  4.56x   (near-ideal for 5 instances)
```

### Multi-Algorithm Parallel ("evaluate as they arrive")

The orchestrator runs `asyncio.gather()` across all offspring in a generation.
Each offspring's lifecycle (plan -> code -> evaluate) runs as an async coroutine.
Since every step has `await` points (LLM calls, subprocess evaluation), the event
loop naturally interleaves them:

```
offspring 1: [plan ~2s] [code ~3s] [eval ~0.5s]  done
offspring 2:    [plan ~2s]   [code ~3s]   [eval ~0.5s]  done
offspring 3:       [plan ~2s]      [code ~3s]   [eval ~0.5s]
                 interleaved via event loop
```

No special configuration needed — this is how `asyncio.gather()` works when
all coroutines have `await` points.

## 4. Historical: Direct Import Pattern (Deprecated)

Earlier versions of LunarLander used `importlib.import_module()` to load the
policy module directly in-process (no subprocess). This had two critical issues:

### Issue 1: No fault isolation

Policy code that segfaulted, called `sys.exit()`, or leaked memory would crash
the main orchestrator process.

### Issue 2: sys.modules caching bug

`importlib.import_module("choose_action")` consults `sys.modules` first. When
multiple algorithms are evaluated (each in a different worktree), the first import
populates `sys.modules["choose_action"]`, and all subsequent imports silently
return **that same cached module** — even if `sys.path` points at a different worktree.

**Symptoms:** Algorithm B gets Algorithm A's code. Scores are identical for
different algorithms. Hard to debug because no error is raised.

**Fix (if you must use direct import):** Use `importlib.util.spec_from_file_location()`
with a unique module name. This bypasses `sys.modules` entirely:

```python
# WRONG -- returns cached module from first worktree:
sys.path.insert(0, str(algo_dir))
module = importlib.import_module("choose_action")

# CORRECT -- loads from exact file path every time:
file_path = algo_dir / "choose_action.py"
module_name = f"_policy_{id(self)}_{hash(str(file_path))}"
spec = importlib.util.spec_from_file_location(module_name, str(file_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

**Recommendation:** Use subprocess instead. It avoids both issues and provides
true multi-instance parallelism as a bonus.

## 5. Implementation Status

| Change | Status |
|--------|--------|
| Async subprocess for TSP/Sorting | Done |
| Subprocess isolation for LunarLander | Done |
| sys.modules fix in importlib path | Done |
| Multi-algorithm parallel via asyncio.gather | Done (natural from orchestrator design) |
| Batched dispatch_batch in orchestrator | Done |
