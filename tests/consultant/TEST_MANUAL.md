# LLM4AD Chat 合并命令测试手册

## 前置条件

1. 确保 `~/.llm4ad/settings.yaml` 已配置 provider：

```yaml
providers:
  - name: default
    type: openai_compatible
    api_key: <your-api-key>
    base_url: https://ark.cn-beijing.volces.com/api/v3
    model: deepseek-v3-2-251201
  - name: dashscope
    type: anthropic
    auth_token: <your-auth-token>
    base_url: https://coding.dashscope.aliyuncs.com/apps/anthropic
    model: MiniMax-M2.5
```

2. 安装依赖：`uv sync`
3. 确认 CLI 可用：`llm4ad --help`（应看到 `chat` 命令，不应看到 `build` 命令）

---

## 测试 1：验证 CLI 入口

### 1.1 确认 build 命令已移除

```bash
llm4ad build --help
```

**预期结果**：报错 "No such command 'build'"

### 1.2 确认 chat 命令帮助信息

```bash
llm4ad chat --help
```

**预期结果**：显示以下选项：
- `-p / --provider`
- `-r / --resume`
- `-o / --output`
- `-l / --list-sessions`
- `--max-repair`
- `--prompt`
- `--non-interactive`
- `--code-path`
- `--data-path`

### 1.3 确认 list-sessions 可用

```bash
llm4ad chat --list-sessions
```

**预期结果**：显示 "No saved sessions found." 或已有会话列表

---

## 测试 2：完整三阶段流程（Happy Path）

### 启动命令

```bash
llm4ad chat -p default -o ./test_output
```

### Phase 1：需求收集

对话中依次输入以下内容（每次等待 LLM 回复后再输入下一条）：

**第 1 轮输入：**
```
我想用进化算法自动设计一个排序算法。给定一个整数列表，生成的算法需要返回排序后的列表。评价标准是正确性（排序结果是否正确）和效率（比较次数越少越好）。
```

**第 2 轮输入（如果 LLM 追问数据集）：**
```
不需要外部数据集，评估时随机生成长度为 10-100 的整数列表即可。
```

**第 3 轮输入（如果 LLM 追问更多细节）：**
```
没有现成代码，从零开始生成就好。项目名叫 sorting_evolution。
```

**预期行为**：
- LLM 会引导收集问题描述、数据、评价标准等信息
- 当信息足够时自动进入 Phase 2（显示 "Phase 2: Building" 面板）

### Phase 2：自动构建

**预期行为**：
- 显示 spinner/进度条
- 依次经过 "Analyzing problem..." → "Generating artifacts..." → "Validating code..." → "Build complete."
- 无需用户交互

### Phase 3：审查与迭代

**预期行为**：
- 显示生成的评估函数代码（语法高亮）
- 显示配置摘要（项目名、函数名、指标）
- LLM 解释评估逻辑
- 提供 4 个选项：确认 / 修改评估函数 / 修改配置 / 重新生成

**输入（确认）：**
```
1
```

**预期结果**：
- 显示 "Build complete!" 面板
- 显示输出目录路径和生成的文件列表
- 询问是否立即运行 pipeline

**输入（不运行）：**
```
n
```

**预期结果**：
- 显示 `llm4ad run ./test_output/sorting_evolution/config.yaml` 命令提示
- 显示 `python ./test_output/sorting_evolution/debug_run.py` 命令提示

### 验证输出文件

```bash
ls ./test_output/sorting_evolution/
```

**预期文件**：
- `evaluator_sorting_evolution.py`（或类似命名）
- `algs/` 目录含算法模板
- `config.yaml`
- `debug_run.py`

```bash
python ./test_output/sorting_evolution/debug_run.py
```

**预期结果**：debug_run 能正常执行（可能需要 provider 配置）

---

## 测试 3：Phase 3 修改评估函数

### 启动命令

```bash
llm4ad chat -p default -o ./test_modify
```

### Phase 1 输入

