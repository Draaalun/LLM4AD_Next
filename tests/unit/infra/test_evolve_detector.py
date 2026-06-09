"""Unit tests for the EvolveDetector class."""

import os
import textwrap

import pytest

from llm4ad.infra.repo_analyzer.evolve_detector import EvolveDetector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def detector() -> EvolveDetector:
    """Create a default EvolveDetector with standard configuration."""
    return EvolveDetector({})


@pytest.fixture()
def detector_with_context() -> EvolveDetector:
    """Create an EvolveDetector with 3 lines of context."""
    return EvolveDetector(
        {"context_lines_before": 3, "context_lines_after": 3}
    )


# ---------------------------------------------------------------------------
# Helper to create test files
# ---------------------------------------------------------------------------


def _write_file(path, content: str) -> None:
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ===========================================================================
# Tests for _classify_marker_line
# ===========================================================================


class TestClassifyMarkerLine:
    """Tests for the _classify_marker_line static method."""

    def test_python_start(self) -> None:
        """Test Python hash-comment START marker detection."""
        assert EvolveDetector._classify_marker_line("# EVOLVE_START") == "START"

    def test_python_end(self) -> None:
        """Test Python hash-comment END marker detection."""
        assert EvolveDetector._classify_marker_line("# EVOLVE_END") == "END"

    def test_cpp_start(self) -> None:
        """Test C++ double-slash START marker detection."""
        assert EvolveDetector._classify_marker_line("// EVOLVE_START") == "START"

    def test_cpp_end(self) -> None:
        """Test C++ double-slash END marker detection."""
        assert EvolveDetector._classify_marker_line("// EVOLVE_END") == "END"

    def test_block_comment_start(self) -> None:
        """Test C-style block comment START marker detection."""
        assert EvolveDetector._classify_marker_line("/* EVOLVE_START */") == "START"

    def test_block_comment_end(self) -> None:
        """Test C-style block comment END marker detection."""
        assert EvolveDetector._classify_marker_line("/* EVOLVE_END */") == "END"

    def test_html_start(self) -> None:
        """Test HTML comment START marker detection."""
        assert EvolveDetector._classify_marker_line("<!-- EVOLVE_START -->") == "START"

    def test_html_end(self) -> None:
        """Test HTML comment END marker detection."""
        assert EvolveDetector._classify_marker_line("<!-- EVOLVE_END -->") == "END"

    def test_hyphen_separator(self) -> None:
        """Test detection with hyphen as separator between EVOLVE and START/END."""
        assert EvolveDetector._classify_marker_line("# EVOLVE-START") == "START"
        assert EvolveDetector._classify_marker_line("# EVOLVE-END") == "END"

    def test_space_separator(self) -> None:
        """Test detection with space as separator between EVOLVE and START/END."""
        assert EvolveDetector._classify_marker_line("# EVOLVE START") == "START"
        assert EvolveDetector._classify_marker_line("# EVOLVE END") == "END"

    def test_underscore_separator(self) -> None:
        """Test detection with underscore as separator between EVOLVE and START/END."""
        assert EvolveDetector._classify_marker_line("# EVOLVE_START") == "START"
        assert EvolveDetector._classify_marker_line("# EVOLVE_END") == "END"

    def test_case_insensitive(self) -> None:
        """Test that marker detection is case-insensitive."""
        assert EvolveDetector._classify_marker_line("# evolve_start") == "START"
        assert EvolveDetector._classify_marker_line("# Evolve_End") == "END"
        assert EvolveDetector._classify_marker_line("# EVOLVE_start") == "START"

    def test_with_block_name(self) -> None:
        """Test that a block name after START does not prevent detection."""
        assert (
            EvolveDetector._classify_marker_line("# EVOLVE_START my_block") == "START"
        )

    def test_with_leading_whitespace(self) -> None:
        """Test detection when the line has leading whitespace."""
        assert (
            EvolveDetector._classify_marker_line("    # EVOLVE_START") == "START"
        )

    def test_no_separator(self) -> None:
        """Test that EVOLVESTART without a separator is not detected."""
        assert EvolveDetector._classify_marker_line("# EVOLVESTART") is None

    def test_plain_text(self) -> None:
        """Test that plain text without EVOLVE keyword returns None."""
        assert EvolveDetector._classify_marker_line("some random code") is None

    def test_empty_line(self) -> None:
        """Test that an empty line returns None."""
        assert EvolveDetector._classify_marker_line("") is None

    def test_just_evolve(self) -> None:
        """Test that bare EVOLVE without START/END returns None."""
        assert EvolveDetector._classify_marker_line("# EVOLVE") is None

    def test_evolve_other_keyword(self) -> None:
        """Test that EVOLVE followed by an unrecognized keyword returns None."""
        assert EvolveDetector._classify_marker_line("# EVOLVE_BLOCK") is None

    def test_prose_mention_in_docstring_rejected(self) -> None:
        """Plain prose containing EVOLVE_START is not a marker."""
        assert (
            EvolveDetector._classify_marker_line(
                "The code between EVOLVE_START and EVOLVE_END markers will be"
            )
            is None
        )

    def test_string_literal_with_evolve_start_rejected(self) -> None:
        """A string literal mentioning EVOLVE_START is not a marker."""
        assert (
            EvolveDetector._classify_marker_line('msg = "EVOLVE_START"') is None
        )

    def test_trailing_comment_with_evolve_rejected(self) -> None:
        """A line with code before the comment is not treated as a marker."""
        assert (
            EvolveDetector._classify_marker_line("x = 1  # EVOLVE_START") is None
        )

    def test_no_comment_leader_rejected(self) -> None:
        """A bare EVOLVE_START without any comment leader is not a marker."""
        assert EvolveDetector._classify_marker_line("EVOLVE_START") is None


