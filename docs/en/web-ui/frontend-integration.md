# Frontend Integration

This guide explains how to embed LLM4AD into a multi-user web platform — that is, how to surface the auto-builder (`llm4ad chat`) and pipeline runner from your own backend / frontend instead of running the CLI directly. It assumes you've already read [Web UI Overview](overview.md) for the bundled UI; this page is for *integrators*.

## Recommended workflow

```
User input (web form)
  → generate config / build_config
  → call LLM4AD API (sync, async, or queued)
  → poll status
  → list and serve generated files
  → trigger evolution run (optional)
```

> Note: as of [#93](https://github.com/llm4ad/llm4ad/pull/93), the `llm4ad build` and `llm4ad build-init` CLI commands have been merged into a unified `llm4ad chat`. The Python builder API (`build_task_sync`, `build_from_config`, `build_from_config_sync`) remains stable and is what you'll actually call from a backend integration. The CLI shorthand changes; the underlying API does not.

## 1. Collect user input

A typical form collects:

**Required**
- **Problem description** (textarea) — natural-language task description
- **LLM provider** (dropdown) — OpenAI, Anthropic, OpenAI-compatible, or a named entry in user settings
- **API key** (password input) — user's LLM API key
- **Model** (dropdown) — `gpt-4o-mini`, `claude-opus-4`, etc.

**Optional**
- **Project name** (text) — auto-generated if empty
- **Output directory** (hidden) — set by your backend to a user-scoped path
- **Multimodal** (checkbox) — enables visualization-aware evaluator scaffolding
- **From existing code** (file upload) — adapt rather than start from scratch
- **Dataset** (file upload) — custom evaluation data

## 2. Build the config

```python
import textwrap
from pathlib import Path

config_content = f"""
builder:
  type: "openai_compatible"
  base_url: "{base_url}"
  api_key: "{api_key}"
  model: "{model}"
  max_repair_attempts: 3

task:
  description: |
{textwrap.indent(description, '    ')}
  output_dir: "/data/llm4ad_builds/{user_id}/{task_id}"
  project_name: "{project_name}"
  multimodal: {str(multimodal).lower()}
"""

config_path = Path(f"/tmp/builds/{user_id}/{task_id}/build_config.yaml")
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(config_content)
```

**Security**: never store API keys in plain text. Encrypt them at rest (e.g. Fernet, KMS), and consider using the user's own key so they pay for LLM usage.

## 3. Call the builder API

### Option A — synchronous (simple, blocking)

```python
from llm4ad.builder import build_from_config_sync

try:
    task_dir = build_from_config_sync(
        str(config_path),
        on_progress=lambda stage, total, msg: print(f"[{stage}/{total}] {msg}"),
    )
except Exception as e:
    return {"status": "error", "message": str(e)}
return {"status": "success", "task_dir": task_dir}
```

Blocks the request for 2–5 minutes. Fine for scripts, not for web APIs.

### Option B — asynchronous (recommended for FastAPI)

```python
import asyncio
from llm4ad.builder import build_from_config

async def build_task_async(config_path: str, user_id: str, task_id: str):
    try:
        task_dir = await build_from_config(config_path)
        await db.update_task_status(user_id, task_id, "completed", task_dir=task_dir)
    except Exception as e:
        await db.update_task_status(user_id, task_id, "failed", error=str(e))

@app.post("/api/build")
async def create_build(req: BuildRequest, background_tasks: BackgroundTasks):
    task_id = generate_task_id()
    config_path = create_config(req, task_id)
    background_tasks.add_task(build_task_async, config_path, req.user_id, task_id)
    return {"task_id": task_id, "status": "building"}
```

### Option C — Celery / RQ (production)

```python
from celery import Celery
from llm4ad.builder import build_from_config_sync

celery = Celery("llm4ad_builder")

@celery.task
def build_task_celery(config_path: str, user_id: str, task_id: str):
    try:
        task_dir = build_from_config_sync(config_path)
        db.update_task_status(user_id, task_id, "completed", task_dir=task_dir)
    except Exception as e:
        db.update_task_status(user_id, task_id, "failed", error=str(e))
```

The bundled FastAPI Web UI uses option B internally (`src/backend/app/api/llm4ad/auto_research.py`).

## 4. Poll status

```python
@app.get("/api/build/{task_id}/status")
async def get_build_status(task_id: str, user_id: str):
    task = await db.get_task(user_id, task_id)
    if not task:
        return {"status": "not_found"}
    return {
        "status": task.status,
        "task_dir": task.task_dir if task.status == "completed" else None,
        "error": task.error if task.status == "failed" else None,
        "progress": task.progress,
    }
```

Frontend (TypeScript / fetch-style):

```ts
async function pollBuildStatus(taskId: string) {
  const start = Date.now()
  while (Date.now() - start < 5 * 60_000) {
    const res = await fetch(`/api/build/${taskId}/status`).then(r => r.json())
    if (res.status === "completed") return { ok: true, taskDir: res.task_dir }
    if (res.status === "failed")    return { ok: false, error: res.error }
    updateProgressBar(res.progress)
    await new Promise(r => setTimeout(r, 5000))
  }
  return { ok: false, error: "Build timeout" }
}
```

Real-time updates: replace polling with WebSockets and stream the same payload from a Redis pub/sub channel populated by the build task.

## 5. List and serve generated files

```python
@app.get("/api/build/{task_id}/files")
async def list_files(task_id: str, user_id: str):
    task = await db.get_task(user_id, task_id)
    if not task or task.status != "completed":
        return {"error": "Task not completed"}
    root = Path(task.task_dir)
    return {
        "files": [
            {"path": str(p.relative_to(root)), "size": p.stat().st_size}
            for p in root.rglob("*") if p.is_file()
        ]
    }

@app.get("/api/build/{task_id}/files/{file_path:path}")
async def download_file(task_id: str, file_path: str, user_id: str):
    task = await db.get_task(user_id, task_id)
    if not task or task.status != "completed":
        return {"error": "Task not completed"}
    full = Path(task.task_dir) / file_path
    if not full.exists() or not full.resolve().is_relative_to(Path(task.task_dir).resolve()):
        return {"error": "File not found"}
    return FileResponse(full)
```

Always validate `file_path` to prevent directory traversal — the `is_relative_to` check above is the minimum.

## 6. Run the generated pipeline

After the user reviews the generated task, expose a "Run" button:

```python
from llm4ad import LLM4AD

@app.post("/api/build/{task_id}/run")
async def run_pipeline(task_id: str, user_id: str):
    task = await db.get_task(user_id, task_id)
    if not task or task.status != "completed":
        return {"error": "Task not completed"}

    config_path = Path(task.task_dir) / "config.yaml"
    llm4ad = LLM4AD(str(config_path))
    run_id = generate_run_id()
    asyncio.create_task(run_evolution(llm4ad, user_id, task_id, run_id))
    return {"run_id": run_id, "status": "running"}

async def run_evolution(llm4ad, user_id, task_id, run_id):
    result = await llm4ad.run()
    await db.update_run(user_id, run_id, "completed", best_score=result.best_individual.score)
```

## Generated directory shape

```
{output_dir}/{project_name}/
├── config.yaml                    # pipeline configuration
├── {project_name}_evaluator.py    # custom evaluator
├── {algorithm_dir}/
│   └── {algorithm}.py             # algorithm template with EVOLVE markers
├── debug_run.py                   # quick local test script
├── test_evaluator.py              # evaluator validation
├── data/sample/
│   └── instance_001.json          # sample dataset
└── blueprint_meta.json            # build metadata
```

## Error handling

| Error | Cause | UX response |
|---|---|---|
| `BuildError: Validation failed after 3 attempts` | LLM produced invalid code repeatedly | Show details; offer manual edit or retry |
| `BuildError: No API key provided` | Missing/invalid API key | Prompt user to check credentials |
| `TimeoutError` | Build took too long | Increase timeout or simplify description |
| `JSONDecodeError` | Invalid build_config YAML | Validate before calling builder |

```python
from llm4ad.builder import BuildError

try:
    task_dir = await build_from_config(str(config_path))
except BuildError as e:
    return {
        "status": "failed",
        "error": "build_failed",
        "message": str(e),
        "details": getattr(e, "validation_errors", None),
    }
```

## Security checklist

- **API key storage**: encrypt at rest; never expose to JS.
- **Path validation**: scope every read/write to per-user directories like `/data/builds/{user_id}/{task_id}/`; reject path traversal.
- **Resource limits**: cap concurrent builds per user, set per-build timeouts, cap output directory size.
- **Input sanitization**: validate descriptions and uploaded files; rate-limit endpoints.

## Performance

- **Cache** identical descriptions (build outputs are deterministic enough to be reusable for prototype/demo flows).
- **Worker pools** (Celery / RQ) for concurrent builds; size workers per available cores.
- **WebSockets + Redis** for live progress instead of polling.

## Reference example

A minimal FastAPI integration:

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
import textwrap

from llm4ad.builder import build_from_config, BuildError

app = FastAPI()

class BuildRequest(BaseModel):
    description: str
    api_key: str
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    multimodal: bool = False

@app.post("/api/build")
async def create_build(req: BuildRequest, background_tasks: BackgroundTasks):
    user_id = "u-demo"
    task_id = "t-001"

    config_path = Path(f"/tmp/builds/{user_id}/{task_id}/build_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(f"""
builder:
  type: "openai_compatible"
  base_url: "{req.base_url}"
  api_key: "{req.api_key}"
  model: "{req.model}"
  max_repair_attempts: 3

task:
  description: |
{textwrap.indent(req.description, '    ')}
  output_dir: "/data/builds/{user_id}/{task_id}"
  project_name: "task_{task_id}"
  multimodal: {str(req.multimodal).lower()}
""")

    background_tasks.add_task(_run_build, str(config_path), user_id, task_id)
    return {"task_id": task_id, "status": "building"}

async def _run_build(config_path: str, user_id: str, task_id: str):
    try:
        task_dir = await build_from_config(config_path)
        # persist to your DB...
    except BuildError as e:
        # mark failed in your DB...
        ...
```

The bundled Web UI in `src/backend/app/api/llm4ad/` is a more complete reference — read it for the full project / task / report data model.

## See also

- [Auto Builder](../guides/auto-builder.md) — what `llm4ad chat` (formerly `build`) does end-to-end
- [Web UI Overview](overview.md) — the bundled deployment that uses these patterns
- `src/backend/app/api/llm4ad/auto_research.py` — production reference implementation
