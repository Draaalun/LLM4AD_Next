"""Tests for advise multi-block fan-out, block-id lookup, and envelope shape."""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path

import pytest

from llm4ad.advisor import (
    AdviseResult,
    AdvisorError,
    advise_block,
    advise_blocks,
    find_block_by_id,
)
from llm4ad.infra.provider.base import GenerationResult


class _FakeProvider:
    """Provider stub that returns canned text and records every prompt."""

    def __init__(self, texts: list[str]):
        self._texts = list(texts)
        self.calls: list[str] = []

    async def generate(self, prompt: str, **kwargs) -> GenerationResult:  # noqa: D401
        """Return the next canned text."""
        self.calls.append(prompt)
        text = self._texts.pop(0) if self._texts else '{"feasibility": "yes"}'
        return GenerationResult(text=text)


class _SequencedProvider:
    """Records concurrent-call peak so we can assert on max_concurrency."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.in_flight = 0
        self.peak = 0
        self.calls: list[str] = []

    async def generate(self, prompt: str, **kwargs) -> GenerationResult:  # noqa: D401
        """Track concurrent in-flight count, then return canned advice."""
        async with self._lock:
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
            self.calls.append(prompt)
        try:
            await asyncio.sleep(0.01)
            return GenerationResult(text='{"feasibility": "yes"}')
        finally:
            async with self._lock:
                self.in_flight -= 1


def _write_block_file(path: Path, body: str = "    return 1") -> None:
    """Create a small Python file with one well-formed EVOLVE block."""
    path.write_text(
        textwrap.dedent(
            f"""\
            def f():
                # EVOLVE_START
            {body}
                # EVOLVE_END
            """
        ),
        encoding="utf-8",
    )


def _write_repo_with_two_blocks(root: Path) -> None:
    """Create a repo with two distinct well-formed EVOLVE blocks."""
    pkg = root / "algo"
    pkg.mkdir(parents=True)
    _write_block_file(pkg / "a.py", body="    return 1")
    _write_block_file(pkg / "b.py", body="    return 2")


def _patch_provider_resolution(monkeypatch: pytest.MonkeyPatch, provider) -> None:
    """Bypass the credential-resolving helper so tests can use a fake provider."""
    import llm4ad.advisor.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "_resolve_provider", lambda **_: provider)


# ---------------------------------------------------------------------------
# find_block_by_id
# ---------------------------------------------------------------------------


def test_find_block_by_id_match(tmp_path: Path):
    """An exact ``rel#start-end`` id matches the corresponding EvolveBlock."""
    _write_block_file(tmp_path / "algo.py")
    block = find_block_by_id(tmp_path, "algo.py#2-4")
    assert block is not None
    assert block.line_start == 2
    assert block.line_end == 4


def test_find_block_by_id_no_match(tmp_path: Path):
    """An id whose range does not match any block returns None."""
    _write_block_file(tmp_path / "algo.py")
    assert find_block_by_id(tmp_path, "algo.py#999-1000") is None


def test_find_block_by_id_malformed_returns_none(tmp_path: Path):
    """Garbage block_id returns None instead of raising."""
    assert find_block_by_id(tmp_path, "no-hash-here") is None
    assert find_block_by_id(tmp_path, "x#abc") is None


# ---------------------------------------------------------------------------
# advise_block envelope shape (single-block path)
# ---------------------------------------------------------------------------


def test_advise_block_returns_envelope_with_single_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Single-block path returns AdviseResult with count==1 and one result."""
    _write_block_file(tmp_path / "algo.py")
    provider = _FakeProvider(['{"feasibility": "yes", "significance": "high"}'])
    _patch_provider_resolution(monkeypatch, provider)

    result: AdviseResult = asyncio.run(
        advise_block("goal", repo_path=tmp_path, lang="en")
    )

    assert result.count == 1
    assert len(result.results) == 1
    assert result.errors == []
    assert result.lang == "en"
    assert result.results[0].feasibility == "yes"
    # Envelope shape is JSON-serializable and stable.
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["count"] == 1
    assert "results" in payload and "errors" in payload


def test_advise_block_with_block_id_resolves_correctly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """--block-id is honoured by advise_block."""
    _write_block_file(tmp_path / "algo.py")
    provider = _FakeProvider(['{"feasibility": "yes"}'])
    _patch_provider_resolution(monkeypatch, provider)

    result = asyncio.run(
        advise_block("goal", repo_path=tmp_path, block_id="algo.py#2-4")
    )
    assert result.count == 1
    # The advisor saw the right block's content.
    assert "return 1" in provider.calls[0]


def test_advise_block_with_unknown_block_id_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An unknown block_id surfaces a clear AdvisorError."""
    _write_block_file(tmp_path / "algo.py")
    _patch_provider_resolution(monkeypatch, _FakeProvider([]))

    with pytest.raises(AdvisorError, match="did not match any EVOLVE block"):
        asyncio.run(
            advise_block("goal", repo_path=tmp_path, block_id="algo.py#100-200")
        )


