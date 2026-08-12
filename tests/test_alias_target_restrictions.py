"""
Tests for alias and target model restriction validation.

This test suite ensures that the restriction service properly validates
both alias names and their target models, preventing policy bypass vulnerabilities.
"""

import os
from unittest.mock import patch

from providers.gemini import GeminiModelProvider
from providers.openai import OpenAIModelProvider
from providers.shared import ProviderType
from utils.model_restrictions import ModelRestrictionService


class TestAliasTargetRestrictions:
    """Test that restriction validation works for both aliases and their targets."""

    def test_openai_alias_target_validation_comprehensive(self):
        """Test OpenAI provider includes both aliases and targets in validation."""
        provider = OpenAIModelProvider(api_key="test-key")

        # Get all known models including aliases and targets
        all_known = provider.list_models(respect_restrictions=False, include_aliases=True, lowercase=True, unique=True)

        # Should include both aliases and their targets
        assert "luna" in all_known  # alias
        assert "gpt-5.6-luna" in all_known  # target of 'luna'
        assert "terra" in all_known  # alias
        assert "gpt-5.6-terra" in all_known  # target of 'terra'

    def test_gemini_alias_target_validation_comprehensive(self):
        """Test Gemini provider includes both aliases and targets in validation."""
        provider = GeminiModelProvider(api_key="test-key")

        # Get all known models including aliases and targets
        all_known = provider.list_models(respect_restrictions=False, include_aliases=True, lowercase=True, unique=True)

        # Should include both aliases and their targets
        assert "flash" in all_known  # alias
        assert "gemini-3-flash-preview" in all_known  # target of 'flash'
        assert "pro" in all_known  # alias
        assert "gemini-3.1-pro-preview" in all_known  # target of 'pro'

    @patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "gpt-5.6-luna"})  # Allow target
    def test_restriction_policy_allows_alias_when_target_allowed(self):
        """Test that restriction policy allows alias when target model is allowed."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = OpenAIModelProvider(api_key="test-key")

        # Both target and its actual aliases should be allowed
        assert provider.validate_model_name("gpt-5.6-luna")
        assert provider.validate_model_name("luna")

    @patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "luna"})  # Allow alias only
    def test_restriction_policy_alias_allows_canonical(self):
        """Alias-only allowlists should permit both the alias and its canonical target."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = OpenAIModelProvider(api_key="test-key")

        assert provider.validate_model_name("luna")
        assert provider.validate_model_name("gpt-5.6-luna")
        assert not provider.validate_model_name("gpt-5.6-terra")

    @patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "gpt5.6t"})
    def test_restriction_policy_alias_allows_short_name(self):
        """Common aliases like 'gpt5.6t' should allow their canonical forms."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = OpenAIModelProvider(api_key="test-key")

        assert provider.validate_model_name("gpt5.6t")
        assert provider.validate_model_name("gpt-5.6-terra")

    @patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "gemini-3-flash-preview"})  # Allow target
    def test_gemini_restriction_policy_allows_alias_when_target_allowed(self):
        """Test Gemini restriction policy allows alias when target is allowed."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = GeminiModelProvider(api_key="test-key")

        # Both target and alias should be allowed
        assert provider.validate_model_name("gemini-3-flash-preview")
        assert provider.validate_model_name("flash")

    @patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash"})  # Allow alias only
    def test_gemini_restriction_policy_alias_allows_canonical(self):
        """Gemini alias allowlists should permit canonical forms."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = GeminiModelProvider(api_key="test-key")

        assert provider.validate_model_name("flash")
        assert provider.validate_model_name("gemini-3-flash-preview")

    def test_restriction_service_validation_includes_all_targets(self):
        """Test that restriction service validation knows about all aliases and targets."""
        with patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "gpt-5.6-luna,invalid-model"}):
            service = ModelRestrictionService()

            # Create real provider instances
            provider_instances = {ProviderType.OPENAI: OpenAIModelProvider(api_key="test-key")}

            # Capture warnings
            with patch("utils.model_restrictions.logger") as mock_logger:
                service.validate_against_known_models(provider_instances)

                # Should have warned about the invalid model
                warning_calls = [call for call in mock_logger.warning.call_args_list if "invalid-model" in str(call)]
                assert len(warning_calls) > 0, "Should have warned about invalid-model"

                # The warning should include both aliases and targets in known models
                warning_message = str(warning_calls[0])
                assert "luna" in warning_message or "gpt-5.6-luna" in warning_message

    @patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "luna,gpt-5.6-luna,terra,gpt-5.6-terra"})
    def test_both_alias_and_target_allowed_when_both_specified(self):
        """Test that both alias and target work when both are explicitly allowed."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = OpenAIModelProvider(api_key="test-key")

        # All should be allowed since we explicitly allowed them
        assert provider.validate_model_name("luna")
        assert provider.validate_model_name("gpt-5.6-luna")
        assert provider.validate_model_name("terra")
        assert provider.validate_model_name("gpt-5.6-terra")

    @patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "gpt5.6t"}, clear=True)
    def test_service_alias_allows_canonical_openai(self):
        """ModelRestrictionService should permit canonical names resolved from aliases."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        provider = OpenAIModelProvider(api_key="test-key")
        service = ModelRestrictionService()

        assert service.is_allowed(ProviderType.OPENAI, "gpt-5.6-terra")
        assert provider.validate_model_name("gpt-5.6-terra")

    @patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash"}, clear=True)
    def test_service_alias_allows_canonical_gemini(self):
        """Gemini alias allowlists should permit canonical forms."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        provider = GeminiModelProvider(api_key="test-key")
        service = ModelRestrictionService()

        assert service.is_allowed(ProviderType.GOOGLE, "gemini-3-flash-preview")
        assert provider.validate_model_name("gemini-3-flash-preview")

    def test_alias_target_policy_regression_prevention(self):
        """Regression test to ensure aliases and targets are both validated properly.

        This test specifically prevents the bug where list_models() only returned
        aliases but not their targets, causing restriction validation to miss
        deny-list entries for target models.
        """
        # Test OpenAI provider
        openai_provider = OpenAIModelProvider(api_key="test-key")
        openai_all_known = openai_provider.list_models(
            respect_restrictions=False, include_aliases=True, lowercase=True, unique=True
        )

        # Verify that for each alias, its target is also included
        for model_name, config in openai_provider.MODEL_CAPABILITIES.items():
            assert model_name.lower() in openai_all_known
            if isinstance(config, str):  # This is an alias
                # The target should also be in the known models
                assert (
                    config.lower() in openai_all_known
                ), f"Target '{config}' for alias '{model_name}' not in known models"

        # Test Gemini provider
        gemini_provider = GeminiModelProvider(api_key="test-key")
        gemini_all_known = gemini_provider.list_models(
            respect_restrictions=False, include_aliases=True, lowercase=True, unique=True
        )

        # Verify that for each alias, its target is also included
        for model_name, config in gemini_provider.MODEL_CAPABILITIES.items():
            assert model_name.lower() in gemini_all_known
            if isinstance(config, str):  # This is an alias
                # The target should also be in the known models
                assert (
                    config.lower() in gemini_all_known
                ), f"Target '{config}' for alias '{model_name}' not in known models"

    def test_no_duplicate_models_in_alias_aware_listing(self):
        """Test that alias-aware list_models variant doesn't return duplicates."""
        # Test all providers
        providers = [
            OpenAIModelProvider(api_key="test-key"),
            GeminiModelProvider(api_key="test-key"),
        ]

        for provider in providers:
            all_known = provider.list_models(
                respect_restrictions=False, include_aliases=True, lowercase=True, unique=True
            )
            # Should not have duplicates
            assert len(all_known) == len(set(all_known)), f"{provider.__class__.__name__} returns duplicate models"

    def test_restriction_validation_uses_polymorphic_interface(self):
        """Test that restriction validation uses the clean polymorphic interface."""
        service = ModelRestrictionService()

        # Create a mock provider
        from unittest.mock import MagicMock

        mock_provider = MagicMock()
        mock_provider.list_models.return_value = ["model1", "model2", "target-model"]

        # Set up a restriction that should trigger validation
        service.restrictions = {ProviderType.OPENAI: {"invalid-model"}}

        provider_instances = {ProviderType.OPENAI: mock_provider}

        # Should call the polymorphic method
        service.validate_against_known_models(provider_instances)

        # Verify the polymorphic method was called
        mock_provider.list_models.assert_called_once_with(
            respect_restrictions=False,
            include_aliases=True,
            lowercase=True,
            unique=True,
        )

    @patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "gpt-5.6-luna"})  # Restrict to specific model
    def test_complex_alias_chains_handled_correctly(self):
        """Test that complex alias chains are handled correctly in restrictions."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = OpenAIModelProvider(api_key="test-key")

        # Only gpt-5.6-luna should be allowed
        assert provider.validate_model_name("gpt-5.6-luna")

        # Other models should be blocked
        assert not provider.validate_model_name("gpt-5.6-terra")
        assert not provider.validate_model_name("gpt-5.6-terra")

    def test_critical_regression_validation_sees_alias_targets(self):
        """CRITICAL REGRESSION TEST: Ensure validation can see alias target models."""
        # This test specifically validates the HIGH-severity bug that was found
        service = ModelRestrictionService()

        # Create provider instance
        provider = OpenAIModelProvider(api_key="test-key")
        provider_instances = {ProviderType.OPENAI: provider}

        # Get all known models - should include BOTH aliases AND targets
        all_known = provider.list_models(respect_restrictions=False, include_aliases=True, lowercase=True, unique=True)

        # Critical check: should contain both aliases and their targets
        assert "luna" in all_known  # alias
        assert "gpt-5.6-luna" in all_known  # target of luna
        assert "terra" in all_known  # alias
        assert "gpt-5.6-terra" in all_known  # target of terra

        # Simulate restriction validation with a target model name
        with patch("utils.model_restrictions.logger") as mock_logger:
            # Set restriction to target model (not alias)
            service.restrictions = {ProviderType.OPENAI: {"gpt-5.6-luna"}}

            # This should NOT generate warnings because gpt-5.6-luna is known
            service.validate_against_known_models(provider_instances)

            # Should NOT have any warnings about gpt-5.6-luna being unrecognized
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "gpt-5.6-luna" in str(call) and "not a recognized" in str(call)
            ]
            assert len(warning_calls) == 0, "gpt-5.6-luna should be recognized as valid target model"

        # Test the reverse: alias in restriction should also be recognized
        with patch("utils.model_restrictions.logger") as mock_logger:
            # Set restriction to alias name
            service.restrictions = {ProviderType.OPENAI: {"luna"}}

            # This should NOT generate warnings because luna is known
            service.validate_against_known_models(provider_instances)

            # Should NOT have any warnings about luna being unrecognized
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "luna" in str(call) and "not a recognized" in str(call)
            ]
            assert len(warning_calls) == 0, "luna should be recognized as valid alias"

    def test_critical_regression_prevents_policy_bypass(self):
        """CRITICAL REGRESSION TEST: Prevent policy bypass through missing target validation."""
        # Test with a made-up restriction scenario
        with patch.dict(os.environ, {"OPENAI_ALLOWED_MODELS": "gpt-5.6-luna,gpt-5.6-terra"}):
            # Clear cached restriction service
            import utils.model_restrictions

            utils.model_restrictions._restriction_service = None

            service = ModelRestrictionService()
            provider = OpenAIModelProvider(api_key="test-key")

            # These specific target models should be recognized as valid
            all_known = provider.list_models(
                respect_restrictions=False, include_aliases=True, lowercase=True, unique=True
            )
            assert "gpt-5.6-luna" in all_known, "Target model gpt-5.6-luna should be known"
            assert "gpt-5.6-terra" in all_known, "Target model gpt-5.6-terra should be known"

            # Validation should not warn about these being unrecognized
            with patch("utils.model_restrictions.logger") as mock_logger:
                provider_instances = {ProviderType.OPENAI: provider}
                service.validate_against_known_models(provider_instances)

                # Should not warn about our allowed models being unrecognized
                all_warnings = [str(call) for call in mock_logger.warning.call_args_list]
                for warning in all_warnings:
                    assert "gpt-5.6-luna" not in warning or "not a recognized" not in warning
                    assert "gpt-5.6-terra" not in warning or "not a recognized" not in warning

            # The restriction should actually work
            assert provider.validate_model_name("gpt-5.6-luna")
            assert provider.validate_model_name("gpt-5.6-terra")
            assert not provider.validate_model_name("invalid-model")  # not in allowed list
