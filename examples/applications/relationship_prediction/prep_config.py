"""Sync case data into the YAML config's background field.

Run this script before starting evolution to ensure the planner
has the correct case information.

Usage:
    python prep_config.py                          # use first case in data/
    python prep_config.py --case data/case_02.yaml # specify a case file
"""

import argparse
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

BACKGROUND_TEMPLATE = """\
  This project predicts the most likely outcome for a relationship crisis case
  using a MULTI-OUTCOME COMPETITION approach.

  ===== CRITICAL CONSTRAINT =====
  You are evolving PREDICTION TEXT, not code or algorithms.
  The EVOLVE block contains `get_prediction() -> str` which returns a hardcoded
  Chinese-language prediction string. You MUST keep this structure:
  - The function takes NO arguments
  - The function body is ONLY a return statement with string concatenation
  - Do NOT add imports, classes, data structures, simulations, or API calls
  - Do NOT rename the function or change its signature
  - ONLY modify the TEXT CONTENT of the returned string
  - The output file MUST be named predict_seed.py (not implementation.py)
  ===== END CONSTRAINT =====

  ===== EVALUATION PRIORITY =====
  The evaluator judges WHETHER YOU PICKED THE RIGHT OUTCOME, not how well
  you write. A plainly-written prediction that picks the correct most-likely
  outcome will score HIGHER than a beautifully-written prediction that picks
  the wrong outcome. Focus on:
  1. Is the primary outcome truly the most probable given these two people?
  2. Are the alternative outcomes real possibilities (not strawmen)?
  3. Does the exclusion reasoning pinpoint specific trait differences?
  ===== END PRIORITY =====

  Your task: improve the prediction to select the most probable outcome.
  Think about:
  - Given these specific personality traits, what outcome has the highest probability?
  - What alternative outcomes are genuinely possible, and why are they less likely?
  - Which specific traits determine the probability ranking between outcomes?
  - Is the primary outcome probability >50%? Be decisive, not hedging.

  ## The Case to Predict

{case_indented}

  ## Required Output Structure (Multi-Outcome Competition)

  The prediction MUST include these sections:
  1. 最可能结局（概率 X%） - Primary outcome with timeline and reasoning chain
  2. 替代结局 A（概率 Y%） - First alternative with trigger conditions and exclusion reasoning
  3. 替代结局 B（概率 Z%） - Second alternative with trigger conditions and exclusion reasoning
  4. 排除推理 - Summary of why primary > alternatives, citing specific trait differences

  Rules:
  - X + Y + Z = 100%, X > Y > Z, X > 50%
  - Each alternative must be a REAL possibility, not a strawman
  - Exclusion reasoning must cite SPECIFIC traits that determine the ranking
"""


def find_default_case() -> Path:
    """Find the first case file in data/."""
    data_dir = SCRIPT_DIR / "data"
    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"Data directory not found: {data_dir}. "
            "Use --case to specify a case file explicitly."
        )
    cases = sorted(data_dir.glob("case_*.yaml")) + sorted(data_dir.glob("case_*.yml"))
    if not cases:
        raise FileNotFoundError(f"No case files found in {data_dir}")
    return cases[0]


def indent_text(text: str, prefix: str = "  ") -> str:
    """Indent each line of text with a prefix."""
    return "\n".join(prefix + line if line.strip() else "" for line in text.splitlines())


def main() -> None:
    """Sync case data into YAML config background field via text replacement."""
    parser = argparse.ArgumentParser(description="Sync case data into config background")
    parser.add_argument("--case", type=str, help="Path to case YAML file (default: first in data/)")
    args = parser.parse_args()

    case_path = Path(args.case).resolve() if args.case else find_default_case()

    case_text = case_path.read_text(encoding="utf-8").strip()
    case_indented = indent_text(case_text)
    background_block = BACKGROUND_TEMPLATE.format(case_indented=case_indented)

    yaml_text = CONFIG_PATH.read_text(encoding="utf-8")

    # Replace the background field: match from "background:" to the next top-level key
    pattern = r"(background:\s*[|>]?-?\n).*?(\n\S)"
    replacement = f"background: |\n{background_block}\n\\2"
    new_yaml = re.sub(pattern, replacement, yaml_text, count=1, flags=re.DOTALL)

    if new_yaml == yaml_text and "background:" not in yaml_text:
        raise ValueError("Could not find 'background:' field in YAML config")

    CONFIG_PATH.write_text(new_yaml, encoding="utf-8")
    print(f"Synced case: {case_path.name}")
    print(f"Updated: {CONFIG_PATH.name}")


if __name__ == "__main__":
    main()
