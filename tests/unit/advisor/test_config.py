"""Tests for advisor config generation and loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm4ad.advisor.advisor_config import (
    generate_advisor_config,
    load_advisor_config,
)
from llm4ad.advisor.pipeline import AdvisorError


def test_generate_and_load_round_trip(tmp_path: Path, monkeypatch):
    """Generated template can be loaded back after filling in a key."""
    path = tmp_path / "advise.yaml"
    generate_advisor_config(path, goal="minimize comparisons")

    # The template uses ${LLM4AD_ADVISE_API_KEY}; expansion needs the env var.
    monkeypatch.setenv("LLM4AD_ADVISE_API_KEY", "sk-test")
    monkeypatch.setenv("LLM4AD_ADVISE_BASE_URL", "https://example.test/v1")

    cfg = load_advisor_config(path)
    assert cfg.advisor.api_key == "sk-test"
    assert cfg.advisor.base_url == "https://example.test/v1"
    assert "minimize comparisons" in cfg.task.goal


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(AdvisorError, match="not found"):
        load_advisor_config(tmp_path / "nope.yaml")


def test_load_requires_api_key(tmp_path: Path):
    path = tmp_path / "advise.yaml"
    path.write_text(
        "advisor:\n"
        "  api_key: \"\"\n"
        "task:\n"
        "  goal: anything\n",
        encoding="utf-8",
    )
    with pytest.raises(AdvisorError, match="No API key"):
        load_advisor_config(path)


def test_load_requires_goal(tmp_path: Path):
    path = tmp_path / "advise.yaml"
    path.write_text(
        "advisor:\n"
        "  api_key: sk-x\n"
        "task:\n"
        "  goal: \"\"\n",
        encoding="utf-8",
    )
    with pytest.raises(AdvisorError, match="No goal"):
        load_advisor_config(path)


def test_line_range_parsed_as_tuple(tmp_path: Path):
    path = tmp_path / "advise.yaml"
    path.write_text(
        "advisor:\n"
        "  api_key: sk-x\n"
        "task:\n"
        "  goal: g\n"
        "  line_range: [3, 9]\n",
        encoding="utf-8",
    )
    cfg = load_advisor_config(path)
    assert cfg.task.line_range == (3, 9)
