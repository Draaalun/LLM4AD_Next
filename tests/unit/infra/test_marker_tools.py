"""Unit tests for marker validation, stripping, and path-level inspection."""

from __future__ import annotations

import textwrap
from pathlib import Path

from llm4ad.infra.repo_analyzer import (
    BlockSpan,
    classify_marker,
    clean_path,
    inspect_path,
    strip_marker_lines,
    validate_markers,
)

# ---------------------------------------------------------------------------
# classify_marker
# ---------------------------------------------------------------------------


class TestClassifyMarker:
    """Smoke tests; full coverage of classification lives in test_evolve_detector."""

    def test_python_start(self) -> None:
        """`#`-comment START is recognised."""
        assert classify_marker("# EVOLVE_START") == "START"

    def test_python_end(self) -> None:
        """`#`-comment END is recognised."""
        assert classify_marker("# EVOLVE_END") == "END"

    def test_non_marker(self) -> None:
        """Plain code is not a marker."""
        assert classify_marker("x = 1") is None


# ---------------------------------------------------------------------------
# validate_markers
# ---------------------------------------------------------------------------


def _lines(text: str) -> list[str]:
    return textwrap.dedent(text).lstrip("\n").splitlines(keepends=True)


class TestValidateMarkers:
    """Verify stack-based pairing and issue reporting."""

    def test_single_python_block(self) -> None:
        """One well-formed Python block produces one BlockSpan, no issues."""
        lines = _lines(
            """
            x = 1
            # EVOLVE_START
            body
            # EVOLVE_END
            y = 2
            """
        )
        blocks, issues = validate_markers(lines)
        assert issues == []
        assert blocks == [
            BlockSpan(line_start=2, line_end=4, comment_style="#", block_name="")
        ]

    def test_html_block_with_name(self) -> None:
        """HTML-comment markers carry the right comment_style and block_name."""
        lines = _lines(
            """
            <p>before</p>
            <!-- EVOLVE_START region_a -->
            <span></span>
            <!-- EVOLVE_END -->
            """
        )
        blocks, issues = validate_markers(lines)
        assert issues == []
        assert len(blocks) == 1
        assert blocks[0].comment_style == "<!-- -->"
        assert blocks[0].block_name == "region_a"

    def test_multiple_non_overlapping(self) -> None:
        """Sequential non-overlapping blocks are paired in order."""
        lines = _lines(
            """
            # EVOLVE_START a
            1
            # EVOLVE_END
            mid
            # EVOLVE_START b
            2
            # EVOLVE_END
            """
        )
        blocks, issues = validate_markers(lines)
        assert issues == []
        assert [b.block_name for b in blocks] == ["a", "b"]
        assert [(b.line_start, b.line_end) for b in blocks] == [(1, 3), (5, 7)]

    def test_nested_emits_inner_block_and_issue(self) -> None:
        """Nested START is reported with related_line pointing to the outer."""
        lines = _lines(
            """
            # EVOLVE_START outer
            a
            # EVOLVE_START inner
            b
            # EVOLVE_END
            c
            # EVOLVE_END
            """
        )
        blocks, issues = validate_markers(lines)
        # Both blocks recovered (inner pops first, then outer).
        ranges = [(b.line_start, b.line_end) for b in blocks]
        assert (3, 5) in ranges
        assert (1, 7) in ranges
        # A single 'nested' issue for the inner START referring back to outer.
        nested = [i for i in issues if i.kind == "nested"]
        assert len(nested) == 1
        assert nested[0].line == 3
        assert nested[0].related_line == 1

    def test_unbalanced_start_at_eof(self) -> None:
        """A START with no matching END is reported as unbalanced_start."""
        lines = _lines(
            """
            # EVOLVE_START
            x = 1
            """
        )
        blocks, issues = validate_markers(lines)
        assert blocks == []
        assert [i.kind for i in issues] == ["unbalanced_start"]
        assert issues[0].line == 1

    def test_unbalanced_end_at_head(self) -> None:
        """A leading END with no matching START is reported as unbalanced_end."""
        lines = _lines(
            """
            # EVOLVE_END
            x = 1
            """
        )
        blocks, issues = validate_markers(lines)
        assert blocks == []
        assert [i.kind for i in issues] == ["unbalanced_end"]
        assert issues[0].line == 1


# ---------------------------------------------------------------------------
# strip_marker_lines
# ---------------------------------------------------------------------------


class TestStripMarkerLines:
    """Marker lines are removed; body and surrounding context stay."""

    def test_basic_strip(self) -> None:
        """Marker lines are removed; body and surrounding code stay verbatim."""
        content = textwrap.dedent(
            """\
            x = 1
            # EVOLVE_START
            body
            # EVOLVE_END
            y = 2
            """
        )
        new_content, removed = strip_marker_lines(content)
        assert removed == [2, 4]
        assert new_content == "x = 1\nbody\ny = 2\n"

    def test_no_markers(self) -> None:
        """A file without markers is returned unchanged with no removed lines."""
        content = "x = 1\ny = 2\n"
        new_content, removed = strip_marker_lines(content)
        assert removed == []
        assert new_content == content

    def test_strip_keeps_body_for_nested(self) -> None:
        """Nested markers are stripped but their bodies remain."""
        content = textwrap.dedent(
            """\
            # EVOLVE_START outer
            outer_body
            # EVOLVE_START inner
            inner_body
            # EVOLVE_END
            still_outer
            # EVOLVE_END
            """
        )
        new_content, removed = strip_marker_lines(content)
        assert removed == [1, 3, 5, 7]
        assert "outer_body" in new_content
        assert "inner_body" in new_content
        assert "EVOLVE" not in new_content


