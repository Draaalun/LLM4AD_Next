"""Tests for Algorithm data model with diff-based storage."""

from llm4ad.planner.base import (
    Algorithm,
    CodeArtifact,
    GenerationMetadata,
    InsightType,
)
from llm4ad.utils.diff_utils import (
    apply_unified_diff,
    generate_unified_diff,
    hash_content,
    parse_diff_stats,
    validate_diff,
)


class TestCodeArtifact:
    """Tests for CodeArtifact."""

    def test_code_constructor(self):
        """Test CodeArtifact construction with default values."""
        artifact = CodeArtifact(
            file_path="test.py",
            content="print('hello')",
        )
        assert artifact.file_path == "test.py"
        assert artifact.content == "print('hello')"
        assert artifact.content_mode == "diff"
        assert artifact.base_commit_hash is None
        assert artifact.base_file_hash is None

    def test_code_artifact_full_mode(self):
        """Test CodeArtifact in full mode."""
        artifact = CodeArtifact(
            file_path="test.py",
            content="def foo():\\n    return 42",
            content_mode="full",
        )
        assert artifact.content_mode == "full"


class TestDiffUtils:
    """Tests for diff utility functions."""

    def test_hash_content(self):
        """Test hash_content produces consistent results."""
        content = "test content"
        hash1 = hash_content(content)
        hash2 = hash_content(content)
        assert len(hash1) == 16
        assert hash1 == hash2

    def test_generate_unified_diff_basic(self):
        """Test generating a simple diff."""
        old = "line 1\nline 2\nline 3\n"
        new = "line 1\nline 2 changed\nline 3\n"
        diff = generate_unified_diff(old, new, "test.txt")
        assert "line 2 changed" in diff
        assert "-line 2" in diff

    def test_apply_unified_diff(self):
        """Test applying a diff works correctly."""
        base = "line 1\nline 2\nline 3\n"
        old = base
        new = "line 1\nline 2 changed\nline 3\n"
        diff = generate_unified_diff(old, new, "test.txt")
        result, success = apply_unified_diff(base, diff)
        assert success
        assert result == new

    def test_validate_diff_correct(self):
        """Test validation passes with correct diff."""
        base = "a\nb\nc\n"
        new = "a\nb changed\nc\n"
        diff = generate_unified_diff(base, new, "test.txt")
        assert validate_diff(base, diff, new) is True

    def test_validate_diff_incorrect(self):
        """Test validation fails with incorrect result."""
        base = "a\nb\nc\n"
        expected = "a\nx changed\nc\n"
        diff = generate_unified_diff(base, "a\nb changed\nc\n", "test.txt")
        assert validate_diff(base, diff, expected) is False

    def test_parse_diff_stats_add(self):
        """Test parsing diff statistics."""
        diff = """--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,4 @@\n line1\n-line2\n+line2 changed\n+line3 added\n line3\n"""
        added, removed, modified = parse_diff_stats(diff)
        # line2 is modified (removed + added) → counts as 1 modified
        # line3 added is a pure addition → counts as 1 added
        # no pure removed lines left
        assert added == 1
        assert removed == 0
        assert modified == 1

    def test_parse_diff_stats_multiple(self):
        """Test parsing multiple changes."""
        diff = """--- a/test.py\n+++ b/test.py\n@@ -1,5 +1,6 @@\n+new line 1\n line 1\n line 2\n line 3\n-line 4\n+line 4 modified\n line 5\n"""
        added, removed, modified = parse_diff_stats(diff)
        # new line 1 is pure addition → 1 added
        # line 4 is modified → removed + added → 1 modified
        # no pure removed lines
        assert added == 1  # only the pure addition at the beginning
        assert removed == 0
        assert modified == 1


