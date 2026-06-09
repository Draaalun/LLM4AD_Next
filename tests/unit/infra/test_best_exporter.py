"""Tests for :mod:`llm4ad.infra.best_exporter`."""

from __future__ import annotations

import json
import time
from pathlib import Path

from llm4ad.infra.best_exporter import export_best
from llm4ad.infra.version_control.base import WorktreeInfo
from llm4ad.orchestrator.base import EvolutionResult
from llm4ad.planner.base import Algorithm, CodeArtifact, EvaluationResult, InsightType


def _make_individual(
    *,
    score: float,
    worktree_path: Path | None,
    name: str = "candidate",
    code_text: str = "print('hello')\n",
    artifact_path: str = "main.py",
) -> Algorithm:
    """Build a minimally valid Algorithm with optional worktree backing."""
    individual = Algorithm(
        insight_type=InsightType.INITIAL,
        description=f"{name} description",
        name=name,
        generation=3,
        island_id=0,
    )
    individual.code_artifacts = [
        CodeArtifact(
            file_path=artifact_path,
            content=code_text,
            content_mode="full",
        )
    ]
    individual.evaluation = EvaluationResult(
        score=score,
        metrics={"primary": score, "runtime_ms": 12.0},
    )
    if worktree_path is not None:
        worktree_path.mkdir(parents=True, exist_ok=True)
        (worktree_path / artifact_path).write_text(code_text, encoding="utf-8")
        # A nested file to verify the recursive copy.
        (worktree_path / "subpkg").mkdir(exist_ok=True)
        (worktree_path / "subpkg" / "helper.py").write_text(
            "def helper():\n    return 1\n", encoding="utf-8"
        )
        (worktree_path / ".git").mkdir(exist_ok=True)
        (worktree_path / ".git" / "HEAD").write_text(
            "ref: refs/heads/main\n", encoding="utf-8"
        )
        individual.worktree = WorktreeInfo(
            name=f"{name}-wt",
            path=str(worktree_path),
            branch=f"{name}-branch",
            commit_hash="deadbeef",
            created_at=time.time(),
            last_used_at=time.time(),
        )
    return individual


class TestExportBestSingleObjective:
    """Single-best path: one ``code/`` snapshot + metadata.json + summary.txt."""

    def test_writes_code_snapshot_metadata_and_summary(self, tmp_path: Path) -> None:
        """A run with one best individual produces a stable best/ directory."""
        wt_root = tmp_path / "wt-source"
        best_individual = _make_individual(score=12.5, worktree_path=wt_root)
        result = EvolutionResult(
            state="completed",  # type: ignore[arg-type]
            best_individual=best_individual,
            final_generation=3,
            total_evaluations=42,
            duration_seconds=1.23,
        )

        best_dir = tmp_path / "run" / "best"
        export_best(result, best_dir)

        # Code snapshot exists, recursive copy worked.
        assert (best_dir / "code" / "main.py").exists()
        assert (best_dir / "code" / "subpkg" / "helper.py").exists()
        # .git is filtered out by the ignore patterns.
        assert not (best_dir / "code" / ".git").exists()
        # Metadata is JSON and contains key fields.
        meta = json.loads((best_dir / "metadata.json").read_text(encoding="utf-8"))
        assert meta["score"] == 12.5
        assert meta["generation"] == 3
        assert meta["worktree"]["name"] == "candidate-wt"
        assert meta["evaluation"]["metrics"]["primary"] == 12.5
        # Human-readable summary exists.
        summary = (best_dir / "summary.txt").read_text(encoding="utf-8")
        assert "Best score" in summary
        assert "12.5" in summary

    def test_falls_back_to_code_artifacts_when_worktree_missing(
        self, tmp_path: Path
    ) -> None:
        """No worktree → write code_artifacts directly so the user still has the source."""
        best_individual = _make_individual(score=7.0, worktree_path=None)
        # Worktree is None on this individual.
        result = EvolutionResult(
            state="completed",  # type: ignore[arg-type]
            best_individual=best_individual,
            final_generation=1,
            total_evaluations=5,
        )
        best_dir = tmp_path / "run" / "best"

        export_best(result, best_dir)

        assert (best_dir / "code" / "main.py").exists()
        assert "print('hello')" in (best_dir / "code" / "main.py").read_text(
            encoding="utf-8"
        )

    def test_no_best_writes_no_artifact(self, tmp_path: Path) -> None:
        """A failed run with no best leaves best/ empty (no metadata, no code)."""
        result = EvolutionResult(
            state="completed",  # type: ignore[arg-type]
            best_individual=None,
            final_generation=0,
            total_evaluations=0,
        )
        best_dir = tmp_path / "run" / "best"

        export_best(result, best_dir)

        assert best_dir.exists()
        assert not (best_dir / "code").exists()
        assert not (best_dir / "metadata.json").exists()


