"""
Telemetry utilities for creating Langfuse-compatible OpenTelemetry spans.

This module provides functions to create detailed, structured spans for LLM
interactions that are compatible with Langfuse's expectations for raw
OpenTelemetry data. It replicates the attribute and structure conventions
observed in known-good implementations, creating a dedicated child span for
each LLM call.
"""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from typing import Any, Iterator
from typing import Optional
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from utils.auth import current_user_id

logger = logging.getLogger(__name__)

# --- Provider/Model normalization for pricing & dedup ---
_MODEL_ALIASES = {
    # OpenAI
    "gpt5": "gpt-5",
    "gpt5-mini": "gpt-5-mini",
    "gpt4o": "gpt-4o",
    "gpt4.1": "gpt-4.1",
    "gpt4.1-mini": "gpt-4.1-mini",
    # Anthropic
    "claude3.5": "claude-3.5",
    "claude4": "claude-4",
    "claude-4": "claude-4",
    "claude4.1": "claude-4.1",
    "claude-4.1": "claude-4.1",
    # Google
    "gemini2.5": "gemini-2.5",
    "gemini2.0": "gemini-2.0",
}

def _normalize_provider(provider_name: Any) -> str:
    try:
        p = str(provider_name or "").strip()
    except Exception:
        return ""
    return p.lower().replace(" ", "")

def _normalize_model(provider: str, model_name: Any) -> str:
    try:
        m = str(model_name or "").strip()
    except Exception:
        return ""
    key = m.lower().replace(" ", "")
    return _MODEL_ALIASES.get(key, m)

def _to_int(v: Any) -> int:
    try:
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        return int(float(str(v).strip()))
    except Exception:
        return 0

def _extract_output_text(model_response: Any) -> str:
    try:
        if model_response is None:
            return ""
        if isinstance(model_response, dict):
            ch = model_response.get("choices")
            if isinstance(ch, list) and ch:
                first = ch[0] or {}
                msg = first.get("message") if isinstance(first, dict) else None
                if isinstance(msg, dict) and msg.get("content"):
                    return str(msg["content"])
                if isinstance(first, dict) and first.get("text"):
                    return str(first["text"])
            if "output_text" in model_response:
                out_t = model_response["output_text"]
                return "".join(map(str, out_t)) if isinstance(out_t, list) else str(out_t)
            cands = model_response.get("candidates")
            if isinstance(cands, list) and cands:
                c0 = cands[0] or {}
                content = c0.get("content")
                if isinstance(content, dict):
                    parts = content.get("parts") or []
                    texts = [str(p.get("text") or "") for p in parts if isinstance(p, dict) and "text" in p]
                    if texts:
                        return "".join(texts)
                if isinstance(content, str):
                    return content
            cont = model_response.get("content")
            if isinstance(cont, list) and cont and isinstance(cont[0], dict) and cont[0].get("text"):
                return str(cont[0]["text"])
            for key in ("content", "text", "output"):
                v = model_response.get(key)
                if isinstance(v, (str, bytes)):
                    return v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
            return json.dumps(model_response)
        for attr in ("content", "text"):
            v = getattr(model_response, attr, None)
            if isinstance(v, (str, bytes)):
                return v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
        choices = getattr(model_response, "choices", None)
        if isinstance(choices, list) and choices:
            first = choices[0]
            msg = getattr(first, "message", None)
            if msg is not None:
                c = getattr(msg, "content", None)
                if c:
                    return str(c)
            t = getattr(first, "text", None)
            if t:
                return str(t)
        return str(model_response)
    except Exception:
        try:
            return json.dumps(model_response)
        except Exception:
            return str(model_response)


def _set_attr_safe(span: Span, key: str, value: Any) -> None:
    """Set an attribute on a span, falling back to JSON for complex types.
    Some OTEL SDKs only accept primitives or lists of primitives; Langfuse expects
    certain nested structures. We try the direct set and if it fails, we JSON-encode.
    """
    try:
        span.set_attribute(key, value)
    except Exception:
        try:
            span.set_attribute(key, json.dumps(value))
        except Exception:
            # last resort: string cast
            span.set_attribute(key, str(value))


