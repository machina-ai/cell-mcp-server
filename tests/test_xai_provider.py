"""Tests for X.AI provider implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.shared import ProviderType
from providers.xai import XAIModelProvider


class TestXAIProvider:
    """Test X.AI provider functionality."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    @patch.dict(os.environ, {"XAI_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization."""
        provider = XAIModelProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.XAI
        assert provider.base_url == "https://api.x.ai/v1"

    def test_initialization_with_custom_url(self):
        """Test provider initialization with custom base URL."""
        provider = XAIModelProvider("test-key", base_url="https://custom.x.ai/v1")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://custom.x.ai/v1"

    def test_model_validation(self):
        """Test model name validation."""
        provider = XAIModelProvider("test-key")

        # Test valid models
        assert provider.validate_model_name("grok-4.5") is True
        assert provider.validate_model_name("grok4.5") is True
        assert provider.validate_model_name("grok-4.3") is True
        assert provider.validate_model_name("grok-4.3-low") is True
        assert provider.validate_model_name("grok-4.3-none") is True
        assert provider.validate_model_name("grok") is True
        assert provider.validate_model_name("fast") is True
        assert provider.validate_model_name("non-reasoning") is True

        # Test invalid model
        assert provider.validate_model_name("invalid-model") is False
        assert provider.validate_model_name("gpt-4") is False
        assert provider.validate_model_name("gemini-pro") is False

    def test_resolve_model_name(self):
        """Test model name resolution."""
        provider = XAIModelProvider("test-key")

        # Test shorthand resolution
        assert provider._resolve_model_name("grok") == "grok-4.3"
        assert provider._resolve_model_name("grok4.5") == "grok-4.5"
        assert provider._resolve_model_name("fast") == "grok-4.3-low"
        assert provider._resolve_model_name("grok4.1f") == "grok-4.3-low"
        assert provider._resolve_model_name("non-reasoning") == "grok-4.3-none"

        # Test full name passthrough
        assert provider._resolve_model_name("grok-4.5") == "grok-4.5"
        assert provider._resolve_model_name("grok-4.3") == "grok-4.3"
        assert provider._resolve_model_name("grok-4.3-low") == "grok-4.3-low"

    def test_get_capabilities_grok45(self):
        """Test getting model capabilities for GROK-4.5."""
        provider = XAIModelProvider("test-key")

        capabilities = provider.get_capabilities("grok-4.5")
        assert capabilities.model_name == "grok-4.5"
        assert capabilities.friendly_name == "X.AI (Grok 4.5)"
        assert capabilities.context_window == 500_000
        assert capabilities.provider == ProviderType.XAI
        assert capabilities.supports_extended_thinking is True
        assert capabilities.supports_system_prompts is True
        assert capabilities.supports_streaming is True
        assert capabilities.supports_function_calling is True

        # Test temperature range
        assert capabilities.temperature_constraint.min_temp == 0.0
        assert capabilities.temperature_constraint.max_temp == 2.0

    def test_get_capabilities_fast(self):
        """Test getting model capabilities for Grok 4.3 Low Reasoning."""
        provider = XAIModelProvider("test-key")

        capabilities = provider.get_capabilities("grok-4.3-low")
        assert capabilities.model_name == "grok-4.3-low"
        assert capabilities.api_model_name == "grok-4.3"
        assert capabilities.default_reasoning_effort == "low"
        assert capabilities.friendly_name == "X.AI (Grok 4.3 Low Reasoning)"
        assert capabilities.context_window == 1_000_000
        assert capabilities.provider == ProviderType.XAI
        assert capabilities.supports_extended_thinking is True

    def test_get_capabilities_with_shorthand(self):
        """Test getting model capabilities with shorthand."""
        provider = XAIModelProvider("test-key")

        capabilities = provider.get_capabilities("grok")
        assert capabilities.model_name == "grok-4.3"  # Should resolve to grok-4.3
        assert capabilities.context_window == 1_000_000

        capabilities_fast = provider.get_capabilities("fast")
        assert capabilities_fast.model_name == "grok-4.3-low"  # Should resolve to grok-4.3-low
        assert capabilities_fast.context_window == 1_000_000

    def test_unsupported_model_capabilities(self):
        """Test error handling for unsupported models."""
        provider = XAIModelProvider("test-key")

        with pytest.raises(ValueError, match="Unsupported model 'invalid-model' for provider xai"):
            provider.get_capabilities("invalid-model")

    def test_extended_thinking_flags(self):
        """X.AI capabilities should expose extended thinking support correctly."""
        provider = XAIModelProvider("test-key")

        thinking_aliases = ["grok-4.5", "grok", "grok4.5", "fast", "grok-4.3", "grok-4.3-low"]
        for alias in thinking_aliases:
            assert provider.get_capabilities(alias).supports_extended_thinking is True

        non_thinking_aliases = ["grok-4.3-none", "non-reasoning"]
        for alias in non_thinking_aliases:
            assert provider.get_capabilities(alias).supports_extended_thinking is False

    def test_provider_type(self):
        """Test provider type identification."""
        provider = XAIModelProvider("test-key")
        assert provider.get_provider_type() == ProviderType.XAI

    @patch.dict(os.environ, {"XAI_ALLOWED_MODELS": "grok-4.5"})
    def test_model_restrictions(self):
        """Test model restrictions functionality."""
        # Clear cached restriction service
        import utils.model_restrictions
        from providers.registry import ModelProviderRegistry

        utils.model_restrictions._restriction_service = None
        ModelProviderRegistry.reset_for_testing()

        provider = XAIModelProvider("test-key")

        # grok-4.5 should be allowed
        assert provider.validate_model_name("grok-4.5") is True

        # fast should be blocked
        assert provider.validate_model_name("fast") is False
        assert provider.validate_model_name("grok-4.3-low") is False

    @patch.dict(os.environ, {"XAI_ALLOWED_MODELS": "grok,fast"})
    def test_multiple_model_restrictions(self):
        """Test multiple models in restrictions."""
        # Clear cached restriction service
        import utils.model_restrictions
        from providers.registry import ModelProviderRegistry

        utils.model_restrictions._restriction_service = None
        ModelProviderRegistry.reset_for_testing()

        provider = XAIModelProvider("test-key")

        assert provider.validate_model_name("grok") is True
        assert provider.validate_model_name("fast") is True

    @patch.dict(os.environ, {"XAI_ALLOWED_MODELS": ""})
    def test_empty_restrictions_allows_all(self):
        """Test that empty restrictions allow all models."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = XAIModelProvider("test-key")

        assert provider.validate_model_name("grok-4.5") is True
        assert provider.validate_model_name("grok-4.3") is True
        assert provider.validate_model_name("grok-4.3-low") is True
        assert provider.validate_model_name("grok-4.3-none") is True
        assert provider.validate_model_name("grok") is True
        assert provider.validate_model_name("fast") is True

    def test_friendly_name(self):
        """Test friendly name constant."""
        provider = XAIModelProvider("test-key")
        assert provider.FRIENDLY_NAME == "X.AI"

        capabilities = provider.get_capabilities("grok-4.5")
        assert capabilities.friendly_name == "X.AI (Grok 4.5)"

    def test_supported_models_structure(self):
        """Test that MODEL_CAPABILITIES has the correct structure."""
        provider = XAIModelProvider("test-key")

        # Check that all expected base models are present
        assert "grok-4.5" in provider.MODEL_CAPABILITIES
        assert "grok-4.3" in provider.MODEL_CAPABILITIES
        assert "grok-4.3-low" in provider.MODEL_CAPABILITIES

        # Check model configs have required fields
        from providers.shared import ModelCapabilities

        grok45_config = provider.MODEL_CAPABILITIES["grok-4.5"]
        assert isinstance(grok45_config, ModelCapabilities)
        assert grok45_config.context_window == 500_000
        assert grok45_config.supports_extended_thinking is True
        assert "grok4.5" in grok45_config.aliases

        grok43_config = provider.MODEL_CAPABILITIES["grok-4.3"]
        assert isinstance(grok43_config, ModelCapabilities)
        assert grok43_config.context_window == 1_000_000
        assert "grok" in grok43_config.aliases

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_resolves_alias_before_api_call(self, mock_openai_class):
        """Test that generate_content resolves aliases before making API calls."""
        # Set up mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "grok-4.5"
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        provider = XAIModelProvider("test-key")

        result = provider.generate_content(prompt="Test prompt", model_name="grok", temperature=0.7)

        # Verify the API was called with the RESOLVED model name
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]

        assert call_kwargs["model"] == "grok-4.3"
        assert result.content == "Test response"
        assert result.model_name == "grok-4.3"

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_other_aliases(self, mock_openai_class):
        """Test other alias resolutions in generate_content."""
        from unittest.mock import MagicMock

        # Set up mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        provider = XAIModelProvider("test-key")

        # Test grok -> grok-4.3
        mock_response.model = "grok-4.3"
        provider.generate_content(prompt="Test", model_name="grok", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "grok-4.3"

        # Test fast -> grok-4.3 (mapped from grok-4.3-low) with reasoning_effort=low
        mock_response.model = "grok-4.3"
        provider.generate_content(prompt="Test", model_name="fast", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "grok-4.3"
        assert call_kwargs["reasoning_effort"] == "low"

        # Test non-reasoning -> grok-4.3 with reasoning_effort=none
        provider.generate_content(prompt="Test", model_name="non-reasoning", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "grok-4.3"
        assert call_kwargs["reasoning_effort"] == "none"
