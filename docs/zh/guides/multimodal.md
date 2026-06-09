# 多模态进化 (MLES) 指南

本指南介绍 LLM4AD 的**多模态 LLM 进化策略 (Multimodal LLM-based Evolution Strategy, MLES)** 功能，包括：

- 功能定位与核心思想
- 快速启用
- 架构与数据流
- 配置参考
- 前端集成模式
- 如何添加新的多模态任务
- 已有任务参考

## 1. 功能定位

传统的 LLM 算法进化（如 EoH、MEoH）是纯文本的：LLM 仅通过数值分数和文本描述来理解算法表现，无法直观感知算法的行为模式（轨迹震荡、路径交叉等）。

MLES 的核心思想是：在进化过程中，让 LLM **同时看到算法行为的可视化图像**（轨迹图、路线图等），从而做出视觉驱动的改进。

**关键设计原则：**

- **完全 opt-in**：通过 `multimodal.enabled: true` 启用，默认关闭，不影响已有的纯文本流程
- **存储模式可选**：`behavior_storage` 控制磁盘占用与显示速度的权衡
- **前端透明**：无论使用哪种存储模式，前端总能获取到图像

## 2. 快速启用

在已有的纯文本 YAML 配置基础上，只需两处改动：

### 2.1 添加 `multimodal` 配置块

```yaml
multimodal:
  enabled: true
  behavior_storage: "raw"       # "rendered" | "raw" | "none"
```

### 2.2 将 sampler 替换为多模态版本

```yaml
planner:
  type: "llm_evolution"
  samplers:
    - name: "init_sampler"                    # 初始化不变
    - name: "multimodal_mutation_sampler"      # 替换 mutation_sampler
    - name: "multimodal_crossover_sampler"     # 替换 crossover_sampler
```

### 2.3 确保 LLM Provider 支持视觉

多模态 sampler 会在 prompt 中嵌入图像，因此 planner provider 必须支持 vision 输入（如 `gpt-4o`、`gpt-4o-mini`、`claude-sonnet`）。

## 3. 架构

### 3.1 数据流

```
Evaluator (subprocess)
    │
    ├─ score, metrics              (与纯文本相同)
    └─ BehaviorData                (多模态新增)
         ├─ observation: str       (文本观察摘要)
         └─ visualizations[]
              ├─ data_base64       (预渲染 PNG, 或 None)
              ├─ raw_data          (紧凑数据, 用于延迟渲染)
              └─ renderer          (渲染器注册名)
                    │
                    ▼
              Dispatcher (跨实例聚合)
                    │
                    ▼
              Orchestrator (绑定到 Algorithm 对象)
                    │
                    ▼
              Multimodal Sampler
                    │
                    ├─ render_visualization(viz)   → base64 PNG
                    ├─ compress_image_base64(...)   → 适配 LLM token 预算
                    └─ 嵌入为 ContentPart 到 ChatMessage
                          │
                          ▼
                      LLM (看到图像 + 文本 → 提出改进)
```

### 3.2 三种存储模式

`behavior_storage` 控制**进化过程中保存到磁盘的内容**，是存储/性能的权衡，不是可见性开关。

| 模式 | 评估器保存内容 | 单实例磁盘占用 | 特点 |
|------|--------------|--------------|------|
| `"rendered"` | 预渲染 base64 PNG | ~40-100 KB | 即时显示；文件较大 |
| `"raw"` | 紧凑数据字典 + 渲染器名称 | ~1-5 KB | 文件小；按需渲染 |
| `"none"` | 无 | 0 | 最小磁盘占用；需重跑评估器获取图像 |

### 3.3 透明降级链（前端获取图像）

无论进化时使用哪种模式，前端**始终**能获取图像。`render_visualization()` 实现三级降级：

```
1. viz.data_base64 存在?     → 直接返回           (rendered 模式: 即时)
2. viz.raw_data + renderer?  → 按需渲染并缓存      (raw 模式: 一次性开销)
3. 什么都没有?               → 重跑评估器          (none 模式: 较慢)
```

### 3.4 磁盘文件结构