class TestAlgorithm:
    """Tests for Algorithm with diff-based storage."""

    def test_algorithm_insight_initial(self):
        """Test creating an initial Algorithm."""
        insight = Algorithm(
            insight_type=InsightType.INITIAL,
            description="Test algorithm description",
        )
        assert insight.id is not None
        assert insight.insight_type == InsightType.INITIAL
        assert insight.lines_added == 0
        assert insight.population_id == ""

    def test_add_code_artifact_adds_to_collection(self):
        """Test adding code artifacts."""
        insight = Algorithm(
            insight_type=InsightType.INITIAL,
            description="Test algorithm",
        )
        insight.add_code_artifact(
            file_path="alg.py",
            content="def sort(arr): return arr",
            is_entrypoint=True,
            content_mode="full",
        )
        assert len(insight.code_artifacts) == 1

    def test_calculate_diff_stats(self):
        """Test calculating diff stats from artifacts."""
        old_content = "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n"
        new_content = "def optimized_bubble_sort(arr):\n    n = len(arr)\n    swapped = True\n    for i in range(n):\n        if not swapped:\n            break\n        swapped = False\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n                swapped = True\n    return arr\n"
        diff = generate_unified_diff(old_content, new_content, "bubble_sort.py")

        insight = Algorithm(
            insight_type=InsightType.MUTATION,
            description="Optimized bubble sort",
            parent_ids=["parent123"],
            generation=1,
        )
        insight.add_code_artifact(
            file_path="bubble_sort.py",
            content=diff,
            is_entrypoint=True,
            content_mode="diff",
        )

        added, removed, modified = insight.calculate_diff_stats()
        assert added > 0
        assert insight.lines_added == added
        assert insight.lines_removed == removed
        assert insight.lines_modified == modified

    def test_resolve_full_content_initial_full(self):
        """Test resolve_full_content on initial full content insight."""
        insight = Algorithm(
            insight_type=InsightType.INITIAL,
            description="Initial algorithm",
        )
        insight.add_code_artifact(
            "test.py", "def hello(): return 42", content_mode="full", is_entrypoint=True
        )
        result = insight.resolve_full_content({})
        assert len(result) == 1
        assert result[0].content_mode == "full"
        assert "hello" in result[0].content

    def test_resolve_full_content_parent_diff(self):
        """Test reconstructing full code from parent diff chain."""
        # Parent (generation 0)
        parent_content = "def sort(arr):\n    return sorted(arr)\n"
        parent = Algorithm(
            id="parent_id",
            insight_type=InsightType.INITIAL,
            description="Parent sort",
            generation=0,
        )
        parent.add_code_artifact(
            "sort.py",
            parent_content,
            is_entrypoint=True,
            content_mode="full",
        )

        # Child with diff - change the function
        child_new_content = "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[0]\n    left = [x for x in arr[1:] if x <= pivot]\n    right = [x for x in arr[1:] if x > pivot]\n    return quicksort(left) + [pivot] + quicksort(right)\n"
        diff = generate_unified_diff(parent_content, child_new_content, "sort.py")

        child = Algorithm(
            insight_type=InsightType.MUTATION,
            description="Quicksort mutation",
            parent_ids=["parent_id"],
            generation=1,
        )
        child.add_code_artifact(
            "sort.py",
            diff,
            is_entrypoint=True,
            content_mode="diff",
            base_file_hash=hash_content(parent_content),
        )

        # Resolve
        parent_map = {"parent_id": parent}
        result_artifacts = child.resolve_full_content(parent_map)

        assert len(result_artifacts) == 1
        assert result_artifacts[0].content_mode == "full"
        assert "quicksort" in result_artifacts[0].content
        assert result_artifacts[0].base_file_hash == hash_content(parent_content)

    def test_resolve_full_content_multiple_generations(self):
        """Test resolving across multiple generations of diffs."""
        # Gen 0: initial
        content0 = "def f(x):\n    return x + 1\n"
        gen0 = Algorithm(
            id="gen0",
            insight_type=InsightType.INITIAL,
            description="Initial f",
            generation=0,
        )
        gen0.add_code_artifact("f.py", content0, content_mode="full")

        # Gen 1: change return x + 2
        content1 = "def f(x):\n    return x + 2\n"
        diff0_1 = generate_unified_diff(content0, content1, "f.py")
        gen1 = Algorithm(
            id="gen1",
            insight_type=InsightType.MUTATION,
            description="Change to +2",
            parent_ids=["gen0"],
            generation=1,
        )
        gen1.add_code_artifact("f.py", diff0_1, content_mode="diff")

        # Gen 2: add docstring
        content2 = 'def f(x):\n    """Add 2 to x."""\n    return x + 2\n'
        diff1_2 = generate_unified_diff(content1, content2, "f.py")
        gen2 = Algorithm(
            id="gen2",
            insight_type=InsightType.MUTATION,
            description="Add docstring",
            parent_ids=["gen1"],
            generation=2,
        )
        gen2.add_code_artifact("f.py", diff1_2, content_mode="diff")

        parent_map = {"gen0": gen0, "gen1": gen1}
        result = gen2.resolve_full_content(parent_map)
        assert len(result) == 1
        assert result[0].content_mode == "full"
        # Check that the final content includes the docstring
        assert '"""' in result[0].content
        assert "Add 2 to x" in result[0].content
        assert "x + 2" in result[0].content

    def test_metadata_provenance(self):
        """Test complete provenance metadata is stored."""
        meta = GenerationMetadata(
            operator="mutation",
            llm_provider="openai",
            llm_model="gpt-4o",
            agent_id="agent-123",
            agent_name="llm-mutator",
            agent_version="1.1",
            change_description="Optimized the swap operation",
            targeted_files=["sorting/quick_sort.py"],
            seed=42,
            code_generator_version="2.0",
        )
        assert meta.agent_id == "agent-123"
        assert meta.agent_name == "llm-mutator"
        assert meta.change_description == "Optimized the swap operation"
        assert "sorting/quick_sort.py" in meta.targeted_files
        assert meta.seed == 42

    def test_backward_compatibility(self):
        """Test that existing fields still work with defaults."""
        # Old style without new fields should still work
        insight = Algorithm(
            insight_type=InsightType.INITIAL,
            description="Old style insight",
            code_artifacts=[
                CodeArtifact(file_path="old.py", content="old code", content_mode="full")
            ],
        )
        assert insight.changed_files == []
        assert insight.lines_added == 0
        assert insight.lines_removed == 0
        assert insight.lines_modified == 0
        assert insight.population_id == ""
        # Check existing methods still work
        assert insight.has_code()
        assert insight.get_code("old.py") == "old code"