class TestExportBestMultiObjective:
    """Multi-objective path: ``best/`` plus ``best/pareto/<idx>/`` per archive entry."""

    def test_writes_pareto_subdirs_for_archive(self, tmp_path: Path) -> None:
        """Every archive member gets its own snapshot under best/pareto/."""
        a = _make_individual(
            score=1.0, worktree_path=tmp_path / "a", name="a", code_text="A=1\n"
        )
        b = _make_individual(
            score=2.0, worktree_path=tmp_path / "b", name="b", code_text="B=2\n"
        )
        c = _make_individual(
            score=3.0, worktree_path=tmp_path / "c", name="c", code_text="C=3\n"
        )
        result = EvolutionResult(
            state="completed",  # type: ignore[arg-type]
            best_individual=a,
            final_population=[a, b, c],
            final_generation=5,
            total_evaluations=30,
        )
        best_dir = tmp_path / "run" / "best"

        export_best(result, best_dir)

        # The single best is still emitted at the top level.
        assert (best_dir / "code" / "main.py").exists()
        assert (best_dir / "metadata.json").exists()
        # Every archive member has its own subdir with the correct payload.
        for idx, code_text in enumerate(("A=1\n", "B=2\n", "C=3\n")):
            sub = best_dir / "pareto" / str(idx)
            assert sub.exists(), f"missing {sub}"
            assert (sub / "code" / "main.py").read_text(encoding="utf-8") == code_text
            assert (sub / "metadata.json").exists()
        # Summary mentions the archive size.
        summary = (best_dir / "summary.txt").read_text(encoding="utf-8")
        assert "Pareto archive (3 members)" in summary

    def test_prefers_metadata_archive_when_final_population_empty(
        self, tmp_path: Path
    ) -> None:
        """MEoH also stashes the archive in ``metadata['elitist_archive']``."""
        a = _make_individual(
            score=1.0, worktree_path=tmp_path / "a", name="a", code_text="A\n"
        )
        b = _make_individual(
            score=2.0, worktree_path=tmp_path / "b", name="b", code_text="B\n"
        )
        result = EvolutionResult(
            state="completed",  # type: ignore[arg-type]
            best_individual=a,
            final_population=[],
            final_generation=2,
            total_evaluations=10,
            metadata={"elitist_archive": [a, b]},
        )
        best_dir = tmp_path / "run" / "best"

        export_best(result, best_dir)

        assert (best_dir / "pareto" / "0" / "code" / "main.py").exists()
        assert (best_dir / "pareto" / "1" / "code" / "main.py").exists()


class TestExportBestRobustness:
    """The exporter never raises — failures must only warn and continue."""

    def test_missing_worktree_path_does_not_raise(self, tmp_path: Path) -> None:
        """A worktree pointing at a non-existent path produces a warning, not a crash."""
        ind = _make_individual(score=4.0, worktree_path=None)
        # Forge a worktree pointing at a path we did not create.
        ind.worktree = WorktreeInfo(
            name="ghost",
            path=str(tmp_path / "does-not-exist"),
            branch="ghost",
            commit_hash="0",
            created_at=time.time(),
            last_used_at=time.time(),
        )
        result = EvolutionResult(
            state="completed",  # type: ignore[arg-type]
            best_individual=ind,
            final_generation=1,
            total_evaluations=1,
        )
        best_dir = tmp_path / "run" / "best"

        # Should not raise.
        export_best(result, best_dir)

        # Metadata is still written even though we couldn't snapshot code.
        assert (best_dir / "metadata.json").exists()