```
runs/{project_name}/{run_id}/
├── generated/                               # 所有算法产物
│   ├── island_0_gen_0_abc123.json           # 算法元数据
│   ├── island_0_gen_0_abc123.md             # 人类可读摘要
│   ├── island_0_gen_0_abc123_viz_0_0.png    # 行为图像 (rendered 模式)
│   ├── island_0_gen_0_abc123_raw_0_0.json   # 原始数据 (raw 模式)
│   └── ...
├── output/                                  # 进化状态导出
├── worktrees/                               # 算法代码快照
│   └── island_0_gen_0_ind_abc123/
│       └── solve.py                         # 实际算法代码
└── logs/
```

## 4. 配置参考

### MultimodalConfig

```yaml
multimodal:
  enabled: false                    # 主开关 (默认: false)
  behavior_storage: "rendered"      # 存储模式: "rendered" | "raw" | "none"
  max_images_per_prompt: 3          # 每次 LLM 调用最大图像数
  image_max_size_kb: 512            # 超过此大小自动压缩
  include_observation_text: true    # 是否在图像旁附加文本观察
```

### PlannerConfig

```yaml
planner:
  type: "llm_evolution"
  mask_evolve_blocks: false         # 是否遮盖 EVOLVE 块 (默认: false)
                                    # false: coder 可以看到现有代码并迭代改进
                                    # true: coder 只能看到占位符，强制全新生成
  samplers:
    - name: "init_sampler"
    - name: "multimodal_mutation_sampler"
    - name: "multimodal_crossover_sampler"
  selection_strategy: "weighted"
```

### Algorithm JSON Schema (关键字段)

```jsonc
{
  "id": "abc123def456",
  "name": "Algorithm Name",
  "description": "...",
  "generation": 3,
  "island_id": 0,
  "parent_ids": ["parent_id_1"],
  "evaluation": {
    "score": -283.45,
    "metrics": { "tour_length": 283.45, "valid_tour": 1.0 }
  },
  "generation_meta": {
    "operator": "multimodal_mutation_sampler",
    "llm_model": "gpt-4o-mini"
  },
  "behavior_data": [
    {
      "observation": "instance_001 | N=10 | Length=283.45",
      "instance_id": "data/small/instance_001.json",
      "visualizations": [
        {
          "label": "TSP Tour",
          "media_type": "image/png",
          "data_base64": null,        // rendered 模式: 从伴随 PNG 文件加载
          "raw_data": { "nodes": [...], "tour": [...] },  // raw 模式
          "renderer": "tsp_tour"      // 延迟渲染器名称
        }
      ]
    }
  ]
}
```

## 5. 前端集成

### 5.1 VisualizationAPI（推荐）

`VisualizationAPI` 是前端获取算法行为数据的标准接口：

```python
from llm4ad.frontend.visualization import VisualizationAPI

api = VisualizationAPI(
    generated_dir=Path("runs/my_project/run_001/generated"),
    evaluator_script=Path("my_evaluator.py"),   # none 模式重跑需要
    dataset_dir=Path("data/"),                  # none 模式重跑需要
    project_root=Path("my_algorithm/"),          # none 模式重跑需要
)

# 列出所有算法
algorithms = api.list_algorithms()

# 获取详情
detail = api.get_algorithm_detail(alg_id)

# 获取行为数据（含存储模式信息）
behavior = api.get_algorithm_behavior(alg_id)

# 获取图像（rendered/raw 透明处理）
image_b64 = api.get_algorithm_image(alg_id, viz_index=0)

# none 模式: 重跑评估器
behavior_list = api.rerun_and_visualize(alg_id)
```

### 5.2 两步降级模式（前端参考模式）

这是前端获取图像的标准模式，`view_algorithm.py` 中有完整实现：

