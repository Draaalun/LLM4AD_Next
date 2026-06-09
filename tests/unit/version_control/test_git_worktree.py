"""Tests for Git worktree version control implementation."""

import tempfile
import time
from pathlib import Path

import pytest

from llm4ad.infra.version_control.git_worktree import GitWorktreeVersionControl

pytestmark = pytest.mark.unit


def test_git_worktree_initialization():
    """Test that Git worktree version control initializes correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Initialize with empty config
        config = {
            "type": "git_worktree",
            "auto_initialize": True,
            "auto_cleanup": True,
        }

        vc = GitWorktreeVersionControl(config, base_dir)
        result = vc.initialize()

        assert result.success
        assert (base_dir / ".git").exists()
        assert (base_dir / "worktrees").exists()
        # Metadata file only created after first worktree is added
        assert vc._metadata == {}


def test_create_worktree():
    """Test creating a new worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        # Create first worktree
        result = vc.create_worktree("test1")
        assert result.success

        # Check that it exists in list
        worktrees = vc.list_worktrees()
        assert len(worktrees) == 1
        assert worktrees[0].name == "test1"
        assert Path(worktrees[0].path).exists()

        # Check path is correct
        path = vc.get_worktree_path("test1")
        assert path is not None
        assert path.exists()


def test_create_duplicate_worktree_fails():
    """Test that creating a duplicate worktree fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        vc.create_worktree("test1")
        result = vc.create_worktree("test1")

        assert not result.success
        assert "already exists" in result.message


def test_commit_changes():
    """Test committing changes in a worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        # Create worktree
        result = vc.create_worktree("test_commit")
        worktree = result.data.get("worktree")  # Should be set
        assert result.success
        assert worktree is not None

        worktree_path = vc.get_worktree_path("test_commit")
        assert worktree_path is not None

        # Create a file with some content
        test_file = worktree_path / "test.py"
        with open(test_file, "w", encoding='UTF-8') as f:
            f.write("print('hello world')\n")

        # Commit the changes
        commit_result = vc.commit_changes(worktree, "Add test file")
        assert commit_result.success
        assert commit_result.data["changes_committed"]
        assert commit_result.data["commit_hash"] is not None


def test_delete_worktree():
    """Test deleting a worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        # Create and delete
        result = vc.create_worktree("test_delete")
        worktree = result.data.get("worktree")
        assert len(vc.list_worktrees()) == 1
        assert worktree is not None

        result = vc.delete_worktree(worktree, force=True)
        assert result.success
        assert len(vc.list_worktrees()) == 0

        path = vc.get_worktree_path("test_delete")
        assert path is None


def test_lock_unlock_worktree():
    """Test locking and unlocking a worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        vc.create_worktree("test_lock")

        # Lock
        result = vc.lock_worktree("test_lock", "test locking")
        assert result.success

        worktrees = vc.list_worktrees()
        assert worktrees[0].is_locked

        # Unlock
        result = vc.unlock_worktree("test_lock")
        assert result.success

        worktrees = vc.list_worktrees()
        assert not worktrees[0].is_locked


def test_cleanup_old_resources():
    """Test cleanup of old worktrees."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True, "max_worktrees": 2}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        # Create three worktrees, all unlocked
        vc.create_worktree("old1")
        time.sleep(0.1)
        vc.create_worktree("old2")
        time.sleep(0.1)
        vc.create_worktree("new1")

        # Max worktrees is 2, so oldest should be cleaned up
        result = vc.cleanup_old_resources(max_age_days=100, max_worktrees=2)
        assert result.success
        assert result.data["deleted_count"] == 1

        worktrees = vc.list_worktrees()
        assert len(worktrees) == 2
        # Oldest (old1) should be deleted, remaining are old2 and new1
        names = {wt.name for wt in worktrees}
        assert "old2" in names
        assert "new1" in names
        assert "old1" not in names


def test_cleanup_respects_locking():
    """Test that locked worktrees are not cleaned up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        config = {"auto_initialize": True}
        vc = GitWorktreeVersionControl(config, base_dir)
        vc.initialize()

        vc.create_worktree("locked1")
        vc.lock_worktree("locked1", "preserve this")
        time.sleep(0.1)
        vc.create_worktree("locked2")
        vc.lock_worktree("locked2", "preserve this too")
        time.sleep(0.1)
        vc.create_worktree("unlocked1")

        # All are older than 0 days, max_worktrees is 2
        # Only the unlocked one should be deleted if we're over limit
        result = vc.cleanup_old_resources(max_age_days=0, max_worktrees=2)
        assert result.success

        # Both locked should remain, one unlocked deleted
        worktrees = vc.list_worktrees()
        assert len(worktrees) == 2
        names = {wt.name for wt in worktrees}
        assert "locked1" in names
        assert "locked2" in names


def test_find_git_root_in_parent():
    """Test that git root is found when base_dir is not at repo root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Initialize git at root
        root_dir = tmpdir / "root"
        root_dir.mkdir()

        config = {"auto_initialize": True}
        vc_root = GitWorktreeVersionControl(config, root_dir)
        vc_root.initialize()

        # Create VC in a subdirectory - should find git root from parent
        sub_dir = root_dir / "subdir" / "subsubdir"
        vc_sub = GitWorktreeVersionControl(config, sub_dir)

        # Check that it found the existing git repo (using resolve to handle symlinks like /var -> /private/var)
        assert vc_sub._git_root.resolve() == root_dir.resolve()
        assert (vc_sub._git_root / ".git").exists()