# ---------------------------------------------------------------------------
# advise_blocks (--all path)
# ---------------------------------------------------------------------------


def test_advise_blocks_resolves_all_well_formed_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """advise_blocks discovers every block in the repo and produces N results."""
    _write_repo_with_two_blocks(tmp_path)
    provider = _FakeProvider(
        ['{"feasibility": "yes"}', '{"feasibility": "partial"}']
    )
    _patch_provider_resolution(monkeypatch, provider)

    result = asyncio.run(advise_blocks("goal", tmp_path, max_concurrency=2))

    assert result.count == 2
    assert len(result.results) == 2
    assert result.errors == []
    feasibilities = sorted(r.feasibility for r in result.results)
    assert feasibilities == ["partial", "yes"]


def test_advise_blocks_skips_files_with_marker_issues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Files containing nested or unbalanced markers are excluded from --all."""
    pkg = tmp_path / "algo"
    pkg.mkdir(parents=True)
    _write_block_file(pkg / "good.py")
    # Nested markers — `evolve check` would flag this file.
    (pkg / "bad.py").write_text(
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
    provider = _FakeProvider(['{"feasibility": "yes"}'])
    _patch_provider_resolution(monkeypatch, provider)

    result = asyncio.run(advise_blocks("goal", tmp_path))

    assert result.count == 1
    assert result.results[0].block_ref is not None
    # Detector keeps OS-native separators in block_ref; normalize for assert.
    assert (
        Path(result.results[0].block_ref["file_path"]).as_posix()
        == "algo/good.py"
    )


def test_advise_blocks_continues_on_per_block_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A failing per-block call is recorded in errors, not raised."""
    _write_repo_with_two_blocks(tmp_path)

    class _PartialProvider:
        def __init__(self):
            self.calls: list[str] = []

        async def generate(self, prompt: str, **kwargs) -> GenerationResult:  # noqa: D401
            """Return success for a.py, raise for b.py."""
            self.calls.append(prompt)
            if "a.py" in prompt:
                return GenerationResult(text='{"feasibility": "yes"}')
            raise RuntimeError("simulated per-block failure")

    _patch_provider_resolution(monkeypatch, _PartialProvider())

    result = asyncio.run(advise_blocks("goal", tmp_path))

    assert result.count == 1
    assert len(result.errors) == 1
    err = result.errors[0]
    assert "b.py" in err["block_id"]
    assert "RuntimeError" in err["error"]


def test_advise_blocks_concurrency_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """``max_concurrency`` caps the number of in-flight LLM calls."""
    _write_repo_with_two_blocks(tmp_path)
    # Add a few more blocks so the cap actually bites.
    for name in ("c", "d", "e"):
        _write_block_file(tmp_path / "algo" / f"{name}.py")
    provider = _SequencedProvider()
    _patch_provider_resolution(monkeypatch, provider)

    result = asyncio.run(advise_blocks("goal", tmp_path, max_concurrency=2))

    assert result.count == 5
    assert provider.peak <= 2


def test_advise_blocks_errors_when_no_well_formed_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An empty repo produces a clear error."""
    pkg = tmp_path / "algo"
    pkg.mkdir(parents=True)
    (pkg / "plain.py").write_text("x = 1\n", encoding="utf-8")
    _patch_provider_resolution(monkeypatch, _FakeProvider([]))

    with pytest.raises(AdvisorError, match="No EVOLVE markers"):
        asyncio.run(advise_blocks("goal", tmp_path))