@contextmanager
def create_llm_span(
    model_name: str, provider_name: str, prompt: str
) -> Iterator[Span]:
    """
    Starts a new child span for an LLM call, following Langfuse conventions.

    This context manager creates a new span named after the model, sets
    pre-call attributes (model, provider, prompt, user), and yields the span.
    The caller is responsible for enriching the span with the response data
    using `enrich_span_with_response`.

    Args:
        model_name: The name of the language model being called.
        provider_name: The name of the model provider (e.g., 'google').
        prompt: The full prompt being sent to the model.

    Yields:
        The newly created and active OpenTelemetry Span.
    """
    tracer = trace.get_tracer(__name__)
    _prov = _normalize_provider(provider_name)
    _model_norm = _normalize_model(_prov, model_name)
    with tracer.start_as_current_span(f"cell-mcp.{_model_norm}") as span:
        if span.is_recording():
            try:
                # Set attributes available before the LLM call (normalized)
                span.set_attribute("gen_ai.system", _prov)
                span.set_attribute("gen_ai.request.model", _model_norm)
                if _model_norm != model_name:
                    span.set_attribute("llm.model_alias", str(model_name))
                # Langfuse uses this to categorize the operation, e.g., "chat"
                span.set_attribute("gen_ai.operation.name", "chat")
                # Langfuse convention for the input prompt
                try:
                    span.set_attribute("llm.prompts", [prompt])
                except Exception:
                    span.set_attribute("llm.prompts", json.dumps([prompt]))

                # Mirror plain input field for compatibility with consumers expecting 'input'
                try:
                    span.set_attribute("input", prompt)
                except Exception:
                    span.set_attribute("input", str(prompt))

                user_id = current_user_id()
                if user_id:
                    span.set_attribute("user.id", user_id)
            except Exception as e:
                logger.warning(f"Failed to set pre-call OTEL attributes: {e}")

        yield span


def enrich_span_with_response(span: Span, model_response: Any) -> None:
    """
    Enriches a span with details from the model's response, including
    the completion content and token usage.

    Args:
        span: The OpenTelemetry Span to enrich.
        model_response: The response object from the model provider.
    """
    if not span or not span.is_recording():
        return

    try:
        out_text = _extract_output_text(model_response)
        if isinstance(out_text, str) and len(out_text) > 500_000:
            out_text = "...(truncated)" + out_text[-500_000:]
        try:
            span.set_attribute("llm.completions", [{"text": out_text}])
            # Mirror plain output field for compatibility with consumers expecting 'output'
            try:
                span.set_attribute("output", out_text)
            except Exception:
                span.set_attribute("output", str(out_text))
        except Exception as e:
            logger.warning("Failed to map llm.completions: %s", e, exc_info=True)
    except Exception as e:
        logger.warning("Failed to map llm.completions: %s", e, exc_info=True)

    try:
        usage: dict[str, Any] = {}
        if isinstance(model_response, dict):
            usage = model_response.get("usage") or model_response.get("usageMetadata") or {}
        else:
            usage = getattr(model_response, "usage", None) or getattr(model_response, "usageMetadata", None) or {}

        # Normalize input/output/total token keys across providers
        in_candidates = (
            usage.get("prompt_tokens"),
            usage.get("promptTokenCount"),
            usage.get("input_tokens"),
            usage.get("inputTokenCount"),
            usage.get("inputTextTokenCount"),
        )
        out_candidates = (
            usage.get("completion_tokens"),
            usage.get("candidatesTokenCount"),
            usage.get("output_tokens"),
            usage.get("outputTokenCount"),
            usage.get("outputTextTokenCount"),
        )
        total_candidates = (
            usage.get("total_tokens"),
            usage.get("totalTokens"),
            usage.get("total_token_count"),
            usage.get("totalTokenCount"),
        )

        in_toks = _to_int(next((v for v in in_candidates if v is not None), None))
        out_toks = _to_int(next((v for v in out_candidates if v is not None), None))
        total = _to_int(next((v for v in total_candidates if v is not None), None))
        if total == 0:
            total = in_toks + out_toks

        # Ensure attributes are stored as integers, not strings
        span.set_attributes({
            "llm.prompt_tokens": in_toks,
            "llm.completion_tokens": out_toks,
            "llm.total_tokens": total,
            "llm.usage.prompt_tokens": in_toks,
            "llm.usage.completion_tokens": out_toks,
            "llm.usage.total_tokens": total,
            "gen_ai.usage.input_tokens": in_toks,
            "gen_ai.usage.output_tokens": out_toks,
            "gen_ai.usage.total_tokens": total,
        })
    except Exception as e:
        logger.warning("Failed to map token usage: %s", e, exc_info=True)