```
我要设计一个图着色算法。给定一个无向图（邻接矩阵表示），算法需要返回每个节点的颜色编号。评价标准是使用的颜色数越少越好，同时相邻节点不能同色（违反约束要扣分）。不需要外部数据，随机生成 20 节点的图即可。
```

### Phase 2

等待自动构建完成。

### Phase 3 — 修改评估函数

当显示评估函数和选项后，输入：

```
2
```

然后描述修改意图：

```
请在评估函数中增加一个额外的惩罚项：如果使用的颜色数超过节点数的一半，额外扣 100 分。
```

**预期行为**：
- 显示 "Applying modifications to evaluator..."
- 显示 "Re-validating modified evaluator..." spinner
- 重新展示修改后的评估函数代码
- 再次提供 4 个选项

**输入（确认修改后的版本）：**
```
1
```

**预期结果**：正常保存文件

---

## 测试 4：构建失败与重试

### 启动命令

```bash
llm4ad chat -p default -o ./test_retry
```

### Phase 1 — 提供模糊描述

```
帮我设计一个算法。
```

**预期行为**：
- LLM 应追问更多细节（问题太模糊）
- 如果 LLM 仍然尝试构建并失败，应显示 "Build failed" 并询问是否重试

**如果构建失败后输入：**
```
y
```

然后补充信息：

```
具体来说，我要设计一个背包问题的贪心算法。有 N 个物品，每个有重量和价值，背包容量为 W，目标是最大化总价值。评价标准是算法找到的解的总价值与最优解的比值。测试数据随机生成 20 个物品，容量为总重量的一半。
```

**预期行为**：重新进入 Phase 2 构建，这次应该成功

---

## 测试 5：Session 保存与恢复

### 5.1 启动并中断

```bash
llm4ad chat -p default -o ./test_resume
```

Phase 1 输入：

```
我想设计一个 TSP 旅行商问题的启发式算法。给定城市坐标，返回访问顺序。评价标准是总路径长度越短越好。
```

等待 LLM 回复后，按 **Ctrl+C**。

**预期结果**：
- 显示 "Interrupted. Saving session..."
- 显示 "Session saved. Resume with: llm4ad chat --resume <session_id>"
- 记录下 session_id

### 5.2 查看已保存会话

```bash
llm4ad chat --list-sessions
```

**预期结果**：表格中显示刚才保存的 session，Phase 列显示 "needs_gathering"

### 5.3 恢复会话

```bash
llm4ad chat --resume <session_id> -p default
```

**预期结果**：
- 显示 "Resumed session: <session_id>"
- 继续 Phase 1 对话（不需要重新描述问题）

继续输入：

```
不需要外部数据，随机生成 10 个城市的坐标。项目名叫 tsp_heuristic。
```

**预期行为**：正常继续流程进入 Phase 2

---

## 测试 6：使用不同 Provider

```bash
llm4ad chat -p dashscope -o ./test_dashscope
```

**预期行为**：使用 dashscope provider（MiniMax-M2.5 模型）正常运行三阶段流程

输入：

```
设计一个函数逼近算法，用简单的数学表达式拟合给定数据点。评价标准是均方误差越小越好，同时表达式长度越短越好（复杂度惩罚）。随机生成 sin(x) + noise 的 50 个数据点作为测试数据。
```

---

## 测试 7：Phase 3 重新生成

启动 chat 并完成 Phase 1 和 Phase 2 后，在 Phase 3 选择重新生成：

```
4
```

**预期行为**：
- 显示 "Regenerating from scratch..."
- 重新执行 Phase 2 构建流程
- 展示新生成的评估函数（应与之前不同）

---

## 测试 8：--max-repair 参数

```bash
llm4ad chat -p default -o ./test_repair --max-repair 1
```

**预期行为**：如果验证失败，最多只尝试 1 次自动修复（而非默认的 3 次）

---

## 测试 9：输出目录已存在

```bash
mkdir -p ./test_existing
llm4ad chat -p default -o ./test_existing
```

完成三阶段后：

