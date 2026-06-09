"""演化分析报告内置 Prompt 模板集合。

每个构建函数返回 ``(system_prompt, user_prompt)`` 二元组；当用户未提供
自定义模板时，Service 层调用这些函数来生成发送给 LLM 的输入。

注：Prompt 字面量保持英文，因其作为 LLM 指令直接使用，不在中文化范围内。
"""

import json

MAX_LOG_CHARS = 100_000


def _truncate(text: str, max_chars: int = MAX_LOG_CHARS) -> str:
    """将文本截断到 ``max_chars`` 长度，超出部分追加省略标记。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated due to length] ..."


def _serialize_nodes(nodes: list[dict]) -> str:
    return json.dumps(nodes, ensure_ascii=False, indent=2, default=str)


# ---- 1. Technical Change Report ----

_TECH_CHANGE_SYSTEM = """\
You are an expert algorithm evolution analyst. The user will provide \
evolution logs from an automated algorithm design system. Each log entry \
of type "generated" represents a candidate algorithm produced during \
evolution, including its generation number, scores, and code/design details.

Analyze the logs and produce a Markdown report with exactly the \
following four sections. Use concrete data from the logs — cite generation \
numbers, algorithm names/IDs, score values, and technique names whenever \
possible. Write in a professional yet readable tone suitable for a \
technical team report.

IMPORTANT: Output the Markdown content directly as plain text. \
Do NOT wrap it in ```markdown``` or any other code fences.

## 1. Technology Adoption & Usage Patterns
Identify recurring algorithmic techniques, data structures, or heuristics \
that appeared across generations. Note which were adopted widely, which \
were tried and discarded (and why, if inferable), and which represent \
the current dominant approach.

## 2. Instance Preference Analysis
Analyze how different strategies or algorithms perform across different \
problem instances or datasets. Identify which strategies are best suited \
for which types of instances and why.

## 3. Objective Preference Analysis
Analyze how different techniques affect different optimization objectives \
(e.g., accuracy, speed, energy consumption, solution quality). Identify \
trade-offs and specializations.

## 4. Future Evolution Direction & Prediction
Based on observed trends, predict the most promising directions for \
continued evolution. Suggest specific algorithmic modifications, \
combinations, or entirely new approaches that could yield further \
improvements. Justify your predictions with evidence from the logs.\
"""


# ---- 2. Node Comparison ----

_NODE_COMPARISON_SYSTEM = """\
You are an expert algorithm evolution analyst. The user will provide data \
for several specific algorithm nodes selected from an evolution tree. \
Each node contains its generation info, algorithm code/design, and \
performance scores across instances.

Produce a Markdown report comparing these nodes. Output the Markdown \
content directly as plain text — do NOT wrap it in ```markdown``` or \
any other code fences. Structure the report as follows:

## Overview
Briefly introduce the nodes being compared (IDs, generations, lineage if \
available).

## Structural & Design Comparison
Compare the algorithmic approaches, data structures, heuristics, and \
code patterns used by each node. Use a comparison table where helpful.

## Performance Comparison
Compare scores across instances/objectives. Identify which node excels \
where and why. Include a score comparison table if data is available.

## Key Insights
Summarize the most actionable insights: what design choices lead to \
better performance, and what trade-offs exist between the nodes.

Use concrete data — cite node IDs, scores, and technique names.\
"""


# ---- 3. Chain Analysis ----

_CHAIN_ANALYSIS_SYSTEM = """\
You are an expert algorithm evolution analyst. The user will provide an \
ordered sequence of algorithm nodes forming a parent-child chain on a \
single branch of the evolution tree. The first node is the ancestor and \
the last is the descendant.

Produce a Markdown report analyzing the evolution along this chain. \
Output the Markdown content directly as plain text — do NOT wrap it \
in ```markdown``` or any other code fences.

## Chain Overview
Summarize the chain length, generation span, and overall score trajectory.

## Step-by-Step Evolution Analysis
For each parent → child transition, describe:
- What changed (new technique, parameter tweak, structural modification)
- The performance impact (score delta, which instances improved/degraded)
- Why this change was likely beneficial or detrimental

## Technology Succession Timeline
Summarize the major algorithmic techniques that appeared and disappeared \
along the chain, presented as a timeline.

## Overall Trajectory Assessment
Characterize the evolution direction: was it converging, diverging, or \
plateauing? What was the dominant improvement strategy (exploitation vs. \
exploration)?

