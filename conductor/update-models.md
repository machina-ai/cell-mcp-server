# Implementation Plan: Update OpenAI, xAI, and Gemini Model Configurations

## Objective
Update model configurations and provider implementations in Zen MCP Server to support exclusively the requested native models for **OpenAI Direct**, **xAI / Grok**, and **Google Gemini Direct**, updating JSON metadata, preferred model logic, and documentation.

---

## Targeted Models & Parameters

### 1. OpenAI Direct (`conf/openai_models.json`)
* **`gpt-5.6-terra`**: Flagship terra model (1M context, 128K output, intelligence: 20).
* **`gpt-5.6-luna`**: Luna reasoning model (1M context, 128K output, response API enabled, intelligence: 20).
* **`gpt-5.6-terra`**: Standard flagship model (1M context, 128K output, intelligence: 19).
* **`gpt-5.6-terra-mini`**: Fast mini variant (1M context, 128K output, intelligence: 17).

### 2. xAI / Grok (`conf/xai_models.json`)
* **`grok-4.5`**: Flagship Grok model (2M context, 2M output, extended thinking, intelligence: 20).
* **`grok-4-1-fast-reasoning`**: High-performance fast reasoning model (2M context, 2M output, intelligence: 18).

### 3. Google Gemini Direct (`conf/gemini_models.json`)
* **`gemini-3.7-flash`**: High-speed next-gen model (1.05M context, 65.5K output, 32.7K max thinking tokens, intelligence: 18).
* **`gemini-3-flash`**: Ultra-fast iteration model (1.05M context, 65.5K output, 24.5K max thinking tokens, intelligence: 16).
* **`gemini-3.1-pro-preview`**: Deep reasoning Pro model (1.05M context, 65.5K output, 32.7K max thinking tokens, intelligence: 20).

---

## Affected Files

1. `conf/openai_models.json` – Replace existing entries with the 4 OpenAI models.
2. `conf/xai_models.json` – Replace existing entries with the 2 xAI models.
3. `conf/gemini_models.json` – Replace existing entries with the 3 Gemini models.
4. `providers/openai.py` – Update `get_preferred_model()` preference order.
5. `providers/xai.py` – Update `get_preferred_model()` preference order.
6. `providers/gemini.py` – Update `MAX_THINKING_TOKENS` dictionary and `get_preferred_model()`.
7. `.env.example` – Document required API keys and updated model list.

---

## Phased Implementation Steps

### Phase 1: JSON Configurations Update
- Overwrite `conf/openai_models.json` with the updated JSON specs for `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-terra-mini`.
- Overwrite `conf/xai_models.json` with the updated JSON specs for `grok-4.5` and `grok-4-1-fast-reasoning`.
- Overwrite `conf/gemini_models.json` with the updated JSON specs for `gemini-3.7-flash`, `gemini-3-flash`, and `gemini-3.1-pro-preview`.

### Phase 2: Provider Logic Adjustments
- In `providers/openai.py`: Update `get_preferred_model()` lists for `EXTENDED_REASONING`, `FAST_RESPONSE`, and `BALANCED` categories to prioritize `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-terra-mini`.
- In `providers/xai.py`: Update `get_preferred_model()` to prioritize `grok-4.5` and `grok-4-1-fast-reasoning`.
- In `providers/gemini.py`:
  - Update `MAX_THINKING_TOKENS` mapping for `gemini-3.7-flash`, `gemini-3-flash`, and `gemini-3.1-pro-preview`.
  - Update `get_preferred_model()` preference list.

### Phase 3: Environment Documentation
- Update `.env.example` comments for OpenAI, Gemini, and xAI model options.

---

## Verification & Testing
1. Run pytest model listing and selection tests:
   ```bash
   .zen_venv/bin/activate && pytest tests/test_auto_mode_model_listing.py tests/test_auto_mode_provider_selection.py -v
   ```
2. Run full quality checks:
   ```bash
   .zen_venv/bin/activate && ./code_quality_checks.sh
   ```
3. Run simulator quick test:
   ```bash
   .zen_venv/bin/activate && python communication_simulator_test.py --quick
   ```