# ===========================================================================
# Tests for _detect_comment_style
# ===========================================================================


class TestDetectCommentStyle:
    """Tests for the _detect_comment_style static method."""

    def test_python_hash(self) -> None:
        """Test hash comment style detection."""
        assert EvolveDetector._detect_comment_style("# EVOLVE_START") == "#"

    def test_cpp_double_slash(self) -> None:
        """Test double-slash comment style detection."""
        assert EvolveDetector._detect_comment_style("// EVOLVE_START") == "//"

    def test_c_block_comment(self) -> None:
        """Test C-style block comment detection."""
        assert EvolveDetector._detect_comment_style("/* EVOLVE_START */") == "/* */"

    def test_html_comment(self) -> None:
        """Test HTML comment style detection."""
        assert (
            EvolveDetector._detect_comment_style("<!-- EVOLVE_START -->") == "<!-- -->"
        )

    def test_with_leading_whitespace(self) -> None:
        """Test that leading whitespace does not affect comment style detection."""
        assert EvolveDetector._detect_comment_style("    # EVOLVE_START") == "#"
        assert EvolveDetector._detect_comment_style("  // EVOLVE_START") == "//"

    def test_default_hash(self) -> None:
        """Test that lines without a recognizable prefix default to hash."""
        assert EvolveDetector._detect_comment_style("EVOLVE_START") == "#"


# ===========================================================================
# Tests for _extract_block_name
# ===========================================================================


class TestExtractBlockName:
    """Tests for the _extract_block_name static method."""

    def test_simple_name(self) -> None:
        """Test extraction of a simple block name."""
        assert EvolveDetector._extract_block_name("# EVOLVE_START my_block") == "my_block"

    def test_no_name(self) -> None:
        """Test that missing block name returns empty string."""
        assert EvolveDetector._extract_block_name("# EVOLVE_START") == ""

    def test_name_with_block_comment_closer(self) -> None:
        """Test that trailing block-comment closer is stripped from the name."""
        assert (
            EvolveDetector._extract_block_name("/* EVOLVE_START optimizer */")
            == "optimizer"
        )

    def test_name_with_html_closer(self) -> None:
        """Test that trailing HTML comment closer is stripped from the name."""
        assert (
            EvolveDetector._extract_block_name("<!-- EVOLVE_START widget -->")
            == "widget"
        )

    def test_multiword_name(self) -> None:
        """Test extraction of a multi-word block name."""
        assert (
            EvolveDetector._extract_block_name("# EVOLVE_START sort algorithm v2")
            == "sort algorithm v2"
        )

    def test_name_preserves_case(self) -> None:
        """Test that block name case is preserved."""
        assert (
            EvolveDetector._extract_block_name("# EVOLVE_START MyBlock")
            == "MyBlock"
        )


