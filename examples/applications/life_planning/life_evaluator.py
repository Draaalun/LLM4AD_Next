"""Life Planning Evaluator using LLMJudgeEvaluator base class.

Executes the generated Python script to capture the Markdown plan,
then uses an LLM judge to score it on actionability, alignment,
comprehensiveness, and personalization.
"""

from llm4ad.evaluator.base import Metric, MetricType
from llm4ad.evaluator.llm_judge import LLMJudgeEvaluator


@LLMJudgeEvaluator.register("life_planning_evaluator")
class LifePlanningEvaluator(LLMJudgeEvaluator):
    """Evaluator for LLM-generated life plans."""

    script_patterns = ["implementation.py", "plan.py"]

    @property
    def name(self) -> str:
        """Get evaluator name."""
        return "life_planning_evaluator"

    @property
    def metrics(self) -> list[Metric]:
        """Get evaluation metrics."""
        return [
            Metric(name="actionability", type=MetricType.MAXIMIZE, weight=0.3),
            Metric(name="alignment", type=MetricType.MAXIMIZE, weight=0.3),
            Metric(name="comprehensiveness", type=MetricType.MAXIMIZE, weight=0.15),
            Metric(name="personalization", type=MetricType.MAXIMIZE, weight=0.25),
        ]

    def build_judge_prompt(self, data_content: str, script_output: str) -> str:
        """Build the LLM judge prompt for life plan evaluation.

        Args:
            data_content: Raw YAML user profile.
            script_output: Generated Markdown life plan.

        Returns:
            Judge prompt string.
        """
        return f"""
You are an expert, impartial, and strict life planning consultant. \
Your task is to critically evaluate a life plan generated for a user \
based on their personal profile.

**1. User's Personal Profile:**
```yaml
{data_content}
```

**2. The AI-Generated Life Plan to Evaluate:**
```markdown
{script_output}
```

**3. Your Task and Evaluation Criteria:**
Review the generated plan and score it on the following four criteria.
Scores must be integers from 1 (terrible) to 10 (excellent).
- Actionability (1-10): How concrete, specific, and actionable are the proposed steps? Are the goals S.M.A.R.T.?
- Alignment (1-10): How well does the plan reflect the user's core values and long-term aspirations?
- Comprehensiveness (1-10): Does the plan address the key areas of life implied by the user's aspirations?
- Personalization (1-10): Are the goals genuinely derived from THIS specific user's profile?
      - 10: Goals directly reference the user's actual aspirations and values
      - 5: Goals are loosely related but feel generic
      - 1: Goals are completely generic
      CRITICAL CHECK: Compare the user's current_role and aspirations against each
      specific goal in the plan. If the goals would make equal sense for a completely
      different person, they are not personalized.

**4. Required Output Format:**
You MUST provide your response in a raw JSON format, without any
introductory text, explanations, or markdown code fences.
The JSON object must contain the four scores and a brief reasoning string.
Example of a valid response:
{{
"actionability": 8,
"alignment": 9,
"comprehensiveness": 7,
"personalization": 8,
"reasoning": "The plan is highly aligned but lacks specific financial steps."
}}
"""
