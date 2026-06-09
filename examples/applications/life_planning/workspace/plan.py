"""Life plan generator that calls LLM API to produce personalized plans."""

import os
import sys
import json
from openai import OpenAI


# EVOLVE_START: prompt_strategy
def build_prompt(p: dict) -> str:
    """Build the prompt that instructs the LLM to generate a life plan.

    This function will be evolved to find the best prompt engineering strategy.
    """
    return (
        f"You are a professional life planning consultant. "
        f"Create a detailed {p['time_horizon_years']}-year life plan for {p['name']}, "
        f"age {p['age']}, currently working as {p['current_role']}. "
        f"Their aspirations: {', '.join(p['aspirations'])}. "
        f"Their core values: {', '.join(p['values'])}. "
        f"Output in Markdown with 4 modules: "
        f"1) Career Development, 2) Personal Growth, "
        f"3) Financial Health, 4) Life & Travel. "
        f"Each module must have 1-2 S.M.A.R.T goals "
        f"(Specific, Measurable, Achievable, Relevant, Time-bound) "
        f"with concrete action steps, specific numbers, and deadlines. "
        f"Tailor every goal to this person's specific aspirations and values."
    )
# EVOLVE_END: prompt_strategy


def generate_plan(profile_path: str) -> str:
    """Generate a personalized life plan by calling LLM API."""
    p = json.load(open(profile_path, encoding="utf-8"))
    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", os.environ.get("OPENAI_BASE_URL", "https://llmapi.paratera.com")),
        api_key=os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
    )
    model = os.environ.get("LLM_MODEL", "Kimi-K2.5")
    prompt = build_prompt(p)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plan.py <profile.json>")
        sys.exit(1)
    print(generate_plan(sys.argv[1]))
