# Implementation Plan: Update xAI Models to Grok 4.6

## Objective
Update xAI model definitions and provider integration in Zen MCP Server to:
1. Configure **`grok-4.6`** as the flagship and exclusive native model for xAI.
2. Remove deprecated `grok-4.3` and its reasoning effort variants (`grok-4.3`, `grok-4.3-low`, `grok-4.3-none`).
3. Retain unified alias resolution (`grok`, `grok-latest`, `grok4.6`, `fast` -> `grok-4.6`).

---

## Model Specifications & Parameters

### `grok-4.6` (Flagship Reasoning)
* **Model Name:** `grok-4.6`
* **Aliases:** `grok`, `grok-latest`, `grok4.6`, `grok-4.6`, `fast`
* **Context Window:** 500,000 tokens
* **Max Output Tokens:** 128,000 tokens
* **Intelligence Score:** 20
* **Capabilities:** Extended thinking, streaming, function calling, JSON mode, images (20MB).

---

## Affected Files

1. `conf/xai_models.json` – Update model configurations for `grok-4.6`.
2. `providers/xai.py` – Update `get_preferred_model()` to prioritize `grok-4.6`.
3. `.env.example` – Update documentation for xAI Grok models.
4. Test suites (`tests/test_xai_provider.py`, `tests/test_supported_models_aliases.py`, `tests/test_auto_mode_provider_selection.py`, `tests/test_auto_mode_comprehensive.py`).

---

## Verification & Testing
- Run xAI tests and full test suite:
  ```bash
  .zen_venv/bin/pytest tests/test_xai_provider.py tests/test_supported_models_aliases.py tests/test_auto_mode_provider_selection.py -v
  ```
- Run code quality checks.