Use concrete data throughout.\
"""


# ---- 4. Optimal Algorithm Analysis ----

_CHAMPION_BIRTH_SYSTEM = """\
You are an expert algorithm evolution analyst writing a report suitable \
for team presentations or academic papers. The user will provide the \
complete lineage of the best-performing (optimal) algorithm node, \
traced from the initial generation to the final optimal algorithm.

Produce a Markdown report with the following structure. Output the \
Markdown content directly as plain text — do NOT wrap it in \
```markdown``` or any other code fences.

## Optimal Algorithm Summary
State the optimal algorithm's node ID, its generation, and its headline \
performance metrics.

## Lineage Overview
Briefly describe the full ancestry path (number of ancestors, generation \
span, overall score progression).

## Aha Moments (Key Breakthroughs)
Identify **3 to 5 critical mutation points** where a significant \
breakthrough occurred. For each Aha Moment:
- **Generation & Node ID**: When and where it happened
- **The Innovation**: What new technique, structure, or parameter was \
introduced
- **Impact**: Quantitative improvement (score delta, ranking change)
- **Why It Worked**: Technical explanation of why this innovation was \
effective

## Evolution Narrative
Tell the story of how the optimal algorithm emerged — a coherent narrative \
connecting the Aha Moments, suitable for a 2-minute verbal summary to \
colleagues.

## Lessons Learned
What general principles about algorithm design can be extracted from \
this optimal algorithm's evolution journey?

Write in a professional, engaging tone. Use concrete data throughout.\
"""


# ---- User Prompt Templates (with {variable} placeholders) ----

_TECH_CHANGE_USER_TEMPLATE = """\
## Task Background
{background}

## Evolution Logs
{logs_summary}

Please analyze the above evolution logs and produce the report.\
"""

_NODE_COMPARISON_USER_TEMPLATE = """\
## Task Background
{background}

## Selected Nodes Data
{nodes_data}

Please compare these algorithm nodes and produce the report.\
"""

_CHAIN_ANALYSIS_USER_TEMPLATE = """\
## Task Background
{background}

## Chain Nodes (ancestor → descendant)
{chain_data}

Please analyze this evolution chain and produce the report.\
"""

_CHAMPION_BIRTH_USER_TEMPLATE = """\
## Task Background
{background}

## Optimal Algorithm Lineage (initial generation → optimal algorithm)
{lineage_data}

Please trace the optimal algorithm's emergence and produce the report.\
"""

REPORT_TEMPLATES: dict[str, dict] = {
    "tech_change": {
        "user_prompt_template": _TECH_CHANGE_USER_TEMPLATE,
        "variables": ["background", "logs_summary"],
    },
    "node_comparison": {
        "user_prompt_template": _NODE_COMPARISON_USER_TEMPLATE,
        "variables": ["background", "nodes_data"],
    },
    "chain_analysis": {
        "user_prompt_template": _CHAIN_ANALYSIS_USER_TEMPLATE,
        "variables": ["background", "chain_data"],
    },
    "champion_birth": {
        "user_prompt_template": _CHAMPION_BIRTH_USER_TEMPLATE,
        "variables": ["background", "lineage_data"],
    },
}

_SYSTEM_PROMPTS: dict[str, str] = {
    "tech_change": _TECH_CHANGE_SYSTEM,
    "node_comparison": _NODE_COMPARISON_SYSTEM,
    "chain_analysis": _CHAIN_ANALYSIS_SYSTEM,
    "champion_birth": _CHAMPION_BIRTH_SYSTEM,
}


def build_prompts(
    report_type: str,
    log_data: list[dict] | str,
    background: str,
) -> tuple[str, str]:
    """根据报告类型构建 ``(system_prompt, user_prompt)`` 二元组。

    Args:
        report_type: 报告类型标识，需为 ``_SYSTEM_PROMPTS`` 中的合法键。
        log_data: 演化日志数据（字符串或节点列表）。
        background: 任务背景/上下文描述字符串。
    """
    system = _SYSTEM_PROMPTS[report_type]
    template = REPORT_TEMPLATES[report_type]["user_prompt_template"]
    bg = background or "No additional background provided."

    if report_type == "tech_change":
        user = template.format(background=bg, logs_summary=_truncate(str(log_data)))
    else:
        data_str = _truncate(_serialize_nodes(log_data))  # type: ignore[arg-type]
        variable_name = REPORT_TEMPLATES[report_type]["variables"][1]
        user = template.format(background=bg, **{variable_name: data_str})

    return system, user
