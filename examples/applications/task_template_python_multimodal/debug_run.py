"""Debug entry point for the multimodal task template pipeline.

Usage:
    Run from any directory -- the script auto-chdir to the task folder
    so that relative paths in the YAML resolve correctly.

    uv run python debug_run.py

This is the multimodal version. After the run completes, it checks
for behavior data (images + observations) on the best individual.
"""

import asyncio
import os
from pathlib import Path

from llm4ad import LLM4AD

# Ensure CWD is the task directory so YAML relative paths resolve correctly
TASK_DIR = Path(__file__).resolve().parent
os.chdir(TASK_DIR)


async def main():
    """Run the full LLM4AD pipeline for the template task (multimodal)."""
    # TODO: Change to your YAML config filename
    llm4ad = LLM4AD("my_task_benchmark.yaml")
    llm4ad.print_run_summary()
    result = await llm4ad.run()

    if result.best_individual:
        print(f"Best score: {result.best_individual.score:.4f}")
        print(f"Best algorithm: {result.best_individual.name}")

        # Multimodal addition: check for behavior data
        if result.best_individual.has_behavior():
            print("Visualization available for best algorithm.")
            obs = result.best_individual.get_observation_text()
            if obs:
                print(f"Behavior observation: {obs}")
    else:
        print("No valid individual found.")


if __name__ == "__main__":
    asyncio.run(main())