# ===========================================================================
# Tests for _pair_start_end
# ===========================================================================


class TestPairStartEnd:
    """Tests for the _pair_start_end static method."""

    def test_single_pair(self) -> None:
        """Test pairing a single START with a single END."""
        starts = [(5, "start_line")]
        ends = [(10, "end_line")]
        pairs = EvolveDetector._pair_start_end(starts, ends)
        assert len(pairs) == 1
        assert pairs[0] == (5, "start_line", 10, "end_line")

    def test_multiple_pairs(self) -> None:
        """Test pairing multiple sequential START/END markers."""
        starts = [(5, "s1"), (15, "s2")]
        ends = [(10, "e1"), (20, "e2")]
        pairs = EvolveDetector._pair_start_end(starts, ends)
        assert len(pairs) == 2
        assert pairs[0] == (5, "s1", 10, "e1")
        assert pairs[1] == (15, "s2", 20, "e2")

    def test_unmatched_start(self) -> None:
        """Test that a START without a following END is skipped."""
        starts = [(5, "s1"), (15, "s2")]
        ends = [(10, "e1")]
        pairs = EvolveDetector._pair_start_end(starts, ends)
        assert len(pairs) == 1
        assert pairs[0] == (5, "s1", 10, "e1")

    def test_extra_end_before_start(self) -> None:
        """Test that END markers before any START are ignored."""
        starts = [(10, "s1")]
        ends = [(5, "orphan_end"), (15, "e1")]
        pairs = EvolveDetector._pair_start_end(starts, ends)
        assert len(pairs) == 1
        assert pairs[0] == (10, "s1", 15, "e1")

    def test_empty_starts(self) -> None:
        """Test that no starts produces no pairs."""
        pairs = EvolveDetector._pair_start_end([], [(10, "e1")])
        assert pairs == []

    def test_empty_ends(self) -> None:
        """Test that no ends produces no pairs."""
        pairs = EvolveDetector._pair_start_end([(5, "s1")], [])
        assert pairs == []

    def test_both_empty(self) -> None:
        """Test that empty inputs produce no pairs."""
        pairs = EvolveDetector._pair_start_end([], [])
        assert pairs == []


# ===========================================================================
# Tests for analyze_file
# ===========================================================================


