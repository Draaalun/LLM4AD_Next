#!/usr/bin/env python3
"""Run the auto-build pipeline with from_code mode (EVOLVE marker reuse).

Usage:
    cd examples/auto_applications_from_code
    python run_build.py

Requires LLM4AD_BUILD_API_KEY, LLM4AD_BUILD_BASE_URL environment variables.
"""

from llm4ad.builder import build_from_config_sync


def main():
    task_dir = build_from_config_sync(
        "build_config.yaml",
        on_progress=lambda stage, total, msg: print(f"[{stage}/{total}] {msg}"),
    )
    print(f"\nBuild complete! Output directory: {task_dir}")


if __name__ == "__main__":
    main()
