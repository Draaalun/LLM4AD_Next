"""Unit tests for global settings loading and provider merging."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from llm4ad.config.settings import (
    get_default_settings_path,
    load_global_settings,
    load_yaml_with_env_expansion,
    merge_with_global_settings,
)


# ---------------------------------------------------------------------------
# load_yaml_with_env_expansion
# ---------------------------------------------------------------------------


class TestLoadYamlWithEnvExpansion:
    """Tests for the reusable YAML loader with env-var expansion."""

    def test_basic_load(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nnum: 42\n")
        data = load_yaml_with_env_expansion(yaml_file)
        assert data == {"key": "value", "num": 42}

    def test_env_var_expansion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-secret")
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text('api_key: "${TEST_API_KEY}"\n')
        data = load_yaml_with_env_expansion(yaml_file)
        assert data["api_key"] == "sk-secret"

    def test_multiple_env_vars_in_field(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text('url: "http://${HOST}:${PORT}/v1"\n')
        data = load_yaml_with_env_expansion(yaml_file)
        assert data["url"] == "http://localhost:8080/v1"

    def test_missing_env_var_raises(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text('key: "${SURELY_UNDEFINED_VAR_XYZ}"\n')
        with pytest.raises(KeyError, match="SURELY_UNDEFINED_VAR_XYZ"):
            load_yaml_with_env_expansion(yaml_file)

    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")
        data = load_yaml_with_env_expansion(yaml_file)
        assert data == {}


# ---------------------------------------------------------------------------
# get_default_settings_path
# ---------------------------------------------------------------------------


class TestGetDefaultSettingsPath:
    """Tests for settings path resolution."""

    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LLM4AD_SETTINGS_FILE", raising=False)
        path = get_default_settings_path()
        assert path == Path.home() / ".llm4ad" / "settings.yaml"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM4AD_SETTINGS_FILE", "/custom/path/settings.yaml")
        path = get_default_settings_path()
        assert path == Path("/custom/path/settings.yaml")


# ---------------------------------------------------------------------------
# load_global_settings
# ---------------------------------------------------------------------------


class TestLoadGlobalSettings:
    """Tests for global settings file loading."""

    def test_file_not_found_returns_empty(self, tmp_path: Path) -> None:
        data = load_global_settings(path=tmp_path / "nonexistent.yaml")
        assert data == {}

    def test_load_existing_file(self, tmp_path: Path) -> None:
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(
            "providers:\n"
            '  - name: "default"\n'
            '    type: "openai"\n'
            '    model: "gpt-4"\n'
        )
        data = load_global_settings(path=settings_file)
        assert len(data["providers"]) == 1
        assert data["providers"][0]["name"] == "default"
        assert data["providers"][0]["type"] == "openai"

    def test_env_var_expansion_in_settings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MY_API_KEY", "sk-test-123")
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(
            "providers:\n"
            '  - name: "default"\n'
            '    type: "openai"\n'
            '    api_key: "${MY_API_KEY}"\n'
        )
        data = load_global_settings(path=settings_file)
        assert data["providers"][0]["api_key"] == "sk-test-123"

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        settings_file = tmp_path / "bad.yaml"
        settings_file.write_text(":\n  bad yaml: [unterminated")
        with pytest.raises((ValueError, Exception)):
            load_global_settings(path=settings_file)


# ---------------------------------------------------------------------------
# merge_with_global_settings
# ---------------------------------------------------------------------------


class TestMergeWithGlobalSettings:
    """Tests for provider merging logic."""

    def test_name_only_resolved_from_global(self) -> None:
        global_data = {
            "providers": [
                {"name": "planner", "type": "openai", "model": "gpt-4", "api_key": "sk-abc"}
            ]
        }
        task_data = {"providers": [{"name": "planner"}], "project_name": "test"}
        merged = merge_with_global_settings(global_data, task_data)
        assert len(merged["providers"]) == 1
        p = merged["providers"][0]
        assert p["name"] == "planner"
        assert p["type"] == "openai"
        assert p["model"] == "gpt-4"
        assert p["api_key"] == "sk-abc"
        # Non-provider fields untouched
        assert merged["project_name"] == "test"

    def test_task_overrides_global_field(self) -> None:
        global_data = {
            "providers": [
                {"name": "coder", "type": "anthropic", "model": "claude", "temperature": 0.7}
            ]
        }
        task_data = {"providers": [{"name": "coder", "temperature": 0.1}]}
        merged = merge_with_global_settings(global_data, task_data)
        p = merged["providers"][0]
        assert p["temperature"] == 0.1  # task override
        assert p["type"] == "anthropic"  # from global
        assert p["model"] == "claude"  # from global

    def test_no_global_match_passthrough(self) -> None:
        global_data = {"providers": [{"name": "planner", "type": "openai"}]}
        task_data = {
            "providers": [{"name": "local", "type": "mock", "model": "test"}]
        }
        merged = merge_with_global_settings(global_data, task_data)
        p = merged["providers"][0]
        assert p["name"] == "local"
        assert p["type"] == "mock"

    def test_no_providers_in_task(self) -> None:
        global_data = {"providers": [{"name": "planner", "type": "openai"}]}
        task_data = {"project_name": "test"}
        merged = merge_with_global_settings(global_data, task_data)
        assert "providers" not in merged
        assert merged["project_name"] == "test"

    def test_empty_global_providers(self) -> None:
        global_data = {"providers": []}
        task_data = {"providers": [{"name": "x", "type": "mock"}]}
        merged = merge_with_global_settings(global_data, task_data)
        assert merged["providers"] == [{"name": "x", "type": "mock"}]

    def test_empty_global_data(self) -> None:
        task_data = {"providers": [{"name": "x", "type": "mock"}]}
        merged = merge_with_global_settings({}, task_data)
        assert merged == task_data

    def test_multiple_providers_mixed(self) -> None:
        global_data = {
            "providers": [
                {"name": "planner", "type": "openai", "model": "gpt-4"},
                {"name": "coder", "type": "anthropic", "model": "claude"},
            ]
        }
        task_data = {
            "providers": [
                {"name": "planner"},  # fully from global
                {"name": "coder", "temperature": 0.2},  # partial override
                {"name": "local", "type": "mock"},  # no global match
            ]
        }
        merged = merge_with_global_settings(global_data, task_data)
        assert len(merged["providers"]) == 3

        p0 = merged["providers"][0]
        assert p0["type"] == "openai"
        assert p0["model"] == "gpt-4"

        p1 = merged["providers"][1]
        assert p1["type"] == "anthropic"
        assert p1["model"] == "claude"
        assert p1["temperature"] == 0.2

        p2 = merged["providers"][2]
        assert p2["type"] == "mock"

    def test_does_not_mutate_inputs(self) -> None:
        global_data = {
            "providers": [{"name": "p", "type": "openai", "model": "gpt-4"}]
        }
        task_data = {"providers": [{"name": "p", "temperature": 0.5}]}
        # Keep copies
        import copy

        global_copy = copy.deepcopy(global_data)
        task_copy = copy.deepcopy(task_data)
        merge_with_global_settings(global_data, task_data)
        assert global_data == global_copy
        assert task_data == task_copy


# ---------------------------------------------------------------------------
# AppConfig integration
# ---------------------------------------------------------------------------


class TestAppConfigWithGlobalSettings:
    """Tests for AppConfig.from_yaml with global settings merging."""

    def test_from_yaml_merges_global(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from llm4ad.config.schema import AppConfig

        # Write global settings
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(
            "providers:\n"
            '  - name: "default"\n'
            '    type: "mock"\n'
            '    model: "mock-model"\n'
        )
        monkeypatch.setenv("LLM4AD_SETTINGS_FILE", str(settings_file))

        # Write task config with provider name only
        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            'project_name: "test-project"\n'
            "providers:\n"
            '  - name: "default"\n'
            "evaluator:\n"
            '  type: "custom"\n'
        )
        config = AppConfig.from_yaml(str(task_file))
        assert len(config.providers) == 1
        assert config.providers[0].name == "default"
        assert config.providers[0].type == "mock"
        assert config.providers[0].model == "mock-model"

    def test_from_yaml_without_global(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from llm4ad.config.schema import AppConfig

        # Point to nonexistent settings so global is empty
        monkeypatch.setenv("LLM4AD_SETTINGS_FILE", str(tmp_path / "nope.yaml"))

        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            'project_name: "test"\n'
            "providers:\n"
            '  - name: "default"\n'
            '    type: "mock"\n'
            '    model: "m"\n'
        )
        config = AppConfig.from_yaml(str(task_file))
        assert config.providers[0].type == "mock"

    def test_from_yaml_skip_global(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from llm4ad.config.schema import AppConfig

        # Even with global settings, use_global_settings=False should skip
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(
            "providers:\n"
            '  - name: "default"\n'
            '    type: "mock"\n'
            '    model: "from-global"\n'
        )
        monkeypatch.setenv("LLM4AD_SETTINGS_FILE", str(settings_file))

        task_file = tmp_path / "task.yaml"
        task_file.write_text(
            'project_name: "test"\n'
            "providers:\n"
            '  - name: "default"\n'
            '    type: "openai"\n'
            '    model: "from-task"\n'
        )
        config = AppConfig.from_yaml(str(task_file), use_global_settings=False)
        assert config.providers[0].model == "from-task"
