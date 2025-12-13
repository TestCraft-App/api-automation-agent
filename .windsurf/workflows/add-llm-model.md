---
description: Add support for a new LLM model to the agent
auto_execution_mode: 1
---

# Add New Model Workflow

This workflow guides you through adding support for a new LLM model to the API Automation Agent. Follow these steps to ensure all code, tests, and documentation are properly updated.

## Prerequisites

- Model name and identifier (e.g., `gpt-5.2`, `claude-sonnet-4-5-20250929`)
- Model pricing information (input and output cost per million tokens)
- Provider information (OpenAI, Anthropic, Google, or AWS Bedrock)
- GitHub CLI (`gh`) must be installed and authenticated

## Steps

// turbo
1. **Create a feature branch**
   
   Create a new branch for the model addition and check it out:
   ```bash
   git checkout -b feature/add-model-<model_name>
   git push -u origin feature/add-model-<model_name>
   ```
   
   Replace `<model_name>` with a short identifier (e.g., `gpt-5-2`, `claude-opus-4-5`).

2. **Add the model to the Model enum**
   
   Edit `src/configuration/models.py`:
   - Add a new enum entry with the model identifier and `ModelCost`
   - If adding a Bedrock variant, also add a `BEDROCK_` prefixed entry with the Bedrock model ID (e.g., `openai.gpt-5.2`, `anthropic.claude-*-v1:0`)
   - Update the `is_bedrock()` method if adding a Bedrock model

3. **Update the interactive setup**
   
   Edit `src/utils/interactive_setup.py`:
   - Add the model to the appropriate provider's `models` list in `SUPPORTED_PROVIDERS`
   - If this is the new recommended model for the provider, update `default_model`
   - For Bedrock models, add to provider `"4"` models list

4. **Update tests**
   
   Edit `tests/integration/test_interactive_setup.py`:
   - Update `test_complete_setup_flow_openai` if the default OpenAI model changed
   - Update `test_bedrock_provider_configuration` if Bedrock models list changed
   - Verify assertions in `test_openai_provider_configuration` still pass

// turbo
5. **Run the test suite**
   
   Verify all tests pass:
   ```bash
   pytest tests/integration/test_interactive_setup.py tests/unit/services/test_llm_service.py -v
   ```
   
   If tests fail, fix the issues before proceeding.

6. **Update main documentation**
   
   Edit `README.md`:
   - Update the model list in the "Supported Models" or provider sections
   - Update any example commands or configurations that reference models
   - If this is the new default/recommended model, update relevant examples

7. **Update usage guide**
   
   Edit `USAGE-GUIDE.txt`:
   - Add the new model to the appropriate provider's model list
   - Update the "(recommended)" label if the default changed
   - Update Bedrock models list if applicable

8. **Update benchmarks documentation**
   
   Edit `benchmarks/README.md`:
   - Add the new model enum name to the `--llms` available choices list
   - Update any example commands if the recommended model changed

9. **Update evaluations documentation**
   
   Edit `evaluations/README.md`:
   - Update the `--llms` example if the recommended model changed
   - Update any example commands that reference specific models

// turbo
10. **Run full test suite**
   
   Verify all tests still pass after documentation updates:
   ```bash
   pytest -v
   ```

11. **Review changes**
    
    Summarize all changes made:
    - Files modified in `src/`
    - Test files updated
    - Documentation files updated
    - Confirm the new model is properly integrated

// turbo
12. **Commit and push changes**
    
    Stage all modified files and commit with a descriptive message:
    ```bash
    git add -A
    git commit -m "add support for <model_name> model"
    git push
    ```
    
    Replace `<model_name>` with the model identifier (e.g., `gpt-5.2`, `claude-sonnet-4-5`).

// turbo
13. **Create a Pull Request**
    
    Create a PR using GitHub CLI with a proper description:
    ```bash
    gh pr create --title "Add support for <model_name> model" --body "## Summary
    
    Adds support for the <model_name> model.
    
    ## Changes
    
    - Added <model_name> to the Model enum in \`src/configuration/models.py\`
    - Updated interactive setup in \`src/utils/interactive_setup.py\`
    - Updated tests in \`tests/integration/test_interactive_setup.py\`
    - Updated documentation (README.md, USAGE-GUIDE.txt, benchmarks/README.md, evaluations/README.md)
    
    ## Model Details
    
    - **Provider**: <provider_name>
    - **Model ID**: <model_id>
    - **Input cost**: $<input_cost>/M tokens
    - **Output cost**: $<output_cost>/M tokens
    
    ## Testing
    
    - [x] All unit tests pass
    - [x] All integration tests pass"
    ```
    
    Replace placeholders with actual values:
    - `<model_name>`: Model name (e.g., `gpt-5.2`)
    - `<provider_name>`: Provider (OpenAI, Anthropic, Google, AWS Bedrock)
    - `<model_id>`: Full model identifier
    - `<input_cost>`, `<output_cost>`: Pricing per million tokens

## Checklist

Before completing, verify:

- [ ] Model added to `Model` enum in `src/configuration/models.py`
- [ ] Bedrock variant added (if applicable)
- [ ] `is_bedrock()` method updated (if Bedrock model)
- [ ] Interactive setup updated in `src/utils/interactive_setup.py`
- [ ] Tests updated and passing
- [ ] `README.md` updated
- [ ] `USAGE-GUIDE.txt` updated
- [ ] `benchmarks/README.md` updated
- [ ] `evaluations/README.md` updated
- [ ] Changes committed and pushed
- [ ] Pull Request created

## Notes

- Model enum names use uppercase with underscores (e.g., `GPT_5_2`, `CLAUDE_SONNET_4_5`)
- Bedrock model IDs follow provider prefixes: `openai.`, `anthropic.`, `google.`
- Always verify pricing information from the official provider documentation
- The `ModelCost` uses cost per million tokens (not per 1K tokens)