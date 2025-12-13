---
description: Fetch a GitHub issue, plan implementation, and execute it
auto_execution_mode: 1
---

# Implement GitHub Issue Workflow

This workflow fetches a GitHub issue from the repository, analyzes it, creates an implementation plan, and executes the changes.

## Prerequisites

- GitHub CLI (`gh`) must be installed and authenticated
- You must have the issue number ready

## Steps

1. **Fetch the GitHub issue**
   
   The user will provide the issue number or link so that you can extract the issue number. Otherwise, ask the user for the issue number, then run:
   ```bash
   gh issue view <ISSUE_NUMBER> --repo TestCraft-App/api-automation-agent
   ```
   
   Review the issue title, description, labels, and any comments to fully understand the requirements.

// turbo
2. **Create a feature branch**
   
   Create a new branch for the issue and check it out:
   ```bash
   git checkout -b feature/issue-<ISSUE_NUMBER>-<short_description>
   git push -u origin feature/issue-<ISSUE_NUMBER>-<short_description>
   ```
   
   Replace `<ISSUE_NUMBER>` with the issue number and `<short_description>` with a brief kebab-case description of the issue (e.g., `feature/issue-42-add-retry-logic`).

3. **Analyze the codebase context**
   
   Use the `code_search` tool to explore relevant parts of the codebase related to the issue. Search for:
   - Files mentioned in the issue
   - Related functionality or components
   - Existing patterns that should be followed
   - Unit or Integration tests that may need updates
   - Documentation mentioning impacted functionality

4. **Create an implementation plan**
   
   Based on the issue requirements and codebase analysis, create a detailed plan using `update_plan` that includes:
   - Files that need to be created or modified
   - Key changes required in each file
   - Unit or Integration test updates or new tests needed
   - Update to the Benchmark or Evals in the `benchmarks/` or `evaluations/` folders
   - Documentation updates if applicable
   - Any dependencies or prerequisites

5. **Implement the changes**
   
   Execute the plan step by step:
   - Make code changes using `edit` or `multi_edit` tools
   - Follow existing code style and patterns
   - Add necessary imports and dependencies
   - Ensure changes are minimal and focused

6. **Update or create tests**
   
   - Add new tests for new functionality
   - Update existing tests if behavior changed
   - Ensure test coverage for the changes
   
// turbo
7. **Run the test suite**
   
   Verify all tests pass:
   ```bash
   pytest -v
   ```
   
   If tests fail, analyze the failures and fix issues before proceeding.

8. **Update documentation**
   
   If the issue affects user-facing functionality:
   - Update README.md if needed
   - Update USAGE-GUIDE.txt if applicable
   - Update any relevant documentation in the `benchmarks/` or `evaluations/` folders per the rules

9. **Verify the implementation**
   
   - Review all changes made
   - Ensure the issue requirements are fully addressed
   - Check that no unrelated changes were introduced
   - Confirm code quality and style consistency

10. **Prepare for PR/commit**
    
    Summarize the changes made and provide:
    - A concise description
    - List of files changed
    - Confirmation that tests pass
    - A PR description

## Notes

- Always follow the project's coding standards and patterns
- Keep changes focused on the issue requirements
- If the issue is unclear, ask for clarification before implementing
- Do not commit or create a PR