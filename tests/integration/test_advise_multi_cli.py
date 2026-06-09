"""CLI integration tests for advise's --block-id / --all / --code mutual-exclusion gates.

These tests do NOT call a real LLM; they only verify the CLI rejects
invalid combinations before any provider is contacted.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from llm4ad.frontend.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    """Plain CliRunner; we assert on stdout for the red error text."""
    return CliRunner()


class TestAdviseMutexGates:
    """Combinations of --all/--block-id/--code/--file/--range must be mutually exclusive."""

    def test_all_with_code_is_rejected(self, runner: CliRunner, tmp_path) -> None:
        """--all together with --code exits 1 with a helpful message."""
        result = runner.invoke(
            app,
            ["advise", "-g", "x", "-r", str(tmp_path), "--all", "--code", "print(1)"],
        )
        assert result.exit_code == 1
        assert "--all cannot be combined with --code" in result.stdout

    def test_all_with_file_is_rejected(self, runner: CliRunner, tmp_path) -> None:
        """--all together with --file exits 1."""
        result = runner.invoke(
            app,
            ["advise", "-g", "x", "-r", str(tmp_path), "--all", "--file", "a.py"],
        )
        assert result.exit_code == 1
        assert "--all cannot be combined with --file" in result.stdout

    def test_all_with_block_id_is_rejected(self, runner: CliRunner, tmp_path) -> None:
        """--all together with --block-id exits 1."""
        result = runner.invoke(
            app,
            [
                "advise",
                "-g",
                "x",
                "-r",
                str(tmp_path),
                "--all",
                "--block-id",
                "a.py#1-3",
            ],
        )
        assert result.exit_code == 1
        assert "--all cannot be combined with --block-id" in result.stdout

    def test_all_without_repo_is_rejected(self, runner: CliRunner) -> None:
        """--all requires --repo."""
        result = runner.invoke(app, ["advise", "-g", "x", "--all"])
        assert result.exit_code == 1
        assert "--all requires --repo" in result.stdout

    def test_block_id_with_range_is_rejected(self, runner: CliRunner, tmp_path) -> None:
        """--block-id with --range is rejected as ambiguous."""
        result = runner.invoke(
            app,
            [
                "advise",
                "-g",
                "x",
                "-r",
                str(tmp_path),
                "--block-id",
                "a.py#1-3",
                "--range",
                "1:3",
            ],
        )
        assert result.exit_code == 1
        assert "--block-id cannot be combined with --range" in result.stdout

    def test_code_with_repo_is_rejected(self, runner: CliRunner, tmp_path) -> None:
        """--code is mutually exclusive with all repo-side options."""
        result = runner.invoke(
            app,
            ["advise", "-g", "x", "-r", str(tmp_path), "--code", "print(1)"],
        )
        assert result.exit_code == 1
        assert "--code cannot be combined" in result.stdout
