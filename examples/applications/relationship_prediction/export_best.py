"""Export the best relationship prediction from an LLM4AD run to a Markdown file.

Reads the best individual's cached output (or runs the script once),
optionally translates it, and writes a Markdown result file.

Usage:
    python export_best.py              # output as-is (no translation)
    python export_best.py --lang en    # translate to English
    python export_best.py --lang zh    # keep Chinese (no-op)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

TRANSLATE_PROMPT = {
    "en": (
        "Translate the following Markdown relationship prediction into English. "
        "Keep all Markdown formatting, headers, bullet points, dialogue, and structure intact. "
        "Translate all Chinese text including dialogue, stage directions, and analysis. "
        "Output ONLY the translated Markdown, nothing else.\n\n{text}"
    ),
    "zh": None,  # Predictions are already in Chinese
}


def find_latest_run(base_dir: Path) -> Path:
    """Find the most recent run directory."""
    runs = sorted(base_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        raise FileNotFoundError(f"No runs found in {base_dir}")
    return runs[0]


def find_best_individual(run_dir: Path) -> tuple[dict, float]:
    """Find the individual with the highest score."""
    generated_dir = run_dir / "generated"
    best_score = -1.0
    best_data = None

    for json_file in generated_dir.glob("*.json"):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        ev = data.get("evaluation") or {}
        score = ev.get("score")
        if score is not None and score > best_score:
            best_score = score
            best_data = data

    if best_data is None:
        raise ValueError("No evaluated individuals found")
    return best_data, best_score


def find_script(wt_path: Path) -> Path:
    """Find the generated script in a worktree."""
    for name in ("predict_seed.py", "predict.py", "scenario.py", "analysis.py", "plan.py"):
        p = wt_path / name
        if p.exists():
            return p
    raise FileNotFoundError(f"No Python script found in {wt_path}")


def read_cached_output(wt_path: Path, case_stem: str) -> str | None:
    """Try to read cached output saved by the evaluator."""
    cache_file = wt_path / f"_output_{case_stem}.md"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    return None


def run_script(script: Path) -> str:
    """Run the prediction script once without case input."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    api_cfg = load_api_config()
    env["LLM_BASE_URL"] = api_cfg.get("base_url", "")
    env["LLM_API_KEY"] = api_cfg.get("api_key", "")
    env["LLM_MODEL"] = api_cfg.get("model", "")
    env["OPENAI_API_KEY"] = api_cfg.get("api_key", "")
    env["OPENAI_BASE_URL"] = api_cfg.get("base_url", "")

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, timeout=300, encoding="utf-8", errors="replace",
        env=env,
    )
    if result.returncode != 0:
        return f"**Script failed:**\n```\n{(result.stderr or '').strip()}\n```"
    return (result.stdout or "").strip()


def translate_text(text: str, lang: str, api_config: dict) -> str:
    """Translate text using LLM if needed."""
    prompt_tpl = TRANSLATE_PROMPT.get(lang)
    if prompt_tpl is None:
        return text

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_config["api_key"],
            base_url=api_config["base_url"],
        )
        response = client.chat.completions.create(
            model=api_config["model"],
            messages=[{"role": "user", "content": prompt_tpl.format(text=text)}],
            max_tokens=4000,
            temperature=0.3,
        )
        translated = (response.choices[0].message.content or "").strip()
        return translated if translated else text
    except Exception as e:
        print(f"  Translation failed ({e}), using original text")
        return text


def load_api_config() -> dict:
    """Load API config from the YAML configuration file."""
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("evaluator", {}).get("api_config", {})


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Export best relationship prediction to Markdown")
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default=None,
        help="Translate output to target language (default: no translation)",
    )
    return parser.parse_args()


def main():
    """Export the best relationship prediction to a Markdown file."""
    args = parse_args()
    lang = args.lang

    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir / "runs" / "relationship_outcome_prediction"
    if not base_dir.exists():
        base_dir = Path("runs/relationship_outcome_prediction")
    out_dir = script_dir / "result"
    out_dir.mkdir(exist_ok=True)

    run_dir = find_latest_run(base_dir)
    best_data, best_score = find_best_individual(run_dir)
    name = best_data.get("name", "Unknown")
    gen = best_data.get("generation", "?")
    island = best_data.get("island_id", "?")
    ind_id = best_data.get("id", "?")
    print(f"Run: {run_dir.name}")
    print(f"Best: {name} | score={best_score} | gen={gen} island={island}")

    wt_path = Path((best_data.get("worktree") or {}).get("path", ""))

    output = read_cached_output(wt_path, "default")
    if not output:
        script = find_script(wt_path)
        print("No cached output, running script...")
        output = run_script(script)

    if not output:
        print("No output produced")
        return

    if lang:
        api_config = load_api_config()
        print(f"Translating to {lang}...")
        output = translate_text(output, lang, api_config)

    md = f"""---
score: {best_score}
algorithm: {name}
generation: {gen}
island: {island}
id: {ind_id}
run: {run_dir.name}
---

{output}
"""
    filename = f"best_prediction_{lang}.md" if lang else "best_prediction.md"
    out_file = out_dir / filename
    out_file.write_text(md, encoding="utf-8")
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
