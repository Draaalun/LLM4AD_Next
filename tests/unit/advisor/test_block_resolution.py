"""Tests for block resolution in the advisor pipeline.

These tests exercise :func:`_resolve_block` without touching the LLM,
covering the four resolution modes: direct block, repo+file+range,
repo-only (sole EVOLVE marker), and raw code.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from llm4ad.advisor.pipeline import AdvisorError, _resolve_block
from llm4ad.infra.repo_analyzer.base import EvolveBlock


def test_direct_evolve_block_is_returned_unchanged():
    """Mode 1: passing evolve_block bypasses all resolution logic."""
    block = EvolveBlock(
        file_path="x.py",
        absolute_path=Path("x.py"),
        line_start=1,
        line_end=2,
        comment_style="#",
        block_name="",
        original_content="pass",
        context_before="",
        context_after="",
        language="python",
    )
    resolved = _resolve_block(
        repo_path=None,
        code=None,
        file_path=None,
        line_range=None,
        evolve_block=block,
    )
    assert resolved is block


def test_repo_with_file_and_range_builds_block(tmp_path: Path):
    """Mode 2: repo + file + range reads the file and constructs a block."""
    src = textwrap.dedent(
        """\
        def a():
            return 1

        def target():
            return 2

        def b():
            return 3
        """
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "algo.py").write_text(src, encoding="utf-8")

    block = _resolve_block(
        repo_path=repo,
        code=None,
        file_path="algo.py",
        line_range=(4, 5),
        evolve_block=None,
    )

    assert block.language == "python"
    assert block.line_start == 4
    assert block.line_end == 5
    assert "def target" in block.original_content
    assert "def a" in block.context_before
    assert "def b" in block.context_after
    assert block.file_path == "algo.py"


def test_repo_without_range_requires_sole_evolve_marker(tmp_path: Path):
    """Mode 3: repo with no EVOLVE markers raises a helpful error."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "algo.py").write_text("def f(): return 1\n", encoding="utf-8")

    with pytest.raises(AdvisorError, match="No EVOLVE markers"):
        _resolve_block(
            repo_path=repo,
            code=None,
            file_path=None,
            line_range=None,
            evolve_block=None,
        )


def test_raw_code_mode_wraps_snippet():
    """Mode 4: a raw snippet becomes a single <snippet>-file block."""
    snippet = "def f():\n    return 42\n"
    block = _resolve_block(
        repo_path=None,
        code=snippet,
        file_path=None,
        line_range=None,
        evolve_block=None,
    )
    assert block.file_path == "<snippet>"
    assert block.line_start == 1
    assert block.line_end >= 2
    assert "return 42" in block.original_content


def test_missing_any_input_raises(tmp_path: Path):
    """No repo, no code, no block ⇒ clear error."""
    with pytest.raises(AdvisorError, match="No block specified"):
        _resolve_block(
            repo_path=None,
            code=None,
            file_path=None,
            line_range=None,
            evolve_block=None,
        )


def test_file_path_without_line_range_is_rejected(tmp_path: Path):
    """file_path and line_range must be supplied together."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "algo.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(AdvisorError, match="must be provided together"):
        _resolve_block(
            repo_path=repo,
            code=None,
            file_path="algo.py",
            line_range=None,
            evolve_block=None,
        )


def test_invalid_line_range_raises(tmp_path: Path):
    """Out-of-bounds line range produces a clear error."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "algo.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(AdvisorError, match="exceeds file length"):
        _resolve_block(
            repo_path=repo,
            code=None,
            file_path="algo.py",
            line_range=(1, 999),
            evolve_block=None,
        )


def test_nonexistent_repo_raises():
    """A repo_path that doesn't exist is an error, not a silent miss."""
    with pytest.raises(AdvisorError, match="repo_path does not exist"):
        _resolve_block(
            repo_path="/definitely/does/not/exist/for/tests",
            code=None,
            file_path=None,
            line_range=None,
            evolve_block=None,
        )
