# Implementation Plan: Update xAI Models & Correct Context Window Specifications

## Objective
Update xAI model definitions and provider integration in Zen MCP Server to:
1. Correct `grok-4.5` context window specification to **500,000 tokens**.
2. Replace retired fast models (`grok-4-1-fast-reasoning`, `grok-4-1-fast-non-reasoning`) with **`grok-4.3`** and its reasoning effort variants (`grok-4.3`, `grok-4.3-low`, `grok-4.3-none`).
3. Enhance `ModelCapabilities` and `OpenAICompatibleProvider` to pass `reasoning_effort` and support mapped API model names when specified.

---

## Model Specifications & Parameters

### 1. `grok-4.5`
* **Model Name:** `grok-4.5`
* **Aliases:** `grok`, `grok4.5`, `grok-4.5`
* **Context Window:** **500,000 tokens** (Corrected from 2M)
* **Max Output Tokens:** 128,000 tokens
* **Intelligence Score:** 20
* **Capabilities:** Extended thinking, streaming, function calling, JSON mode, images (20MB).

### 2. `grok-4.3` (Flagship Standard)
* **Model Name:** `grok-4.3`
* **Aliases:** `grok4.3`, `grok-4.3`
* **Context Window:** 1,000,000 tokens
* **Max Output Tokens:** 128,000 tokens
* **Intelligence Score:** 20
* **Capabilities:** Extended thinking, streaming, function calling, JSON mode, images (20MB).

### 3. `grok-4.3-low` (Fast Reasoning Variant)
* **Model Name:** `grok-4.3-low`
* **API Model Name:** `grok-4.3`
* **Reasoning Effort:** `low`
* **Aliases:** `fast`, `grok4.1f`, `grok-4.1-fast`, `grok-4-1-fast-reasoning`, `grok-4.3-low`
* **Context Window:** 1,000,000 tokens
* **Max Output Tokens:** 128,000 tokens
* **Intelligence Score:** 18
* **Capabilities:** Extended thinking, streaming, function calling, JSON mode, images (20MB).

### 4. `grok-4.3-none` (Non-Reasoning Variant)
* **Model Name:** `grok-4.3-none`
* **API Model Name:** `grok-4.3`
* **Reasoning Effort:** `none`
* **Aliases:** `non-reasoning`, `grok-4-1-fast-non-reasoning`, `grok-4.3-none`
* **Context Window:** 1,000,000 tokens
* **Max Output Tokens:** 128,000 tokens
* **Intelligence Score:** 16
* **Capabilities:** Streaming, function calling, JSON mode, images (20MB).

---

## Affected Files

1. `conf/xai_models.json` – Update model configurations for `grok-4.5`, `grok-4.3`, `grok-4.3-low`, `grok-4.3-none`.
2. `providers/shared/model_capabilities.py` – Add `api_model_name` field to `ModelCapabilities`.
3. `providers/openai_compatible.py` – Pass `reasoning_effort` in `completion_params` when `default_reasoning_effort` is set on model capabilities.
4. `providers/xai.py` – Update `get_preferred_model()` to prioritize `grok-4.5`, `grok-4.3`, `grok-4.3-low`.
5. `.env.example` – Update documentation for xAI Grok models.
6. Test suites (`tests/test_xai_provider.py`, `tests/test_auto_mode_model_listing.py`, `tests/test_auto_mode_provider_selection.py`, etc.).

---

## Phased Implementation Steps

### Phase 1: Core Capabilities & Provider Updates
- Add `api_model_name: Optional[str] = None` to `ModelCapabilities`.
- Update `OpenAICompatibleProvider.generate_content()` to set `completion_params["reasoning_effort"]` if `capabilities.default_reasoning_effort` is set.
- Map `resolved_model = capabilities.api_model_name or resolved_model` when calling the API.

### Phase 2: JSON Configuration Update
- Update `conf/xai_models.json` with corrected 500K context for `grok-4.5` and add `grok-4.3`, `grok-4.3-low`, `grok-4.3-none`.

### Phase 3: Provider Preference & Env Doc Update
- Update `providers/xai.py` model preference order.
- Update `.env.example`.

### Phase 4: Verification & Testing
- Run xAI tests and full test suite:
  ```bash
  .zen_venv/bin/pytest tests/test_xai_provider.py tests/test_auto_mode_provider_selection.py -v
  ```
- Run live API verification script against xAI endpoint.
- Run ruff, isort, and black code quality checks.