**预期结果**：文件正常写入 `./test_existing/<project_name>/` 子目录，不报错

---

## 测试 10：非交互模式（--prompt + --non-interactive）

### 10.1 完全非交互 — Happy Path

```bash
llm4ad chat \
  --prompt "设计一个排序算法。给定一个整数列表，返回排序后的列表。评价标准是正确性（与标准排序结果一致）和效率（比较次数越少越好）。不需要外部数据集，评估时随机生成长度 10-100 的整数列表。项目名 sorting_noninteractive。" \
  --non-interactive \
  -p default \
  -o ./test_ni
```

**预期行为**：
- 显示 "Using provided prompt, skipping needs gathering."
- 直接进入 Phase 2 构建（spinner 进度）
- 构建完成后直接写文件（跳过 Phase 3 审查）
- 显示 "Build complete!" 面板和输出文件列表
- 显示运行命令提示后退出（不询问是否运行）

**验证输出**：

```bash
ls ./test_ni/sorting_noninteractive/
cat ./test_ni/sorting_noninteractive/config.yaml
```

**预期文件**：evaluator、algorithm 目录、config.yaml、debug_run.py

### 10.2 带 --code-path 的非交互模式

先准备一个示例代码文件：

```bash
mkdir -p /tmp/test_code
cat > /tmp/test_code/my_sort.py << 'EOF'
def sort_algorithm(arr: list[int]) -> list[int]:
    """Sort an integer list using a custom algorithm."""
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
EOF
```

```bash
llm4ad chat \
  --prompt "基于已有的排序代码，设计一个更高效的排序算法。评价标准是在随机数组上的比较次数和交换次数。" \
  --code-path /tmp/test_code/my_sort.py \
  --non-interactive \
  -p default \
  -o ./test_ni_code
```

**预期行为**：
- 构建过程中 TaskAnalyzer 会读取 `/tmp/test_code/my_sort.py` 作为上下文
- 生成的评估函数应与排序相关
- 正常完成并写入文件

### 10.3 带 --data-path 的非交互模式

先准备测试数据：

```bash
mkdir -p /tmp/test_data
cat > /tmp/test_data/train.csv << 'EOF'
x,y
0.0,0.0
1.0,0.84
2.0,0.91
3.0,0.14
4.0,-0.76
5.0,-0.96
EOF
```

```bash
llm4ad chat \
  --prompt "设计一个符号回归算法，用数学表达式拟合给定的 CSV 数据。评价标准是均方误差越小越好，表达式节点数越少越好。" \
  --data-path /tmp/test_data \
  --non-interactive \
  -p default \
  -o ./test_ni_data
```

**预期行为**：正常构建，TaskAnalyzer 使用 data_path 作为上下文

---

## 测试 11：仅 --prompt（Phase 3 仍交互）

```bash
llm4ad chat \
  --prompt "设计一个背包问题的贪心算法。有 N 个物品各有重量和价值，背包容量为 W，目标是最大化总价值。评价标准是算法解与最优解的比值。随机生成 20 个物品，容量为总重量一半。项目名 knapsack_greedy。" \
  -p default \
  -o ./test_prompt_only
```

**预期行为**：
- 跳过 Phase 1（显示 "Using provided prompt, skipping needs gathering."）
- 正常执行 Phase 2 构建
- 进入 Phase 3 交互式审查（显示评估函数、提供 4 个选项）
- 用户可以修改或确认

**输入（确认）：**
```
1
```

**预期结果**：正常保存文件

---

## 测试 12：非交互模式错误处理

### 12.1 缺少 --prompt

```bash
llm4ad chat --non-interactive -p default
```

**预期结果**：
- 报错 "Error: --non-interactive requires --prompt"
- 退出码 1

### 12.2 空 prompt（空白字符）

```bash
llm4ad chat --prompt "   " --non-interactive -p default
```

**预期结果**：
- 报错 "Error: --prompt cannot be empty"
- 退出码 1

### 12.3 不存在的 --code-path

