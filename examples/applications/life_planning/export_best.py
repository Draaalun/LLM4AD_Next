"""Export the best life plan from an LLM4AD run to a Markdown file.

Runs the best individual's script against every profile in the data directory,
producing a combined Markdown with one section per profile.

Usage:
    python export_best.py              # default: English
    python export_best.py --lang en    # English output
    python export_best.py --lang zh    # Chinese output
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

LANG_LABELS = {
    "en": {
        "profile": "Profile",
        "filename": "best_plan_en.md",
        "running": "Running for",
        "saved": "Saved to",
    },
    "zh": {
        "profile": "用户画像",
        "filename": "best_plan_zh.md",
        "running": "正在运行",
        "saved": "已保存到",
    },
}

# Prompt templates for translating the plan to the target language
TRANSLATE_PROMPT = {
    "en": None,  # No translation needed, scripts already output English
    "zh": (
        "Translate the following Markdown life plan into Chinese. "
        "Keep all Markdown formatting, headers, bullet points, and structure intact. "
        "Translate all English text including goal names, descriptions, and criteria. "
        "Output ONLY the translated Markdown, nothing else.\n\n{text}"
    ),
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
    for name in ("implementation.py", "plan.py"):
        p = wt_path / name
        if p.exists():
            return p
    raise FileNotFoundError(f"No Python script found in {wt_path}")


def read_cached_output(wt_path: Path, profile_stem: str) -> str | None:
    """Try to read cached output saved by the evaluator."""
    cache_file = wt_path / f"_output_{profile_stem}.md"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    return None


def run_with_profile(script: Path, wt_path: Path, profile_yaml: Path) -> str:
    """Read cached output if available, otherwise run script with profile."""
    # Try cache first (saved by evaluator during pipeline run)
    cached = read_cached_output(wt_path, profile_yaml.stem)
    if cached:
        return cached

    # No cache — run the script
    with open(profile_yaml, "r", encoding="utf-8") as f:
        profile_data = yaml.safe_load(f)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8",
    ) as tmp:
        json.dump(profile_data, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_PROXY"] = "*"
    env["HTTP_PROXY"] = ""
    env["HTTPS_PROXY"] = ""
    api_cfg = load_api_config()
    env["LLM_BASE_URL"] = api_cfg.get("base_url", "")
    env["LLM_API_KEY"] = api_cfg.get("api_key", "")
    env["LLM_MODEL"] = api_cfg.get("model", "")
    # Compatibility: some generated scripts use OPENAI_API_KEY/OPENAI_BASE_URL
    env["OPENAI_API_KEY"] = api_cfg.get("api_key", "")
    env["OPENAI_BASE_URL"] = api_cfg.get("base_url", "")

    result = subprocess.run(
        [sys.executable, str(script), tmp_path],
        capture_output=True, timeout=300, encoding="utf-8", errors="replace",
        env=env,
    )
    Path(tmp_path).unlink(missing_ok=True)

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
            max_tokens=2048,
            temperature=0.3,
        )
        translated = (response.choices[0].message.content or "").strip()
        return translated if translated else text
    except Exception as e:
        print(f"  Translation failed ({e}), using original text")
        return text


def load_api_config() -> dict:
    """Load API config from the YAML configuration file."""
    config_path = Path("examples/applications/life_planning/life_planning.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("evaluator", {}).get("api_config", {})


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Export best life plan to Markdown")
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Output language: en (English, default) or zh (Chinese)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    lang = args.lang
    labels = LANG_LABELS[lang]

    base_dir = Path("runs/life_planning_code_based")
    data_dir = Path("examples/applications/life_planning/data")
    out_dir = Path("examples/applications/life_planning/result")
    out_dir.mkdir(exist_ok=True)

    run_dir = find_latest_run(base_dir)
    best_data, best_score = find_best_individual(run_dir)
    name = best_data.get("name", "Unknown")
    gen = best_data.get("generation", "?")
    island = best_data.get("island_id", "?")
    ind_id = best_data.get("id", "?")
    print(f"Run: {run_dir.name}")
    print(f"Best: {name} | score={best_score} | gen={gen} island={island}")
    print(f"Language: {lang}")

    wt_path = Path((best_data.get("worktree") or {}).get("path", ""))
    script = find_script(wt_path)

    profiles = sorted(data_dir.glob("*.yaml")) or sorted(data_dir.glob("*.yml"))

    # Load API config for translation (only needed for zh)
    api_config = load_api_config() if lang == "zh" else {}

    sections = []
    for p in profiles:
        print(f"  {labels['running']} {p.stem}...")
        output = run_with_profile(script, wt_path, p)
        if lang != "en" and output and not output.startswith("**Script failed"):
            print(f"  Translating {p.stem}...")
            output = translate_text(output, lang, api_config)
        sections.append((p.stem, output))

    md = f"""---
score: {best_score}
algorithm: {name}
generation: {gen}
island: {island}
id: {ind_id}
run: {run_dir.name}
language: {lang}
---
"""
    for label, output in sections:
        md += f"\n---\n\n> **{labels['profile']}: {label}**\n\n{output}\n"

    out_file = out_dir / labels["filename"]
    out_file.write_text(md, encoding="utf-8")
    print(f"\n{labels['saved']} {out_file} ({len(sections)} profiles)")


if __name__ == "__main__":
    main()
