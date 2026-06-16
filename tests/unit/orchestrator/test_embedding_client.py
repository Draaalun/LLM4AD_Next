"""Tests for embedding client configuration."""

from llm4ad.config.app import EmbeddingConfig, TaskSpecificConfig
from llm4ad.orchestrator import embedding_client as embedding_client_module
from llm4ad.orchestrator.embedding_client import EmbeddingClient


class _FakeAsyncOpenAI:
    instances: list["_FakeAsyncOpenAI"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.instances.append(self)


def _patch_async_openai(monkeypatch):
    _FakeAsyncOpenAI.instances = []
    monkeypatch.setattr(embedding_client_module, "AsyncOpenAI", _FakeAsyncOpenAI)
    return _FakeAsyncOpenAI


def test_embedding_config_defaults_timeout_to_sixty_seconds():
    config = EmbeddingConfig()

    assert config.timeout == 60.0


def test_embedding_client_passes_timeout_to_standard_openai_client(monkeypatch):
    fake_openai = _patch_async_openai(monkeypatch)

    EmbeddingClient(
        EmbeddingConfig(
            type="openai_compatible",
            api_key="test-key",
            base_url="http://embedding.example/v1",
            model="embedding-model",
            timeout=45.0,
        )
    )

    assert len(fake_openai.instances) == 1
    assert fake_openai.instances[0].kwargs["timeout"] == 45.0


def test_local_embedding_clients_use_task_timeout_or_global_default(monkeypatch):
    fake_openai = _patch_async_openai(monkeypatch)

    EmbeddingClient(
        EmbeddingConfig(
            type="local",
            timeout=60.0,
            text_config=TaskSpecificConfig(
                api_key="text-key",
                base_url="http://text.example/v1",
                model="text-model",
                timeout=12.0,
            ),
            code_config=TaskSpecificConfig(
                api_key="code-key",
                base_url="http://code.example/v1",
                model="code-model",
            ),
        )
    )

    assert len(fake_openai.instances) == 2
    assert fake_openai.instances[0].kwargs["timeout"] == 12.0
    assert fake_openai.instances[1].kwargs["timeout"] == 60.0
