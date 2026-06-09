"""Demo test: verify AST similarity via CodeBLEU syntax_match + tree-sitter-python.

Environment requirement: tree-sitter-python==0.21.0, tree-sitter>=0.22.0,<0.23.0, codebleu>=0.7.0
Run: pytest tests/test_ast_similarity_demo.py -v
"""

from __future__ import annotations

import importlib
import sys

import pytest

# ---------------------------------------------------------------------------
# 1. Environment check
# ---------------------------------------------------------------------------


def _get_ts_python_version() -> str:
    """Return installed tree-sitter-python version string."""
    try:
        meta = importlib.metadata.version("tree-sitter-python")
        return meta
    except importlib.metadata.PackageNotFoundError:
        return "NOT INSTALLED"


TS_PYTHON_VERSION = _get_ts_python_version()


def test_tree_sitter_python_installed():
    """Verify tree-sitter-python is installed and version == 0.21.x (required by codebleu 0.7)."""
    assert TS_PYTHON_VERSION != "NOT INSTALLED", "tree-sitter-python is not installed"
    major, minor, *_ = TS_PYTHON_VERSION.split(".")
    assert (int(major), int(minor)) == (0, 21), (
        f"Expected tree-sitter-python 0.21.x (required by codebleu ~=0.21), got {TS_PYTHON_VERSION}"
    )
    print(f"\ntree-sitter-python version: {TS_PYTHON_VERSION}")
    print(f"Python version: {sys.version}")


# ---------------------------------------------------------------------------
# 2. Direct codebleu.syntax_match call
# ---------------------------------------------------------------------------


def _calc_syntax_match(left: str, right: str) -> float:
    """Call codebleu.syntax_match.calc_syntax_match directly."""
    syntax_match = importlib.import_module("codebleu.syntax_match")
    score = syntax_match.calc_syntax_match([left], [right], "python")
    return float(score)


# ---------------------------------------------------------------------------
# 3. Reuse the project helper
# ---------------------------------------------------------------------------

from llm4ad.orchestrator.meoh_population import compute_codebleu_similarity  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

# Pair A: identical code
CODE_A1 = """\
def solve(nodes):
    n = len(nodes)
    visited = [False] * n
    tour = [0]
    visited[0] = True
    for _ in range(n - 1):
        last = tour[-1]
        nearest = min(
            (i for i in range(n) if not visited[i]),
            key=lambda i: (nodes[last][0] - nodes[i][0]) ** 2
                        + (nodes[last][1] - nodes[i][1]) ** 2,
        )
        tour.append(nearest)
        visited[nearest] = True
    return tour
"""

CODE_A2 = CODE_A1  # exact copy


# Pair B: structurally similar (same algorithm, minor variable rename)
CODE_B1 = CODE_A1

CODE_B2 = """\
def solve(cities):
    n = len(cities)
    seen = [False] * n
    path = [0]
    seen[0] = True
    for _ in range(n - 1):
        current = path[-1]
        closest = min(
            (j for j in range(n) if not seen[j]),
            key=lambda j: (cities[current][0] - cities[j][0]) ** 2
                        + (cities[current][1] - cities[j][1]) ** 2,
        )
        path.append(closest)
        seen[closest] = True
    return path
"""


# Pair C: structurally different (greedy nearest-neighbor vs random shuffle)
CODE_C1 = CODE_A1

CODE_C2 = """\
import random

def solve(nodes):
    n = len(nodes)
    tour = list(range(n))
    random.shuffle(tour)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                old = _dist(nodes, tour, i, j)
                tour[i:j+1] = reversed(tour[i:j+1])
                new = _dist(nodes, tour, i, j)
                if new < old:
                    improved = True
                else:
                    tour[i:j+1] = reversed(tour[i:j+1])
    return tour

def _dist(nodes, tour, i, j):
    a, b = nodes[tour[i-1]], nodes[tour[i]]
    c, d = nodes[tour[j]], nodes[tour[(j+1) % len(tour)]]
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) + ((c[0]-d[0])**2 + (c[1]-d[1])**2)
"""


def _codebleu_syntax_match_works() -> bool:
    """Check if codebleu.syntax_match works without tree-sitter compat issues."""
    try:
        syntax_match = importlib.import_module("codebleu.syntax_match")
        syntax_match.calc_syntax_match(["def f(): pass"], ["def f(): pass"], "python")
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _codebleu_syntax_match_works(),
    reason="codebleu.syntax_match has tree-sitter compatibility issue",
)
class TestASTSimilarityDirect:
    """Test codebleu.syntax_match directly (no project wrapper)."""

    def test_identical_code(self):
        """Identical code should have similarity = 1.0."""
        score = _calc_syntax_match(CODE_A1, CODE_A2)
        print(f"\n[Direct] identical: {score:.4f}")
        assert score == pytest.approx(1.0), f"Expected 1.0 for identical code, got {score}"

    def test_similar_code(self):
        """Variable-renamed code should have high similarity (> 0.5)."""
        score = _calc_syntax_match(CODE_B1, CODE_B2)
        print(f"\n[Direct] similar (renamed vars): {score:.4f}")
        assert score > 0.5, f"Expected > 0.5 for similar code, got {score}"

    def test_different_code(self):
        """Structurally different code should have lower similarity."""
        score = _calc_syntax_match(CODE_C1, CODE_C2)
        print(f"\n[Direct] different algorithms: {score:.4f}")
        # Just verify it runs and returns a valid float in [0, 1]
        assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_similar_greater_than_different(self):
        """Similar code should score higher than structurally different code."""
        sim_score = _calc_syntax_match(CODE_B1, CODE_B2)
        diff_score = _calc_syntax_match(CODE_C1, CODE_C2)
        print(f"\n[Direct] similar={sim_score:.4f}  different={diff_score:.4f}")
        assert sim_score > diff_score, (
            f"Similar ({sim_score:.4f}) should be > different ({diff_score:.4f})"
        )


class TestASTSimilarityProjectHelper:
    """Test compute_codebleu_similarity from meoh_population.py."""

    def test_empty_strings(self):
        """Empty input should return 0.0."""
        assert compute_codebleu_similarity("", "") == 0.0
        assert compute_codebleu_similarity("def f(): pass", "") == 0.0
        assert compute_codebleu_similarity("", "def f(): pass") == 0.0

    def test_identical(self):
        """Project helper should return 1.0 for identical code."""
        score = compute_codebleu_similarity(CODE_A1, CODE_A2)
        print(f"\n[Helper] identical: {score:.4f}")
        assert score == pytest.approx(1.0)

    def test_similar(self):
        """Project helper should return high score for similar code."""
        score = compute_codebleu_similarity(CODE_B1, CODE_B2)
        print(f"\n[Helper] similar: {score:.4f}")
        assert score > 0.5

    def test_different(self):
        """Project helper should return lower score for different code."""
        score = compute_codebleu_similarity(CODE_C1, CODE_C2)
        print(f"\n[Helper] different: {score:.4f}")
        assert 0.0 <= score <= 1.0

    def test_ordering(self):
        """Similar > different in project helper too."""
        sim = compute_codebleu_similarity(CODE_B1, CODE_B2)
        diff = compute_codebleu_similarity(CODE_C1, CODE_C2)
        print(f"\n[Helper] similar={sim:.4f}  different={diff:.4f}")
        assert sim > diff