def annotate_llm_io_and_usage(
    span: Span,
    *,
    prompt: str,
    response: Any,
    provider_name: str | None = None,
    model_name: str | None = None,
) -> None:
    """Annotate a span with input/output and usage, plus optional provider/model.
    Safe to call even if the span is non-recording.
    """
    if not span or not span.is_recording():
        return
    # Normalize provider/model and ensure canonical attributes
    try:
        _prov = _normalize_provider(provider_name) if provider_name is not None else None
    except Exception:
        _prov = None
    try:
        _model_norm = _normalize_model(_prov or "", model_name) if model_name is not None else None
    except Exception:
        _model_norm = None
    if _prov:
        try:
            span.set_attribute("gen_ai.system", _prov)
        except Exception:
            pass
    if _model_norm:
        try:
            span.set_attribute("gen_ai.request.model", _model_norm)
            if model_name is not None and _model_norm != model_name:
                span.set_attribute("llm.model_alias", str(model_name))
            if hasattr(span, "update_name"):
                try:
                    span.update_name(f"cell-mcp.{_model_norm}")
                except Exception:
                    pass
        except Exception:
            pass
    try:
        _set_attr_safe(span, "llm.prompts", [prompt])
    except Exception:
        pass
    try:
        span.set_attribute("input", prompt)
    except Exception:
        span.set_attribute("input", str(prompt))
    try:
        enrich_span_with_response(span, response)
    except Exception:
        pass

# --- add near the other imports if missing ---
import functools
from opentelemetry import trace

def instrument_generate_content(fn):
    """Wrap a provider's generate_content to auto-annotate telemetry.
    Idempotent: will not double-wrap the same function.
    Behavior:
      - If a current span is recording: do NOT create a new span; just annotate it.
      - Else: create a span via create_llm_span and annotate it.
    """
    if getattr(fn, "_telemetry_wrapped", False):
        return fn

    @functools.wraps(fn)
    def _wrapped(self, *args, **kwargs):
        # Extract minimal context for telemetry from kwargs
        prompt = kwargs.get("prompt", "")
        model_name = kwargs.get("model_name", "")
        try:
            ptype = self.get_provider_type()
            provider_name = getattr(ptype, "value", str(ptype))
        except Exception:
            provider_name = ""

        cur = trace.get_current_span()
        is_recording = bool(cur) and getattr(cur, "is_recording", lambda: False)()

        if is_recording:
            # Do not create a new span; annotate the current one
            response = fn(self, *args, **kwargs)
            try:
                annotate_llm_io_and_usage(
                    cur,
                    prompt=prompt,
                    response=response,
                    provider_name=provider_name,
                    model_name=model_name,
                )
            except Exception:
                pass
            return response

        # No active recording span: create one around the call
        with create_llm_span(model_name, provider_name, prompt) as span:
            response = fn(self, *args, **kwargs)
            try:
                annotate_llm_io_and_usage(
                    span,
                    prompt=prompt,
                    response=response,
                    provider_name=provider_name,
                    model_name=model_name,
                )
            except Exception:
                pass
            return response

    _wrapped._telemetry_wrapped = True
    return _wrapped