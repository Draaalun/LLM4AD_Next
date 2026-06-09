"""Relationship Outcome Evaluator - multi-outcome plausibility judge."""

from llm4ad.evaluator.base import Metric, MetricType
from llm4ad.evaluator.llm_judge import LLMJudgeEvaluator


@LLMJudgeEvaluator.register("relationship_outcome_evaluator")
class RelationshipOutcomeEvaluator(LLMJudgeEvaluator):
    """Evaluator for multi-outcome relationship predictions.

    Judges whether the prediction correctly identifies the most likely
    outcome among competing alternatives, prioritizing plausibility
    over writing quality.
    """

    script_patterns = ["predict_seed.py", "predict.py", "analysis.py"]

    @property
    def name(self) -> str:
        """Get evaluator name."""
        return "relationship_outcome_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get evaluation metrics."""
        return [
            Metric(name="outcome_plausibility", type=MetricType.MAXIMIZE, weight=0.30),
            Metric(name="alternative_reasoning", type=MetricType.MAXIMIZE, weight=0.20),
            Metric(name="trait_specificity", type=MetricType.MAXIMIZE, weight=0.20),
            Metric(name="causal_chain", type=MetricType.MAXIMIZE, weight=0.15),
            Metric(name="behavioral_concreteness", type=MetricType.MAXIMIZE, weight=0.15),
        ]

    def build_judge_prompt(self, data_content: str, script_output: str) -> str:
        """Build the LLM judge prompt for multi-outcome prediction evaluation.

        Args:
            data_content: Raw YAML case description.
            script_output: Generated multi-outcome prediction output.

        Returns:
            Judge prompt string.
        """
        return (
            "你是一位融合心理学与系统动力学的资深研究员。"
            "你的任务是判断一份“多结局预测”是否选对了最可能的结局。\n\n"
            "**核心原则：你评估的是“预测是否选对了最可能发生的事”，而非“文字写得好不好”。"
            "一个文笔平淡但选对了结局的预测，应该比一个文采飞扬但选错了结局的预测得分更高。**\n\n"
            "**评分要求：使用1-100分的精细评分，不要四舍五入到整十数。"
            "请拉开各维度的分数差距，真正差的维度就给低分（40-60），真正好的维度才给高分（85+）。"
            "五个维度的分数不应雷同，每个维度独立判断。**\n\n"
            f"## 案例描述\n```yaml\n{data_content}\n```\n\n"
            f"## 生成的多结局预测\n```\n{script_output}\n```\n\n"
            "## 评分任务\n\n请从以下五个维度给分（1-100分）。\n\n---\n\n"
            "### 1. 结局可能性 (outcome_plausibility, 1-100分)\n\n"
            "**核心检验：主结局是否是给定这两个人的性格和当前处境下，概率最高的走向？**\n\n"
            "- **85-100分（极罕见）：** 读完后强烈觉得“这就是会发生的事”。主结局是唯一合理的高概率走向，"
            "概率分配果断（主结局>50%），且能让人理解为什么其他走向不太可能。\n"
            "- **70-84分：** 主结局合理且可信，但概率分配不够果断，或者存在一个更可能的走向被放在了替代结局里。\n"
            "- **55-69分：** 主结局是可能的但不是最可能的。有更合理的走向被忽略，或者主结局过于理想化/戏剧化。\n"
            "- **40-54分：** 主结局不太可能发生，或者回避了明确判断（概率分配过于均匀如34/33/33）。\n"
            "- **40分以下：** 主结局明显不合理，或者没有给出明确的概率排序。\n\n---\n\n"
            "### 2. 替代结局与排除推理 (alternative_reasoning, 1-100分)\n\n"
            "**核心检验：替代结局是否是真实存在的可能性（而非稻草人）？排除推理是否精准指出了关键差异？**\n\n"
            "- **85-100分（极罕见）：** 替代结局是真正有可能发生的走向，排除推理精准指出了具体的人格特质差异点"
            "——如果某个特质不同，替代结局就会变成主结局。\n"
            "- **70-84分：** 替代结局合理，排除推理有说服力，但有1处论证薄弱或过于笼统。\n"
            "- **55-69分：** 替代结局太弱（明显不可能，只是凑数），或排除推理泛泛而谈，没有指出具体的特质差异。\n"
            "- **40-54分：** 替代结局是稻草人，或完全没有排除推理。\n"
            "- **40分以下：** 没有提供替代结局，或替代结局与主结局本质相同。\n\n---\n\n"
            "### 3. 特质排他性 (trait_specificity, 1-100分)\n\n"
            "**核心检验：如果把案例中的MBTI、依恋类型或core_traits换成其他类型，这篇预测是否立刻不成立？**\n\n"
            "- **85-100分（极罕见）：** 预测的每一个关键行为都能追溯到案例中的具体特质，"
            "且这些特质是不可替换的“齿轮”。把任何一个特质换掉，概率排序就会改变。\n"
            "- **70-84分：** 大部分行为预测与特质有明确关联，但有1-2处可以适用于同类型的其他人格组合。\n"
            "- **55-69分：** 表面引用了特质词汇，但推演路径是该依恋类型的通用套路。去掉MBTI标签不影响阅读。\n"
            "- **40-54分：** 严重依赖刻板印象，忽略了core_traits中的细腻信息。\n"
            "- **40分以下：** 特质只在开头提及，正文推演完全没用到。\n\n---\n\n"
            "### 4. 因果链完整性 (causal_chain, 1-100分)\n\n"
            "**从当前状态到主结局，因果链条是否完整、严密、无跳跃？**\n\n"
            "- **85-100分（极罕见）：** 每一步推演自然推出下一步，且能解释为什么在每个分叉点走向了主结局而非替代结局。\n"
            "- **70-84分：** 因果链完整，使用了可识别的心理学理论，结局令人信服。\n"
            "- **55-69分：** 整体逻辑通顺，有1-2处跳跃或缺乏解释的环节。\n"
            "- **40-54分：** 逻辑链有明显断裂，结局缺乏论证支撑。\n"
            "- **40分以下：** 结局像是随意给出的。\n\n---\n\n"
            "### 5. 行为具象度 (behavioral_concreteness, 1-100分)\n\n"
            "**主结局的时间线中，行为描述是否具体到“可以拍成短剧”的程度？**\n\n"
            "- **85-100分（极罕见）：** 有精确的对话台词、肢体语言描写、具体时间节点，每个细节都能追溯到人物特征。\n"
            "- **70-84分：** 行为预测具体（有对话、动作），时间线有天级别粒度。\n"
            "- **55-69分：** 有结局判断和大致时间线，但描述偏笼统。\n"
            "- **40-54分：** 行为描述模糊，缺少具体场景。\n"
            "- **40分以下：** 全是抽象描述，没有画面感。\n\n---\n\n"
            "## 输出格式\n\n返回纯JSON，不要其他内容：\n"
            "{{\n"
            '"outcome_plausibility": N,\n'
            '"alternative_reasoning": N,\n'
            '"trait_specificity": N,\n'
            '"causal_chain": N,\n'
            '"behavioral_concreteness": N,\n'
            '"reasoning": "2-3句评价，指出预测在结局选择上最强和最弱的地方"\n'
            "}}"
        )
