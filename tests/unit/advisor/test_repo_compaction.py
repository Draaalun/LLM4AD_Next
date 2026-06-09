"""Isolated tests for the repo compaction helper used by the recommender."""

from __future__ import annotations

from pathlib import Path

from llm4ad.advisor.recommender import (
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    _collect_files,
    _compact_repo,
    _rank_files,
)


def test_exclude_patterns_respected(tmp_path: Path):
    """Files under common exclude globs are filtered out."""
    (tmp_path / "keep.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.pyc").write_text("", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x", encoding="utf-8")

    files = _collect_files(tmp_path, DEFAULT_INCLUDE, DEFAULT_EXCLUDE)
    assert "keep.py" in files
    assert all("__pycache__" not in f for f in files)
    assert all("node_modules" not in f for f in files)


def test_include_patterns_limit_extensions(tmp_path: Path):
    """Only files whose name matches an include pattern are kept."""
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.md").write_text("", encoding="utf-8")   # excluded: not in includes
    (tmp_path / "c.txt").write_text("", encoding="utf-8")  # excluded
    (tmp_path / "d.cpp").write_text("", encoding="utf-8")

    files = _collect_files(tmp_path, DEFAULT_INCLUDE, DEFAULT_EXCLUDE)
    assert set(files) == {"a.py", "d.cpp"}


def test_ranking_prefers_goal_keyword_and_entrypoint_names(tmp_path: Path):
    """Files matching goal keywords and named entrypoints rank higher."""
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "util.py").write_text("", encoding="utf-8")
    (tmp_path / "algo.py").write_text("", encoding="utf-8")
    (tmp_path / "tsp_solver.py").write_text("", encoding="utf-8")

    ranked = _rank_files(["deep/util.py", "algo.py", "tsp_solver.py"], tmp_path, "minimize TSP tour length")

    # algo.py is a boosted entrypoint; tsp_solver matches 'tsp' keyword — both rank above deep/util.py.
    assert ranked.index("deep/util.py") == len(ranked) - 1


def test_compaction_respects_total_char_budget(tmp_path: Path):
    """Total compacted contents respect max_total_chars."""
    # Big-ish files to exceed a small budget.
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text("x = 1\n" * 200, encoding="utf-8")

    compacted, unreadable = _compact_repo(
        tmp_path,
        goal="unused",
        max_total_chars=800,
        max_file_bytes=200_000,
        include_patterns=DEFAULT_INCLUDE,
        exclude_patterns=DEFAULT_EXCLUDE,
    )
    assert unreadable == []
    # Budget is a soft cap — may be exceeded only by the last chunk's header accounting.
    assert len(compacted.contents) <= 900
    assert compacted.files_shown >= 1


def test_compaction_truncates_oversized_files_to_head(tmp_path: Path):
    """Files above max_file_bytes show a head-only header and marker."""
    big = tmp_path / "huge.py"
    big.write_text("a = 1\n" * 10_000, encoding="utf-8")

    compacted, unreadable = _compact_repo(
        tmp_path,
        goal="unused",
        max_total_chars=100_000,
        max_file_bytes=1_000,   # force the big file into truncated-head mode
        include_patterns=DEFAULT_INCLUDE,
        exclude_patterns=DEFAULT_EXCLUDE,
    )
    assert unreadable == []
    assert "truncated head only" in compacted.contents
    assert "# ...file truncated..." in compacted.contents


def test_compaction_records_unreadable_binary_file(tmp_path: Path):
    """Non-UTF-8 decoding failure is recorded in unreadable, not raised."""
    bad = tmp_path / "bin.py"     # .py so it matches include
    bad.write_bytes(b"\xff\xfe\x00\x00not valid utf-8 \xc3\x28")

    compacted, unreadable = _compact_repo(
        tmp_path,
        goal="unused",
        max_total_chars=10_000,
        max_file_bytes=10_000,
        include_patterns=DEFAULT_INCLUDE,
        exclude_patterns=DEFAULT_EXCLUDE,
    )
    assert "bin.py" in unreadable
    assert "bin.py" not in compacted.contents


def test_compaction_annotates_with_line_numbers(tmp_path: Path):
    """Compaction output includes 1-based line numbers so the LLM can cite ranges."""
    (tmp_path / "algo.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")

    compacted, _ = _compact_repo(
        tmp_path,
        goal="unused",
        max_total_chars=10_000,
        max_file_bytes=10_000,
        include_patterns=DEFAULT_INCLUDE,
        exclude_patterns=DEFAULT_EXCLUDE,
    )
    assert "1  a = 1" in compacted.contents
    assert "2  b = 2" in compacted.contents
    assert "3  c = 3" in compacted.contents