```python
# Step 1: 检测存储模式
def _detect_storage_mode(api, alg_id):
    behavior = api.get_algorithm_behavior(alg_id)
    if not behavior.get("has_behavior"):
        return "none"
    for v in behavior.get("visualizations", []):
        if v["has_rendered_image"]:
            return "rendered"
        if v["has_raw_data"]:
            return "raw"
    return "none"

# Step 2: 按模式获取图像
mode = _detect_storage_mode(api, alg_id)
if mode in ("rendered", "raw"):
    # get_algorithm_image() 透明处理 rendered 和 raw
    image_b64 = api.get_algorithm_image(alg_id, viz_index=0)
else:
    # none 模式: 重跑评估器
    behavior_list = api.rerun_and_visualize(alg_id)
```

### 5.3 Web 前端 HTML 渲染

图像以 base64 返回，前端直接嵌入 `<img>` 标签：

```html
<img src="data:image/png;base64,{image_b64}" alt="Algorithm Behavior" />
```

### 5.4 参考实现

每个多模态示例目录下的 `view_algorithm.py` 是完整的参考实现，支持：

- 交互式 run 选择 / `--latest` 跳过
- 交互式算法选择 / `--best` / `<algorithm_id>` 参数
- 自动检测存储模式并显示
- 两步降级获取图像
- matplotlib 显示

## 6. 添加新的多模态任务

### 前置条件

- 已有可工作的纯文本评估器（使用子进程隔离）
- 有明确的可视化思路：什么图像能帮助 LLM 理解算法行为？

### Step 1: 定义原始行为数据

确定算法执行产生的紧凑数据，后续可渲染为图像：

```python
# TSP: 返回路线
raw_behavior = {
    "nodes": [[x1, y1], [x2, y2], ...],
    "tour": [0, 3, 1, 2, ...],
    "tour_length": 342.15,
}

# LunarLander: 返回轨迹画布
raw_behavior = {
    "canvas": canvas.tolist(),
    "reward": 150.9,
    "final_state": "Landed safely",
}
```

### Step 2: 修改 `_run_episode` 返回原始数据

```python
def _run_episode(self, ..., capture_behavior=True) -> dict:
    result = {"score": score, "metrics": {...}}
    if capture_behavior:
        result["raw_behavior"] = { ... }  # 任务特定的紧凑数据
    return result
```

### Step 3: 编写渲染函数

将原始数据转换为 base64 PNG 的独立函数：

```python
def _render_result_image(raw_data: dict) -> str:
    fig, ax = plt.subplots(...)
    # ... 绘制可视化 ...
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
```

### Step 4: 注册延迟渲染器

启用 `"raw"` 存储模式的关键。放在评估器文件中：

```python
from llm4ad.evaluator.renderer import BaseRenderer

@BaseRenderer.register("my_task_renderer")
class MyTaskRenderer(BaseRenderer):
    def render(self, raw_data: dict, **kwargs) -> str:
        return _render_result_image(raw_data)
```

### Step 5: 在 `evaluate()` 中构建 BehaviorData

```python
from llm4ad.evaluator.behavior import BehaviorData, BehaviorVisualization

behavior = None
if cfg.behavior_storage != "none":
    if cfg.behavior_storage == "rendered":
        viz = BehaviorVisualization(
            label="My Visualization",
            data_base64=_render_result_image(result["raw_behavior"]),
        )
    elif cfg.behavior_storage == "raw":
        viz = BehaviorVisualization(
            label="My Visualization",
            raw_data=result["raw_behavior"],
            renderer="my_task_renderer",
        )
    behavior = BehaviorData(
        observation=_build_observation_text(result),
        visualizations=[viz],
        instance_id=str(data_path),
    )
return EvaluationResult(score=score, behavior=behavior, ...)
```

### Step 6: 更新子进程入口

```python
def _subprocess_main():
    input_data = json.loads(sys.argv[1])
    behavior_storage = input_data.get("behavior_storage", "rendered")
    capture = behavior_storage != "none"
    result = evaluator._run_episode(..., capture_behavior=capture)

    # 优化: rendered 模式在子进程内渲染，避免传输大量原始数据
    if behavior_storage == "rendered" and result.get("raw_behavior"):
        result["image_base64"] = _render_result_image(result["raw_behavior"])
        del result["raw_behavior"]

    print(json.dumps(result))
```

### Step 7: 编写观察文本构建器

LLM 在图像旁读取的单行摘要：

