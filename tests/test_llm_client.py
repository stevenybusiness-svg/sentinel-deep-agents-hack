"""Unit tests for LLM client factory and model ID lookup."""
import os
from unittest.mock import patch
import pytest

import sentinel.config as config_module
from sentinel.llm_client import get_async_client, get_model_ids


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset the settings singleton between tests."""
    config_module._settings = None
    yield
    config_module._settings = None


class TestGetAsyncClient:
    def test_default_backend_returns_async_anthropic(self):
        """Unset LLM_BACKEND should return AsyncAnthropic instance."""
        with patch.dict(os.environ, {"LLM_BACKEND": ""}, clear=False):
            os.environ.pop("LLM_BACKEND", None)
            config_module._settings = None
            from anthropic import AsyncAnthropic
            client = get_async_client()
            assert type(client).__name__ == "AsyncAnthropic"

    def test_anthropic_backend_returns_async_anthropic(self):
        """LLM_BACKEND=anthropic returns AsyncAnthropic instance."""
        with patch.dict(os.environ, {"LLM_BACKEND": "anthropic"}):
            config_module._settings = None
            from anthropic import AsyncAnthropic
            client = get_async_client()
            assert type(client).__name__ == "AsyncAnthropic"

    def test_bedrock_backend_returns_async_anthropic_bedrock(self):
        """LLM_BACKEND=bedrock returns AsyncAnthropicBedrock instance."""
        with patch.dict(os.environ, {
            "LLM_BACKEND": "bedrock",
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
        }):
            config_module._settings = None
            client = get_async_client()
            assert type(client).__name__ == "AsyncAnthropicBedrock"

    def test_invalid_backend_raises_value_error(self):
        """Invalid LLM_BACKEND value should raise ValueError."""
        with patch.dict(os.environ, {"LLM_BACKEND": "openai"}):
            config_module._settings = None
            with pytest.raises(ValueError, match="Unknown LLM_BACKEND"):
                get_async_client()


class TestGetModelIds:
    def test_anthropic_model_ids_are_correct_defaults(self):
        """Anthropic backend should return correct default model IDs."""
        with patch.dict(os.environ, {"LLM_BACKEND": "anthropic", "SUPERVISOR_MODEL": "", "AGENT_MODEL": ""}):
            config_module._settings = None
            models = get_model_ids()
            assert models["supervisor"] == "claude-opus-4-6"
            assert models["agent"] == "claude-sonnet-4-6"

    def test_bedrock_model_ids_are_correct_defaults(self):
        """Bedrock backend should return correct default model IDs."""
        with patch.dict(os.environ, {
            "LLM_BACKEND": "bedrock",
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "SUPERVISOR_MODEL": "",
            "AGENT_MODEL": "",
        }):
            config_module._settings = None
            models = get_model_ids()
            assert models["supervisor"] == "us.anthropic.claude-opus-4-5-20251101-v1:0"
            assert models["agent"] == "us.anthropic.claude-sonnet-4-5-20251001-v1:0"

    def test_supervisor_model_env_override(self):
        """SUPERVISOR_MODEL env var overrides backend default."""
        with patch.dict(os.environ, {
            "LLM_BACKEND": "anthropic",
            "SUPERVISOR_MODEL": "claude-custom-supervisor",
            "AGENT_MODEL": "",
        }):
            config_module._settings = None
            models = get_model_ids()
            assert models["supervisor"] == "claude-custom-supervisor"
            assert models["agent"] == "claude-sonnet-4-6"

    def test_agent_model_env_override(self):
        """AGENT_MODEL env var overrides backend default."""
        with patch.dict(os.environ, {
            "LLM_BACKEND": "anthropic",
            "SUPERVISOR_MODEL": "",
            "AGENT_MODEL": "claude-custom-agent",
        }):
            config_module._settings = None
            models = get_model_ids()
            assert models["supervisor"] == "claude-opus-4-6"
            assert models["agent"] == "claude-custom-agent"