```bash
llm4ad chat --prompt "test" --code-path /nonexistent/path.py --non-interactive -p default
```

**预期结果**：
- 报错 "Error: code path not found: /nonexistent/path.py"
- 退出码 1

### 12.4 不存在的 --data-path

```bash
llm4ad chat --prompt "test" --data-path /nonexistent/data/ --non-interactive -p default
```

**预期结果**：
- 报错 "Error: data path not found: /nonexistent/data/"
- 退出码 1

### 12.5 非交互模式下构建失败

```bash
llm4ad chat \
  --prompt "x" \
  --non-interactive \
  --max-repair 1 \
  -p default \
  -o ./test_ni_fail
```

**预期行为**：
- 极简 prompt 可能导致构建失败
- 非交互模式下不会询问重试，直接报错退出
- 显示 "Build failed: ..." 错误信息
- 退出码非 0

---

## 测试 13：选择器自定义输入选项

### 启动命令

```bash
llm4ad chat -p default -o ./test_custom_input
```

### 验证场景

在 Phase 1 对话中，当 LLM 给出选项列表时：

**预期行为**：
- 每个选项列表末尾始终显示"其他 — 自行输入 / Other — enter your own"选项
- 即使 LLM 的原始选项中没有包含自定义输入项，也会自动追加
- 如果 LLM 已经提供了自定义输入选项（如"手动输入"、"其他"），则不会重复追加

**操作步骤**：

1. 输入问题描述，等待 LLM 回复并展示选项
2. 使用方向键移动到最后的"其他"选项，按回车
3. 此时应出现文本输入框 `You >` 
4. 输入自定义内容，如：`我要做一个多目标优化问题`

**预期结果**：LLM 正常接收自定义输入并继续对话

---

## 测试 14：编程语言确认

### 14.1 从头生成 — 应询问语言

```bash
llm4ad chat -p default -o ./test_lang
```

**第 1 轮输入**：
```
我想设计一个排序算法，没有现成代码，从头生成。
```

**预期行为**：
- LLM 应在后续对话中询问编程语言偏好
- 例如："您希望用什么编程语言？1) Python  2) C++  3) 其他"

**输入**：
```
Python
```

**预期行为**：继续收集其他信息，最终提取的 NeedsProfile 中 `language` 字段为 `"python"`

### 14.2 有已有代码 — 不需要询问语言

```bash
llm4ad chat -p default -o ./test_lang2
```

**第 1 轮输入**：
```
我有一份现成的排序算法代码在 /tmp/test_code/my_sort.py，希望在此基础上优化。
```

**预期行为**：
- LLM 会读取文件了解上下文
- 不需要额外询问编程语言（可从代码文件推断）

---

## 清理

```bash
rm -rf ./test_output ./test_modify ./test_retry ./test_resume ./test_dashscope ./test_existing ./test_repair
rm -rf ./test_ni ./test_ni_code ./test_ni_data ./test_prompt_only ./test_ni_fail
rm -rf /tmp/test_code /tmp/test_data
```

---

## 常见问题排查

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| "No provider found" | settings.yaml 未配置或 -p 名称错误 | 检查 `~/.llm4ad/settings.yaml` |
| Phase 2 一直 spinner | API 响应慢或超时 | 检查网络，确认 API key 有效 |
| Build failed 循环 | 问题描述太模糊 | 提供更具体的描述、数据格式、评价标准 |
| Ctrl+C 后无法恢复 | session 文件损坏 | 删除 `~/.llm4ad/sessions/<id>.json` 重新开始 |
| 评估函数语法错误 | validator 修复失败 | 增大 --max-repair 或在 Phase 3 手动描述修改 |
| "--non-interactive requires --prompt" | 缺少 --prompt 参数 | 添加 --prompt 参数提供问题描述 |
| "code path not found" | --code-path 路径不存在 | 检查路径拼写，确认文件存在 |
| 非交互模式构建失败 | prompt 信息不足 | 提供更详细的 prompt，或去掉 --non-interactive 使用交互模式 |
