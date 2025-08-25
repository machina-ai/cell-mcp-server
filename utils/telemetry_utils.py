"""
Utility functions for OpenTelemetry integration.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

def add_token_usage_to_span(model_response: Any) -> None:
    """
    Adds token usage information from a ModelResponse to the current OpenTelemetry span.

    This is a best-effort function. It will not raise exceptions if OpenTelemetry
    is not installed, if there is no active span, or if the model_response object
    does not contain the expected usage data.

    Args:
        model_response: An object that should have a `usage` attribute, which is a
                        dictionary containing 'input_tokens', 'output_tokens',
                        and 'total_tokens'. Typically a `ModelResponse` instance.
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        
        # Ensure we have a valid, recording span and usage data
        if not (span and span.is_recording()):
            return

        # Check if model_response and its usage attribute are valid
        usage = getattr(model_response, 'usage', None)
        if not isinstance(usage, dict) or not usage:
            return

        # Set attributes if they exist in the usage dictionary
        if "input_tokens" in usage:
            span.set_attribute("llm.usage.input_tokens", usage.get("input_tokens", 0))
        if "output_tokens" in usage:
            span.set_attribute("llm.usage.output_tokens", usage.get("output_tokens", 0))
        if "total_tokens" in usage:
            span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))

    except ImportError:
        # OpenTelemetry is not installed, do nothing.
        pass
    except Exception as e:
        # Prevent any telemetry-related errors from breaking the main execution flow.
        logger.warning(f"Failed to set OTEL token usage attributes: {e}")
