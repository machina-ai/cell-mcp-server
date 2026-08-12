# Objective
Update the project's model configuration to use OpenAI's new gpt-5.6-terra models, replacing the current gpt-5.6-terra.4 definitions based on recent official documentation.

# Key Files & Context
- `conf/openai_models.json`: Contains the model definitions, metadata, and aliases for OpenAI models.

# Implementation Steps

1. **Update `conf/openai_models.json`:**
   - Modify the existing `gpt-5.6-terra.4` block to define the new `gpt-5.6-terra-pro` model (for advanced reasoning with parallel test-time compute), setting its `context_window` to `1000000`, updating aliases to `["gpt5.5p", "gpt-5.6-terra-pro", "pro"]`, and keeping `supports_extended_thinking` and `use_openai_response_api` enabled.
   - Insert a new block for the `gpt-5.6-terra` (Standard) model. It will have a `context_window` of `1000000`, `supports_extended_thinking` set to `false`, and `supports_temperature` set to `true`.
   - Update the `gpt-5.6-terra.4-mini` block to `gpt-5.6-terra-mini`, adjusting the name, aliases (`["gpt5.5m", "gpt-5.6-terra-mini", "mini"]`), description, and increasing the `context_window` to `1000000`.
   - Update the `gpt-5.6-terra.4-nano` block to `gpt-5.6-terra-nano`, adjusting the name, aliases (`["gpt5.5n", "gpt-5.6-terra-nano", "nano"]`), description, and increasing the `context_window` to `1000000`.

# Verification & Testing
- Review the `conf/openai_models.json` file for valid JSON syntax.
- Ensure that the total number of models in the list includes the new Pro, Standard, Mini, and Nano variants properly formatted without duplicates.
