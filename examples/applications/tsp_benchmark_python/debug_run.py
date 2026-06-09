"""Debug entry point for TSP benchmark pipeline.

Usage:
    Run from any directory — the script auto-chdir to the task folder
    so that relative paths in the YAML resolve correctly.

Set breakpoints in VSCode at key locations:
    - src/llm4ad/evaluator/dispatcher.py:148  (data_files iteration)
    - src/llm4ad/evaluator/dispatcher.py:155  (results returned)
    - src/llm4ad/orchestrator/island_ga.py:806 (results[0] — only first used)
    - tsp_evaluator.py:116                     (evaluate entry)
"""

import asyncio
import os
from pathlib import Path

from llm4ad import LLM4AD

# Ensure CWD is the task directory so YAML relative paths resolve correctly
TASK_DIR = Path(__file__).resolve().parent
os.chdir(TASK_DIR)


async def main():
    """Run the full LLM4AD pipeline for the TSP task."""
    llm4ad = LLM4AD("tsp_benchmark.yaml")
    llm4ad.print_run_summary()
    result = await llm4ad.run()

    if result.best_individual:
        print(f"Best score: {result.best_individual.score:.4f}")
        print(f"Best algorithm: {result.best_individual.name}")
    else:
        print("No valid individual found.")


if __name__ == "__main__":
    asyncio.run(main())
