"""Relationship outcome predictor - evolved prediction text."""


# EVOLVE_START: outcome_predictor
def get_prediction() -> str:
    """Return multi-outcome relationship prediction with probability ranking.

    Returns a prediction with one primary outcome and two alternatives,
    each with explicit probability. Evolution optimizes for selecting
    the most likely outcome given the specific personality traits.
    """
    return (
        "## 最可能结局（概率 X%）\n\n"
        "### 结局描述\n"
        "[给出明确的单一结局判断]\n\n"
        "### 时间线\n"
        "**第1-3天：** [危机后最初几天的微观互动与行为细节]\n"
        "**第4-7天：** [试探、升级或修复的具体行为过程]\n"
        "**第2周及以后：** [最终结局的执行或巩固过程]\n\n"
        "### 推理链\n"
        "1. [从核心特质出发，推导行为动机]\n"
        "2. [特质碰撞如何引发特定互动模式]\n"
        "3. [为什么这个结局是概率最高的]\n\n"
        "---\n\n"
        "## 替代结局 A（概率 Y%）\n\n"
        "### 结局描述\n"
        "[另一种可能的走向]\n\n"
        "### 触发条件\n"
        "[在什么条件下这个结局会发生而非主结局]\n\n"
        "### 为什么不是最可能\n"
        "[基于具体特质解释为什么这个结局概率低于主结局]\n\n"
        "---\n\n"
        "## 替代结局 B（概率 Z%）\n\n"
        "### 结局描述\n"
        "[第三种可能的走向]\n\n"
        "### 触发条件\n"
        "[在什么条件下这个结局会发生]\n\n"
        "### 为什么不是最可能\n"
        "[基于具体特质解释为什么这个结局概率最低]\n\n"
        "---\n\n"
        "## 排除推理\n\n"
        "[总结：为什么主结局比替代结局更可能——"
        "指出关键的人格特质差异点，"
        "说明哪些特质组合决定了概率排序]\n"
    )
# EVOLVE_END: outcome_predictor


if __name__ == "__main__":
    print(get_prediction())
