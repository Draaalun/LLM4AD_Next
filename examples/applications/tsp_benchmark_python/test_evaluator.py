"""Test script to check if the TSP evaluator can be loaded correctly."""

from llm4ad.evaluator.dispatcher import EvaluationDispatcher
from llm4ad.config import EvaluatorConfig

config = EvaluatorConfig(
    module="tsp_evaluator.py:PythonTSPEvaluator",
    timeout=60.0,
    max_retries=2,
    parallel=True,
    batch_size=5,
    dataset={"mode": "directory", "path": "data/small", "recursive": False},
    metrics=["tour_length", "execution_time_ms", "valid_tour"],
)

try:
    dispatcher = EvaluationDispatcher(config=config)
    print("Evaluator loaded successfully")
    print(f"Evaluator class: {dispatcher._eval_cls}")
except Exception as e:
    print(f"Error loading evaluator: {e}")
    import traceback

    traceback.print_exc()
