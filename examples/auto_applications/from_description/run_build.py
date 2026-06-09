#!/usr/bin/env python3
"""Example: Build an LLM4AD application from a build config YAML file.

This script demonstrates the config-based build workflow used by the
multi-user platform:

  1. Frontend generates a build config YAML template
  2. User fills in LLM credentials + problem description
  3. This script reads the completed YAML and runs the build pipeline

Prerequisites:
  Set the environment variables referenced in build_config.yaml:
    export LLM4AD_BUILD_API_KEY="sk-your-key"
    export LLM4AD_BUILD_BASE_URL="https://api.openai.com/v1"

Usage:
    python run_build.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from llm4ad.builder import build_from_config_sync  # noqa: E402


def main():
    """Run the config-based build pipeline."""
    config_path = Path(__file__).parent / "build_config.yaml"

    print("=" * 60)
    print("LLM4AD Automated Task Builder — Config-Based Build")
    print("=" * 60)
    print(f"Config: {config_path}")
    print()

    def on_progress(stage: int, total: int, message: str):
        """Report progress."""
        print(f"  [{stage}/{total}] {message}")

    try:
        task_dir = build_from_config_sync(
            str(config_path),
            on_progress=on_progress,
        )
    except Exception as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("BUILD COMPLETE — Application generated at:")
    print(f"  {task_dir}")
    print()
    print("Generated files:")
    for p in sorted(Path(task_dir).rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(task_dir)}")
    print()
    print("Next steps:")
    print(f"  1. Review and edit: {task_dir}/config.yaml")
    print(f"  2. Quick test:      python {task_dir}/debug_run.py")
    print(f"  3. Run evolution:   llm4ad run {task_dir}/config.yaml")
    print("=" * 60)


if __name__ == "__main__":
    main()
