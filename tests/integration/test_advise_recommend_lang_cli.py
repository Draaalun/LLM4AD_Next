"""Integration tests for --lang validation on advise / recommend CLI.

These tests do NOT call a real LLM; they only verify that the CLI rejects
invalid --lang values before any provider is contacted.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from llm4ad.frontend.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    """Standard CliRunner; advise/recommend don't need stderr separation here."""
    return CliRunner()


class TestLangValidation:
    """Both commands must reject --lang values outside {en, zh}."""

    def test_advise_rejects_unknown_lang(self, runner: CliRunner) -> None:
        """Advise rejects --lang fr with a helpful error and exits 1."""
        result = runner.invoke(
            app,
            ["advise", "-g", "x", "--code", "print('x')", "--lang", "fr"],
        )
        assert result.exit_code == 1
        assert "--lang" in result.stdout
        assert "'en'" in result.stdout and "'zh'" in result.stdout

    def test_recommend_rejects_unknown_lang(self, runner: CliRunner, tmp_path) -> None:
        """Recommend rejects --lang xx and exits 1 before contacting any provider."""
        result = runner.invoke(
            app,
            ["recommend", "-g", "x", "-r", str(tmp_path), "--lang", "xx"],
        )
        assert result.exit_code == 1
        assert "--lang" in result.stdout

    def test_lang_is_case_insensitive(self, runner: CliRunner) -> None:
        """`--lang EN` is accepted and normalized.

        The command may still fail on a different path (missing provider
        credentials), but it must not fail with the --lang error message.
        """
        result = runner.invoke(
            app,
            ["advise", "-g", "x", "--code", "print('x')", "--lang", "EN"],
        )
        # Should NOT fail with the --lang error; if it does, regression.
        assert "--lang must be" not in result.stdout