# ---------------------------------------------------------------------------
# inspect_path / clean_path
# ---------------------------------------------------------------------------


def _build_pkg(root: Path) -> None:
    """Create a tiny task package with a single well-formed block."""
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


class TestInspectPath:
    """High-level walker tests."""

    def test_healthy_package(self, tmp_path: Path) -> None:
        """A package with one valid block reports ok=True and POSIX path."""
        _build_pkg(tmp_path)
        result = inspect_path(tmp_path)
        assert result.ok is True
        assert result.summary["files_scanned"] >= 1
        assert result.summary["blocks"] == 1
        assert result.summary["issues"] == 0
        assert len(result.files) == 1
        f = result.files[0]
        # Path must be POSIX-relative even on Windows.
        assert f.path == "algo/sort.py"
        assert f.blocks[0].line_start == 2
        assert f.blocks[0].line_end == 4

    def test_to_dict_includes_block_id(self, tmp_path: Path) -> None:
        """Each block carries a stable block_id and the active flag."""
        _build_pkg(tmp_path)
        d = inspect_path(tmp_path).to_dict()
        block = d["files"][0]["blocks"][0]
        assert block["block_id"] == "algo/sort.py#2-4"
        assert block["active"] is True
        assert d["summary"]["active_block_id"] == "algo/sort.py#2-4"

    def test_active_is_first_walked_block(self, tmp_path: Path) -> None:
        """Two files each with a block; only the first walked block is active."""
        _build_pkg(tmp_path)
        # Add a second file with its own block. iter_source_files walks via
        # rglob, but for a deterministic assertion we check that exactly one
        # block is flagged active and it equals summary.active_block_id.
        (tmp_path / "algo" / "extra.py").write_text(
            textwrap.dedent(
                """\
                def f():
                    # EVOLVE_START
                    return 1
                    # EVOLVE_END
                """
            ),
            encoding="utf-8",
        )
        result = inspect_path(tmp_path)
        assert result.active_block_id is not None
        active_blocks = [
            b
            for f in result.to_dict()["files"]
            for b in f["blocks"]
            if b["active"]
        ]
        assert len(active_blocks) == 1
        assert active_blocks[0]["block_id"] == result.active_block_id

    def test_no_active_when_no_blocks(self, tmp_path: Path) -> None:
        """No blocks means active_block_id is None in both result and dict."""
        (tmp_path / "plain.py").write_text("x = 1\n", encoding="utf-8")
        result = inspect_path(tmp_path)
        assert result.active_block_id is None
        assert result.to_dict()["summary"]["active_block_id"] is None

    def test_nested_marks_not_ok(self, tmp_path: Path) -> None:
        """Nested markers cause ok=False and surface a 'nested' issue."""
        (tmp_path / "bad.py").write_text(
            textwrap.dedent(
                """\
                # EVOLVE_START a
                # EVOLVE_START b
                pass
                # EVOLVE_END
                # EVOLVE_END
                """
            ),
            encoding="utf-8",
        )
        result = inspect_path(tmp_path)
        assert result.ok is False
        assert result.summary["issues"] == 1
        kinds = [i.kind for i in result.files[0].issues]
        assert "nested" in kinds

    def test_missing_root(self, tmp_path: Path) -> None:
        """A non-existent root yields ok=False with an error in the summary."""
        result = inspect_path(tmp_path / "does_not_exist")
        assert result.ok is False
        assert "error" in result.summary


class TestCleanPath:
    """Dry-run vs apply behaviour."""

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """Without --apply, files are not modified but the plan is reported."""
        _build_pkg(tmp_path)
        before = (tmp_path / "algo" / "sort.py").read_text(encoding="utf-8")
        result = clean_path(tmp_path)  # apply=False default
        after = (tmp_path / "algo" / "sort.py").read_text(encoding="utf-8")
        assert before == after
        assert result.applied is False
        assert result.summary["files_changed"] == 1
        assert result.summary["lines_removed"] == 2
        entry = result.files[0]
        assert entry["written"] is False
        assert entry["removed_lines"] == [2, 4]

    def test_apply_strips_markers(self, tmp_path: Path) -> None:
        """With --apply, marker lines are removed on disk."""
        _build_pkg(tmp_path)
        result = clean_path(tmp_path, apply=True)
        after = (tmp_path / "algo" / "sort.py").read_text(encoding="utf-8")
        assert "EVOLVE" not in after
        assert "return sorted(xs)" in after
        assert result.applied is True
        assert result.files[0]["written"] is True

    def test_clean_skips_files_without_markers(self, tmp_path: Path) -> None:
        """Files without markers are excluded from the clean report."""
        (tmp_path / "plain.py").write_text("x = 1\n", encoding="utf-8")
        result = clean_path(tmp_path, apply=True)
        assert result.summary["files_changed"] == 0
        assert result.files == []