class TestAnalyzeFile:
    """Tests for the analyze_file method (line-by-line scanning, no subprocess)."""

    def test_single_python_block(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test detecting a single Python EVOLVE block with name, style, and content."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "main.py"
        _write_file(
            src,
            """\
            import os

            def hello():
                pass

            # EVOLVE_START greeter
            def greet(name):
                return f"Hello, {name}"
            # EVOLVE_END

            if __name__ == "__main__":
                hello()
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        b = blocks[0]
        assert b.block_name == "greeter"
        assert b.comment_style == "#"
        assert b.language == "python"
        assert b.line_start == 6
        assert b.line_end == 9
        assert "def greet(name):" in b.original_content
        assert 'return f"Hello, {name}"' in b.original_content

    def test_cpp_style_block(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test detecting a C++ double-slash EVOLVE block."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "main.cpp"
        _write_file(
            src,
            """\
            #include <iostream>

            // EVOLVE_START sort_func
            void sort(int* arr, int n) {
                // bubble sort
            }
            // EVOLVE_END

            int main() { return 0; }
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].comment_style == "//"
        assert blocks[0].block_name == "sort_func"
        assert "void sort" in blocks[0].original_content

    def test_html_style_block(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test detecting an HTML comment EVOLVE block."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "index.html"
        _write_file(
            src,
            """\
            <html>
            <body>
            <!-- EVOLVE_START widget -->
            <div id="widget">placeholder</div>
            <!-- EVOLVE_END -->
            </body>
            </html>
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].comment_style == "<!-- -->"
        assert blocks[0].block_name == "widget"
        assert "placeholder" in blocks[0].original_content

    def test_c_block_comment_style(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test detecting a C-style block comment EVOLVE block."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "main.c"
        _write_file(
            src,
            """\
            #include <stdio.h>

            /* EVOLVE_START optimizer */
            int optimize(int x) {
                return x * 2;
            }
            /* EVOLVE_END */

            int main() { return 0; }
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].comment_style == "/* */"
        assert blocks[0].block_name == "optimizer"
        assert "return x * 2" in blocks[0].original_content

    def test_multiple_blocks_in_one_file(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test detecting multiple EVOLVE blocks in a single file."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "multi.py"
        _write_file(
            src,
            """\
            # EVOLVE_START block_a
            a = 1
            # EVOLVE_END

            # EVOLVE_START block_b
            b = 2
            # EVOLVE_END
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 2
        assert blocks[0].block_name == "block_a"
        assert blocks[1].block_name == "block_b"
        assert "a = 1" in blocks[0].original_content
        assert "b = 2" in blocks[1].original_content

    def test_case_insensitive_markers(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test that lowercase EVOLVE markers are detected."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "case.py"
        _write_file(
            src,
            """\
            # evolve_start lower
            x = 1
            # evolve_end
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].block_name == "lower"

    def test_hyphen_separator(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test that hyphen-separated EVOLVE markers are detected."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "sep.py"
        _write_file(
            src,
            """\
            # EVOLVE-START dashed
            y = 42
            # EVOLVE-END
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].block_name == "dashed"

    def test_space_separator(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test that space-separated EVOLVE markers are detected."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "space.py"
        _write_file(
            src,
            """\
            # EVOLVE START spaced
            z = 99
            # EVOLVE END
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].block_name == "spaced"

    def test_context_extraction(
        self, tmp_path: object, detector_with_context: EvolveDetector
    ) -> None:
        """Test that before/after context lines are correctly captured."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "ctx.py"
        _write_file(
            src,
            """\
            line1
            line2
            line3
            line4
            line5
            # EVOLVE_START
            target = True
            # EVOLVE_END
            line_after1
            line_after2
            line_after3
            line_after4
            """,
        )

        blocks = detector_with_context.analyze_file(src, tmp)
        assert len(blocks) == 1
        b = blocks[0]
        # context_lines_before=3 should capture lines 3, 4, 5
        assert "line3" in b.context_before
        assert "line4" in b.context_before
        assert "line5" in b.context_before
        assert "line1" not in b.context_before
        # context_lines_after=3 should capture lines after END
        assert "line_after1" in b.context_after
        assert "line_after2" in b.context_after
        assert "line_after3" in b.context_after

    def test_unmatched_start_ignored(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test that a START without a matching END produces no blocks."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "unmatched.py"
        _write_file(
            src,
            """\
            # EVOLVE_START orphan
            x = 1
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 0

    def test_binary_file_skipped(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test that binary files are gracefully skipped without error."""
        tmp = tmp_path  # type: ignore[assignment]
        src = tmp / "binary.py"
        src.write_bytes(b"\x00\x01\x02\xff# EVOLVE_START\n\x00# EVOLVE_END\n")

        blocks = detector.analyze_file(src, tmp)
        assert blocks == []

    def test_relative_path_in_block(
        self, tmp_path: object, detector: EvolveDetector
    ) -> None:
        """Test that the block file_path is relative to the repo root."""
        tmp = tmp_path  # type: ignore[assignment]
        sub = tmp / "src"
        src = sub / "algo.py"
        _write_file(
            src,
            """\
            # EVOLVE_START
            pass
            # EVOLVE_END
            """,
        )

        blocks = detector.analyze_file(src, tmp)
        assert len(blocks) == 1
        assert blocks[0].file_path == os.path.join("src", "algo.py")


# ===========================================================================
# Tests for analyze (full repository scan via grep)
# ===========================================================================


class TestAnalyze:
    """Tests for the full analyze method using grep/rg subprocess."""

    def test_single_file_repo(self, tmp_path: object) -> None:
        """Test analyzing a repo with one file containing one block."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "main.py",
            """\
            # EVOLVE_START algo
            def solve():
                pass
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 1
        assert len(result.evolvable_blocks) == 1
        assert result.evolvable_blocks[0].block_name == "algo"

    def test_multiple_files(self, tmp_path: object) -> None:
        """Test analyzing a repo with blocks spread across multiple files."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "a.py",
            """\
            # EVOLVE_START block_a
            a = 1
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "b.py",
            """\
            # EVOLVE_START block_b
            b = 2
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 2
        assert len(result.evolvable_blocks) == 2
        names = {b.block_name for b in result.evolvable_blocks}
        assert names == {"block_a", "block_b"}

    def test_excludes_git_directory(self, tmp_path: object) -> None:
        """Test that files inside .git/ are excluded from analysis."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / ".git" / "hooks" / "pre-commit.py",
            """\
            # EVOLVE_START should_be_excluded
            pass
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "main.py",
            """\
            # EVOLVE_START included
            pass
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "should_be_excluded" not in names
        assert "included" in names

    def test_excludes_node_modules(self, tmp_path: object) -> None:
        """Test that files inside node_modules/ are excluded from analysis."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "node_modules" / "pkg" / "index.js",
            """\
            // EVOLVE_START excluded
            var x = 1;
            // EVOLVE_END
            """,
        )
        _write_file(
            tmp / "app.js",
            """\
            // EVOLVE_START included
            var y = 2;
            // EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "excluded" not in names
        assert "included" in names

    def test_excludes_pycache(self, tmp_path: object) -> None:
        """Test that files inside __pycache__/ are excluded from analysis."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "__pycache__" / "mod.py",
            """\
            # EVOLVE_START cached
            pass
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "real.py",
            """\
            # EVOLVE_START real
            pass
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "cached" not in names
        assert "real" in names

    def test_excludes_venv(self, tmp_path: object) -> None:
        """Test that files inside .venv/ are excluded from analysis."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / ".venv" / "lib" / "site.py",
            """\
            # EVOLVE_START venv_file
            pass
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "app.py",
            """\
            # EVOLVE_START app_file
            pass
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "venv_file" not in names
        assert "app_file" in names

    def test_include_filters(self, tmp_path: object) -> None:
        """Test that non-included file extensions are ignored."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "notes.txt",
            """\
            # EVOLVE_START txt_block
            some notes
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "code.py",
            """\
            # EVOLVE_START py_block
            x = 1
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "txt_block" not in names
        assert "py_block" in names

    def test_empty_repo(self, tmp_path: object) -> None:
        """Test analyzing an empty directory."""
        tmp = tmp_path  # type: ignore[assignment]
        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 0
        assert result.evolvable_blocks == []

    def test_no_blocks_in_files(self, tmp_path: object) -> None:
        """Test analyzing files that contain no EVOLVE markers."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "clean.py",
            """\
            def hello():
                print("no blocks here")
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 0
        assert result.evolvable_blocks == []
        assert result.files_analyzed >= 1

    def test_files_analyzed_count(self, tmp_path: object) -> None:
        """Test that files_analyzed reflects all searchable files."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(tmp / "a.py", "x = 1\n")
        _write_file(tmp / "b.py", "y = 2\n")
        _write_file(tmp / "c.py", "z = 3\n")

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert result.files_analyzed >= 3

    def test_file_type_counts(self, tmp_path: object) -> None:
        """Test that file_type_counts correctly tallies file extensions."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(tmp / "a.py", "x = 1\n")
        _write_file(tmp / "b.py", "y = 2\n")
        _write_file(tmp / "c.js", "var z = 3;\n")

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert result.file_type_counts.get(".py", 0) >= 2
        assert result.file_type_counts.get(".js", 0) >= 1

    def test_mixed_comment_styles_across_files(self, tmp_path: object) -> None:
        """Test that different comment styles are detected across file types."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "script.py",
            """\
            # EVOLVE_START py_block
            x = 1
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "app.js",
            """\
            // EVOLVE_START js_block
            var x = 1;
            // EVOLVE_END
            """,
        )
        _write_file(
            tmp / "page.html",
            """\
            <!-- EVOLVE_START html_block -->
            <p>content</p>
            <!-- EVOLVE_END -->
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert len(result.evolvable_blocks) == 3

        style_map = {b.block_name: b.comment_style for b in result.evolvable_blocks}
        assert style_map["py_block"] == "#"
        assert style_map["js_block"] == "//"
        assert style_map["html_block"] == "<!-- -->"

    def test_subdirectory_files(self, tmp_path: object) -> None:
        """Test that files in nested subdirectories are discovered."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "src" / "core" / "algo.py",
            """\
            # EVOLVE_START deep_block
            result = 42
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert len(result.evolvable_blocks) == 1
        b = result.evolvable_blocks[0]
        assert b.block_name == "deep_block"
        assert "src" in b.file_path
        assert "core" in b.file_path

    def test_custom_include_patterns(self, tmp_path: object) -> None:
        """Test that custom include patterns override defaults."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "data.txt",
            """\
            # EVOLVE_START txt_included
            data
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({"include": ["*.txt"]})
        result = detector.analyze(tmp)
        assert len(result.evolvable_blocks) == 1
        assert result.evolvable_blocks[0].block_name == "txt_included"

    def test_custom_exclude_patterns(self, tmp_path: object) -> None:
        """Test that custom exclude patterns filter out matching files."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "keep.py",
            """\
            # EVOLVE_START kept
            pass
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "skip.py",
            """\
            # EVOLVE_START skipped
            pass
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({"exclude": ["skip.py"]})
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "kept" in names
        assert "skipped" not in names

    def test_block_content_accuracy(self, tmp_path: object) -> None:
        """Test that block content contains inner lines but not markers."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "precise.py",
            """\
            # EVOLVE_START
            alpha = 1
            beta = 2
            gamma = 3
            # EVOLVE_END
            """,
        )

        detector = EvolveDetector({})
        result = detector.analyze(tmp)
        assert len(result.evolvable_blocks) == 1
        content = result.evolvable_blocks[0].original_content
        assert "alpha = 1" in content
        assert "beta = 2" in content
        assert "gamma = 3" in content
        # Markers themselves should NOT be in the content
        assert "EVOLVE_START" not in content
        assert "EVOLVE_END" not in content


# ===========================================================================
# Tests for analyze (Python-based scanning)
# ===========================================================================


class TestAnalyzeWithPythonFallback:
    """Tests for the Python-based file scanning approach."""

    @staticmethod
    def _make_detector(config: dict | None = None) -> EvolveDetector:
        """Create an EvolveDetector instance."""
        return EvolveDetector(config or {})

    def test_single_block(self, tmp_path: object) -> None:
        """Test Python fallback detects a single EVOLVE block."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "main.py",
            """\
            # EVOLVE_START algo
            def solve():
                pass
            # EVOLVE_END
            """,
        )

        detector = self._make_detector()
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 1
        assert len(result.evolvable_blocks) == 1
        assert result.evolvable_blocks[0].block_name == "algo"

    def test_excludes_directories(self, tmp_path: object) -> None:
        """Test Python fallback respects exclude patterns."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "node_modules" / "pkg" / "index.js",
            """\
            // EVOLVE_START excluded
            var x = 1;
            // EVOLVE_END
            """,
        )
        _write_file(
            tmp / "app.js",
            """\
            // EVOLVE_START included
            var y = 2;
            // EVOLVE_END
            """,
        )

        detector = self._make_detector()
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "excluded" not in names
        assert "included" in names

    def test_include_filters(self, tmp_path: object) -> None:
        """Test Python fallback respects include patterns."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "notes.txt",
            """\
            # EVOLVE_START txt_block
            data
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "code.py",
            """\
            # EVOLVE_START py_block
            x = 1
            # EVOLVE_END
            """,
        )

        detector = self._make_detector()
        result = detector.analyze(tmp)
        names = {b.block_name for b in result.evolvable_blocks}
        assert "txt_block" not in names
        assert "py_block" in names

    def test_multiple_files_and_blocks(self, tmp_path: object) -> None:
        """Test Python fallback handles multiple files with multiple blocks."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(
            tmp / "a.py",
            """\
            # EVOLVE_START block_a
            a = 1
            # EVOLVE_END
            """,
        )
        _write_file(
            tmp / "b.py",
            """\
            # EVOLVE_START block_b
            b = 2
            # EVOLVE_END
            """,
        )

        detector = self._make_detector()
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 2
        assert len(result.evolvable_blocks) == 2
        names = {b.block_name for b in result.evolvable_blocks}
        assert names == {"block_a", "block_b"}

    def test_empty_repo(self, tmp_path: object) -> None:
        """Test Python fallback on an empty directory."""
        tmp = tmp_path  # type: ignore[assignment]
        detector = self._make_detector()
        result = detector.analyze(tmp)
        assert result.files_with_blocks == 0
        assert result.evolvable_blocks == []

    def test_files_analyzed_count(self, tmp_path: object) -> None:
        """Test Python fallback counts all scanned files."""
        tmp = tmp_path  # type: ignore[assignment]
        _write_file(tmp / "a.py", "x = 1\n")
        _write_file(tmp / "b.py", "y = 2\n")

        detector = self._make_detector()
        result = detector.analyze(tmp)
        assert result.files_analyzed >= 2


# ===========================================================================
# Tests for _detect_language
# ===========================================================================


class TestDetectLanguage:
    """Tests for language detection from file extension."""

    def test_python(self, detector: EvolveDetector, tmp_path: object) -> None:
        """Test that .py maps to python."""
        assert detector._detect_language(tmp_path / "test.py") == "python"  # type: ignore[arg-type]

    def test_cpp(self, detector: EvolveDetector, tmp_path: object) -> None:
        """Test that .cpp maps to cpp."""
        assert detector._detect_language(tmp_path / "test.cpp") == "cpp"  # type: ignore[arg-type]

    def test_javascript(self, detector: EvolveDetector, tmp_path: object) -> None:
        """Test that .js maps to javascript."""
        assert detector._detect_language(tmp_path / "test.js") == "javascript"  # type: ignore[arg-type]

    def test_unknown_extension(self, detector: EvolveDetector, tmp_path: object) -> None:
        """Test that unknown extensions use the extension itself as language."""
        assert detector._detect_language(tmp_path / "test.xyz") == "xyz"  # type: ignore[arg-type]

    def test_custom_language_map(self, tmp_path: object) -> None:
        """Test that custom language_map entries are honored."""
        detector = EvolveDetector({"language_map": {".cbl": "cobol"}})
        assert detector._detect_language(tmp_path / "test.cbl") == "cobol"  # type: ignore[arg-type]


# ===========================================================================
# Tests for context extraction helpers
# ===========================================================================


class TestContextExtraction:
    """Tests for _get_context_before and _get_context_after."""

    def test_context_before_normal(self) -> None:
        """Test extracting context lines before a block in a normal position."""
        detector = EvolveDetector({"context_lines_before": 2})
        lines = ["L1\n", "L2\n", "L3\n", "L4\n", "START\n", "content\n", "END\n"]
        # START is at 1-based line 5
        ctx = detector._get_context_before(lines, 5)
        assert ctx == "L3\nL4\n"

    def test_context_before_at_top(self) -> None:
        """Test context extraction when the block is near the top of the file."""
        detector = EvolveDetector({"context_lines_before": 5})
        lines = ["L1\n", "START\n", "content\n", "END\n"]
        ctx = detector._get_context_before(lines, 2)
        assert ctx == "L1\n"

    def test_context_after_normal(self) -> None:
        """Test extracting context lines after a block in a normal position."""
        detector = EvolveDetector({"context_lines_after": 2})
        lines = ["START\n", "content\n", "END\n", "A1\n", "A2\n", "A3\n"]
        # END is at 1-based line 3
        ctx = detector._get_context_after(lines, 3)
        assert ctx == "A1\nA2\n"

    def test_context_after_at_bottom(self) -> None:
        """Test context extraction when the block is near the end of the file."""
        detector = EvolveDetector({"context_lines_after": 5})
        lines = ["START\n", "content\n", "END\n", "A1\n"]
        ctx = detector._get_context_after(lines, 3)
        assert ctx == "A1\n"

    def test_zero_context(self) -> None:
        """Test that zero context lines produces empty strings."""
        detector = EvolveDetector(
            {"context_lines_before": 0, "context_lines_after": 0}
        )
        lines = ["before\n", "START\n", "content\n", "END\n", "after\n"]
        assert detector._get_context_before(lines, 2) == ""
        assert detector._get_context_after(lines, 4) == ""
