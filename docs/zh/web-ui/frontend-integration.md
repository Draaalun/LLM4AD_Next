# 前端集成

本指南讲如何把 LLM4AD 嵌入到多租户 web 平台 — 也就是从你自己的后端 / 前端调起自动构建器（`llm4ad chat`）和流水线运行器，而不是直接跑 CLI。读本页前最好先看[Web UI 概览](overview.md)；那篇讲内置 UI，本页面对**集成方**。

## 推荐工作流

```
用户输入（Web 表单）
  → 生成 config / build_config
  → 调用 LLM4AD API（同步、异步或队列化）
  → 轮询状态
  → 列出并提供生成文件
  → 触发进化运行（可选）
```

> 注：自 [#93](https://github.com/llm4ad/llm4ad/pull/93) 起，CLI 的 `llm4ad build` 与 `llm4ad build-init` 已合并入 `llm4ad chat`。Python builder API（`build_task_sync`、`build_from_config`、`build_from_config_sync`）保持稳定，是你后端集成实际调用的接口。CLI 短命令变了，底层 API 没变。

## 1. 收集用户输入

典型表单：

**必填**
- **问题描述**（多行文本）— 自然语言描述任务
- **LLM provider**（下拉）— OpenAI、Anthropic、OpenAI 兼容，或用户全局设置中的命名条目
- **API key**（密码输入）— 用户自己的 LLM key
- **模型**（下拉）— `gpt-4o-mini`、`claude-opus-4` 等

**可选**
- **项目名**（文本）— 留空则自动生成
- **输出目录**（隐藏字段）— 后端按用户划分
- **多模态**（复选框）— 启用支持可视化的评估器脚手架
- **基于现有代码**（文件上传）— 在现有代码上改造而非从零开始
- **数据集**（文件上传）— 自定义评估数据

## 2. 拼装配置

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

**安全**：API key 永远不要明文存盘。静态加密（Fernet、KMS 等），并优先让用户使用自己的 key（也由他们承担 LLM 费用）。

## 3. 调用 builder API

### 方案 A — 同步（简单、阻塞）

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

会把请求阻塞 2–5 分钟。脚本可以用，web API 不要。

### 方案 B — 异步（FastAPI 推荐）

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

### 方案 C — Celery / RQ（生产）

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

内置 Web UI 内部用方案 B（`src/backend/app/api/llm4ad/auto_research.py`）。

## 4. 轮询状态

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

前端（TypeScript / fetch）：

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

实时进度：把轮询换成 WebSocket，从 build 任务写入 Redis pub/sub，再推给前端即可。

## 5. 列出和提供生成文件

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

务必校验 `file_path`，防目录穿越 — 上面的 `is_relative_to` 是底线。

## 6. 跑生成的流水线

用户审阅过生成内容后，给一个"Run"按钮：

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

## 生成目录结构

```
{output_dir}/{project_name}/
├── config.yaml                    # 流水线配置
├── {project_name}_evaluator.py    # 自定义评估器
├── {algorithm_dir}/
│   └── {algorithm}.py             # 含 EVOLVE 标记的算法模板
├── debug_run.py                   # 快速本地测试脚本
├── test_evaluator.py              # 评估器校验
├── data/sample/
│   └── instance_001.json          # 示例数据集
└── blueprint_meta.json            # 构建元数据
```

## 错误处理

| 错误 | 原因 | UX 响应 |
|---|---|---|
| `BuildError: Validation failed after 3 attempts` | LLM 反复生成不合法代码 | 显示详情，提供"手动编辑"或"重试" |
| `BuildError: No API key provided` | API key 缺失或无效 | 提示用户检查凭据 |
| `TimeoutError` | 构建过久 | 调大超时或简化描述 |
| `JSONDecodeError` | build_config YAML 格式问题 | 调用 builder 之前先校验 YAML |

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

## 安全清单

- **API key 存储**：静态加密；不要露给 JS。
- **路径校验**：所有读写都限制在每用户目录，如 `/data/builds/{user_id}/{task_id}/`；拒绝目录穿越。
- **资源限额**：每用户并发构建数上限、每次构建超时、输出目录大小上限。
- **输入清洗**：校验描述与上传文件；接口加限流。

## 性能

- **缓存**相同描述（构建结果对 demo / 原型流足够稳定，可复用）。
- **Worker 池**（Celery / RQ）做并发构建；按可用核数设置 worker。
- **WebSocket + Redis** 替代轮询做实时进度。

## 参考样例

最小化 FastAPI 集成：

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
        # 写入你的 DB...
    except BuildError as e:
        # 在 DB 里标记失败...
        ...
```

更完整的参考实现是内置 Web UI 的 `src/backend/app/api/llm4ad/`，里面是完整的 project / task / report 数据模型。

## 相关链接

- [自动构建](../guides/auto-builder.md) — `llm4ad chat`（旧名 `build`）的端到端流程
- [Web UI 概览](overview.md) — 用了这些模式的内置部署
- `src/backend/app/api/llm4ad/auto_research.py` — 生产参考实现
