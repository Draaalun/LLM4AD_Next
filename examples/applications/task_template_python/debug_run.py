"""Debug entry point template for running the full LLM4AD pipeline.

TEMPLATE INSTRUCTIONS:
    1. Update the YAML config filename
    2. Run: uv run python debug_run.py
    3. Set breakpoints in VSCode at key locations:
        - src/llm4ad/evaluator/dispatcher.py  (data file iteration / aggregation)
        - src/llm4ad/orchestrator/island_ga.py (evaluation results handling)
        - my_evaluator.py                     (evaluate entry point)

Usage:
    Run from any directory -- the script auto-chdir to the task folder
    so that relative paths in the YAML resolve correctly.
"""

import asyncio
import os
from pathlib import Path

from llm4ad import LLM4AD

# Ensure CWD is the task directory so YAML relative paths resolve correctly
TASK_DIR = Path(__file__).resolve().parent
os.chdir(TASK_DIR)


async def main():
    """Run the full LLM4AD pipeline for this task."""
    # TEMPLATE: Change to your YAML config filename
    llm4ad = LLM4AD("my_task_benchmark.yaml")
    llm4ad.print_run_summary()
    result = await llm4ad.run()

    if result.best_individual:
        print(f"Best score: {result.best_individual.score:.4f}")
        print(f"Best algorithm: {result.best_individual.name}")
    else:
        print("No valid individual found.")


if __name__ == "__main__":
    asyncio.run(main())
