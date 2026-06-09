"""Integration tests for the ``llm4ad evolve`` CLI subcommand group."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm4ad.frontend.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    """``stdout`` is the JSON channel; the CLI prints diagnostics via Rich."""
    return CliRunner()


def _make_pkg(root: Path) -> None:
    """Create a tiny well-formed task package under ``root``."""
    pkg = root / "algo"
    pkg.mkdir(parents=True)
    (pkg / "sort.py").write_text(
        textwrap.dedent(
            """\
            def sort(xs):
                # EVOLVE_START
                return sorted(xs)
                # EVOLVE_END
            """
        ),
        encoding="utf-8",
    )


def _make_nested(root: Path) -> None:
    """Create a file with malformed (nested) markers."""
    (root / "bad.py").write_text(
        textwrap.dedent(
            """\
            # EVOLVE_START outer
            x = 1
            # EVOLVE_START inner
            y = 2
            # EVOLVE_END
            # EVOLVE_END
            """
        ),
        encoding="utf-8",
    )


class TestEvolveCheck:
    """``llm4ad evolve check`` end-to-end."""

    def test_healthy_package_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        """A clean package exits 0 and prints the OK summary."""
        _make_pkg(tmp_path)
        result = runner.invoke(app, ["evolve", "check", str(tmp_path)])
        assert result.exit_code == 0
        assert "OK" in result.stdout

    def test_json_output_is_parseable(self, runner: CliRunner, tmp_path: Path) -> None:
        """`--json` emits a parseable payload with active_block_id and per-block flag."""
        _make_pkg(tmp_path)
        result = runner.invoke(app, ["evolve", "check", str(tmp_path), "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["summary"]["blocks"] == 1
        assert payload["summary"]["active_block_id"] == "algo/sort.py#2-4"
        block = payload["files"][0]["blocks"][0]
        assert block["block_id"] == "algo/sort.py#2-4"
        assert block["active"] is True

    def test_active_marker_in_human_output(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """The Rich table prints a star next to the active block."""
        _make_pkg(tmp_path)
        result = runner.invoke(app, ["evolve", "check", str(tmp_path)])
        assert result.exit_code == 0
        # `*` is ASCII-safe across Windows code pages; the active block_id
        # appears in the summary's "Active block" row.
        assert "algo/sort.py#2-4" in result.stdout

    def test_nested_exits_one_with_issue(self, runner: CliRunner, tmp_path: Path) -> None:
        """Nested markers cause exit 1 and a 'nested' issue in the JSON output."""
        _make_nested(tmp_path)
        result = runner.invoke(app, ["evolve", "check", str(tmp_path), "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        kinds = [i["kind"] for f in payload["files"] for i in f["issues"]]
        assert "nested" in kinds

    def test_missing_path_returns_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """A missing path exits 1 and surfaces 'error' in the summary."""
        result = runner.invoke(
            app, ["evolve", "check", str(tmp_path / "missing"), "--json"]
        )
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert "error" in payload["summary"]


class TestEvolveClean:
    """``llm4ad evolve clean`` end-to-end."""

    def test_dry_run_does_not_modify(self, runner: CliRunner, tmp_path: Path) -> None:
        """Default invocation reports the plan but leaves files untouched."""
        _make_pkg(tmp_path)
        before = (tmp_path / "algo" / "sort.py").read_text(encoding="utf-8")
        result = runner.invoke(app, ["evolve", "clean", str(tmp_path), "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["applied"] is False
        assert payload["summary"]["files_changed"] == 1
        assert payload["summary"]["lines_removed"] == 2
        # Disk untouched.
        after = (tmp_path / "algo" / "sort.py").read_text(encoding="utf-8")
        assert before == after

    def test_apply_writes_files(self, runner: CliRunner, tmp_path: Path) -> None:
        """`--apply` writes the stripped content to disk."""
        _make_pkg(tmp_path)
        result = runner.invoke(
            app, ["evolve", "clean", str(tmp_path), "--apply", "--json"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["applied"] is True
        assert payload["files"][0]["written"] is True
        contents = (tmp_path / "algo" / "sort.py").read_text(encoding="utf-8")
        assert "EVOLVE" not in contents
        assert "return sorted(xs)" in contents
