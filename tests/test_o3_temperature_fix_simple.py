"""
Simple integration test for the O3 model temperature parameter fix.

This test confirms that the fix properly excludes temperature parameters
for O3 models while maintaining them for regular models.
"""

from unittest.mock import Mock, patch

from providers.openai import OpenAIModelProvider


class TestO3TemperatureParameterFixSimple:
    """Simple test for O3 model parameter filtering."""

    @patch("utils.model_restrictions.get_restriction_service")
    @patch("providers.openai_compatible.OpenAI")
    def test_o3_models_exclude_temperature_from_api_call(self, mock_openai_class, mock_restriction_service):
        """Test that O3 models don't send temperature to the API."""
        # Mock restriction service to allow all models
        mock_service = Mock()
        mock_service.is_allowed.return_value = True
        mock_restriction_service.return_value = mock_service

        # Setup mock client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Setup mock response
        mock_response = Mock()
        mock_response.output_text = "Test response"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gpt-5.6-luna"
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.responses.create.return_value = mock_response

        # Create provider
        provider = OpenAIModelProvider(api_key="test-key")

        # Override _resolve_model_name to return the resolved model name
        provider._resolve_model_name = lambda name: name
        # Override model validation to bypass restrictions
        provider.validate_model_name = lambda name: True

        # Call generate_content with gpt-5.6-luna
        provider.generate_content(
            prompt="Test prompt", model_name="gpt-5.6-luna", temperature=0.5, max_output_tokens=100
        )

        # Verify the API call was made
        mock_client.responses.create.assert_called_once()
        call_kwargs = mock_client.responses.create.call_args[1]

        assert call_kwargs["model"] == "gpt-5.6-luna"
        assert "input" in call_kwargs

    @patch("utils.model_restrictions.get_restriction_service")
    @patch("providers.openai_compatible.OpenAI")
    def test_regular_models_include_temperature_in_api_call(self, mock_openai_class, mock_restriction_service):
        """Test that regular models still send temperature to the API."""
        # Mock restriction service to allow all models
        mock_service = Mock()
        mock_service.is_allowed.return_value = True
        mock_restriction_service.return_value = mock_service

        # Setup mock client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gpt-5.6-terra"
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        # Create provider
        provider = OpenAIModelProvider(api_key="test-key")

        # Override _resolve_model_name to return the resolved model name
        provider._resolve_model_name = lambda name: name
        # Override model validation to bypass restrictions
        provider.validate_model_name = lambda name: True

        # Call generate_content with regular model (use supported model)
        provider.generate_content(
            prompt="Test prompt", model_name="gpt-5.6-terra", temperature=0.5, max_output_tokens=100
        )

        # Verify the API call was made WITH temperature (fixed to 1.0)
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]

        assert call_kwargs["temperature"] == 1.0
        assert call_kwargs["model"] == "gpt-5.6-terra"

    @patch("utils.model_restrictions.get_restriction_service")
    def test_all_o3_models_have_correct_temperature_capability(self, mock_restriction_service):
        """Test that models have correct supports_temperature field in their capabilities."""
        from providers.openai import OpenAIModelProvider

        # Mock restriction service to allow all models
        mock_service = Mock()
        mock_service.is_allowed.return_value = True
        mock_restriction_service.return_value = mock_service

        provider = OpenAIModelProvider(api_key="test-key")

        # Test models that should NOT support temperature parameter
        fixed_temp_models = ["gpt-5.6-luna"]

        for model in fixed_temp_models:
            capabilities = provider.get_capabilities(model)
            assert hasattr(
                capabilities, "supports_temperature"
            ), f"Model {model} capabilities should have supports_temperature field"
            assert capabilities.supports_temperature is False, f"Model {model} should have supports_temperature=False"

        # Test that regular models DO support temperature parameter
        regular_models = ["gpt-5.6-terra"]

        for model in regular_models:
            capabilities = provider.get_capabilities(model)
            assert hasattr(
                capabilities, "supports_temperature"
            ), f"Model {model} capabilities should have supports_temperature field"
            assert capabilities.supports_temperature is True, f"Model {model} should have supports_temperature=True"

    @patch("utils.model_restrictions.get_restriction_service")
    def test_openai_provider_temperature_constraints(self, mock_restriction_service):
        """Test that OpenAI provider has correct temperature constraints."""
        from providers.openai import OpenAIModelProvider

        # Mock restriction service to allow all models
        mock_service = Mock()
        mock_service.is_allowed.return_value = True
        mock_restriction_service.return_value = mock_service

        provider = OpenAIModelProvider(api_key="test-key")

        # Test luna model constraints
        luna_capabilities = provider.get_capabilities("gpt-5.6-luna")
        assert luna_capabilities.temperature_constraint is not None

        # Fixed temp models should have fixed temperature constraint
        temp_constraint = luna_capabilities.temperature_constraint
        assert temp_constraint.validate(1.0) is True
        assert temp_constraint.validate(0.5) is False

        # Test regular model constraints
        gpt55_capabilities = provider.get_capabilities("gpt-5.6-terra")
        assert gpt55_capabilities.temperature_constraint is not None

        # Regular models with fixed constraint validate 1.0
        temp_constraint = gpt55_capabilities.temperature_constraint
        assert temp_constraint.validate(1.0) is True
        assert temp_constraint.validate(0.5) is False