```python
def _build_observation_text(result: dict) -> str:
    return f"Instance={result['instance']} | Score={result['score']:.4f}"
```

### Step 8: 创建 YAML 配置

```yaml
multimodal:
  enabled: true
  behavior_storage: "raw"

planner:
  samplers:
    - name: "init_sampler"
    - name: "multimodal_mutation_sampler"
    - name: "multimodal_crossover_sampler"
```

### Step 9: 测试

```bash
python test_evaluator.py       # 验证评估器 + 行为数据
python debug_run.py            # 完整进化流程
python view_algorithm.py       # 查看行为可视化
```

## 7. 已有任务参考

| 任务 | 目录 | 渲染器名 | 原始数据 | 观察文本格式 |
|------|------|---------|---------|------------|
| LunarLander | `lunarlander_python_multimodal/` | `lunarlander_trajectory` | `{canvas, reward, final_state, seed}` | `Seed=.. \| Reward=.. \| Fuel=..` |
| TSP | `tsp_benchmark_python_multimodal/` | `tsp_tour` | `{nodes, tour, tour_length, n_nodes}` | `inst \| N=.. \| Length=.. \| Time=..` |
| Template | `task_template_python_multimodal/` | `my_task_contour` | `{grid, trajectory, best_point, ...}` | `inst \| Best=.. \| Gap=.. \| Evals=..` |

每个目录包含：

```
my_task_multimodal/
  data/                          # 评估实例数据
  my_algorithm/                  # EVOLVE 标记的代码（version control 管理）
  my_evaluator.py                # 多模态评估器 (关键文件)
  my_task_benchmark.yaml         # 含 multimodal 的配置
  debug_run.py                   # 运行入口
  test_evaluator.py              # 评估器测试
  view_algorithm.py              # 行为可视化查看器
```

## 8. 注意事项

### 渲染器注册与懒加载

延迟渲染器通过 `@BaseRenderer.register("name")` 装饰器注册，只有在评估器模块被导入时才执行。

- **进化过程中**：框架通过 YAML 的 `module` 字段自动导入，无需额外操作
- **独立脚本中**（如 `view_algorithm.py`）：`VisualizationAPI` 在构造时通过 `evaluator_script` 参数自动导入渲染器模块
- 如果渲染器未找到，不会崩溃——`render_visualization()` 返回 `None`，降级链继续

### API Key 安全

不要在 YAML 配置中硬编码 API key，使用环境变量：

```yaml
providers:
  - name: "default"
    api_key: ${LLM_API_KEY}
```

### mask_evolve_blocks 配置

`planner.mask_evolve_blocks`（默认 `false`）控制 coder 是否能看到 EVOLVE 块中的现有代码：

- `false`（推荐）：coder 看到完整代码，可以迭代改进，分数更高
- `true`：EVOLVE 块内容被替换为占位符，强制从头生成

## 9. 文件清单

```
src/llm4ad/
  config/schema.py                          # MultimodalConfig, mask_evolve_blocks
  evaluator/
    behavior.py                             # BehaviorData, BehaviorVisualization
    renderer.py                             # BaseRenderer 注册表, render_visualization()
    dispatcher.py                           # BehaviorData 聚合
  infra/provider/
    base.py                                 # ContentPart (文本 + 图像)
    anthropic.py                            # 多模态消息序列化
    openai_compatible.py                    # 多模态消息序列化
  planner/
    base.py                                 # Algorithm.behavior_data, 序列化/反序列化
    llm_evolution.py                        # mask_evolve_blocks 配置
    sampler/
      prompt_templates.py                   # 多模态 prompt 构建器
      multimodal_mutation_sampler.py        # 图像感知的变异
      multimodal_crossover_sampler.py       # 图像感知的交叉
  utils/image_utils.py                      # LLM prompt 图像压缩
  frontend/visualization.py                 # VisualizationAPI

examples/applications/
  lunarlander_python_multimodal/            # LunarLander 参考实现
  tsp_benchmark_python_multimodal/          # TSP 参考实现
  task_template_python_multimodal/          # 新任务起始模板
```
