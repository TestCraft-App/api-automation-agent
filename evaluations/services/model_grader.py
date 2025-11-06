"""Service for model-based grading of generated files."""

import json
from typing import Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from evaluations.models.evaluation_dataset import ModelGradeResult
from src.configuration.config import Config
from src.utils.logger import Logger


class ModelGrader:
    """Service for evaluating generated files using LLM-based grading."""

    GRADING_PROMPT_TEMPLATE = """You are an expert evaluator for API test automation code.

Your task is to evaluate whether a generated TypeScript test file meets the specified evaluation criteria.

## Generated Test File Content:
{generated_file_content}

## Evaluation Criteria:
{evaluation_criteria}

## Instructions:
1. Carefully review the generated test file content
2. Check if it meets all the requirements specified in the evaluation criteria
3. Provide a clear assessment: PASS or FAIL
4. Give detailed feedback explaining why it passed or failed
5. If applicable, provide a score from 0.0 to 1.0 indicating how well it meets the criteria

## Response Format:
You must respond with a JSON object in this exact format:
{{
    "passed": true or false,
    "score": 0.0 to 1.0 (optional, can be null),
    "feedback": "Detailed explanation of why it passed or failed",
    "reasoning": "Optional additional reasoning or notes"
}}

Respond ONLY with valid JSON, no additional text."""

    def __init__(self, config: Config, llm: Optional[BaseLanguageModel] = None):
        """
        Initialize the Model Grader.

        Args:
            config: Configuration object
            llm: Optional language model to use. If not provided, will use config.model
        """
        self.config = config
        self.logger = Logger.get_logger(__name__)
        self._llm = llm

    def _get_llm(self) -> BaseLanguageModel:
        """Get or create the language model for grading."""
        if self._llm:
            return self._llm

        # Directly create the model instance (same logic as LLMService._select_language_model)
        import pydantic
        from langchain_anthropic import ChatAnthropic
        from langchain_openai import ChatOpenAI

        try:
            if self.config.model.is_anthropic():
                return ChatAnthropic(
                    model_name=self.config.model.value,
                    temperature=1,
                    api_key=pydantic.SecretStr(self.config.anthropic_api_key),
                    timeout=None,
                    stop=None,
                    max_retries=3,
                    max_tokens_to_sample=8192,
                )
            return ChatOpenAI(
                model=self.config.model.value,
                temperature=1,
                max_retries=3,
                api_key=pydantic.SecretStr(self.config.openai_api_key),
            )
        except Exception as e:
            self.logger.error(f"Model initialization error: {e}")
            raise

    def grade(self, generated_file_content: str, evaluation_criteria: str) -> ModelGradeResult:
        """
        Grade a generated file against evaluation criteria.

        Args:
            generated_file_content: Content of the generated test file
            evaluation_criteria: Criteria to evaluate against

        Returns:
            ModelGradeResult with grading information
        """
        try:
            llm = self._get_llm()
            prompt = ChatPromptTemplate.from_template(self.GRADING_PROMPT_TEMPLATE)

            chain = prompt | llm
            response = chain.invoke(
                {
                    "generated_file_content": generated_file_content,
                    "evaluation_criteria": evaluation_criteria,
                }
            )

            content = response.content if hasattr(response, "content") else str(response)
            content = content.strip()

            if content.startswith("```"):
                lines = content.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        if not in_json:
                            in_json = True
                        else:
                            break
                    elif in_json:
                        json_lines.append(line)
                content = "\n".join(json_lines)

            try:
                grade_data = json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON from grader response: {e}. Content: {content}")
                return ModelGradeResult(
                    passed=False,
                    score=0.0,
                    feedback=f"Failed to parse grader response: {str(e)}. Raw response: {content[:200]}",
                    reasoning="Grader response was not valid JSON",
                )

            return ModelGradeResult(
                passed=grade_data.get("passed", False),
                score=grade_data.get("score"),
                feedback=grade_data.get("feedback", "No feedback provided"),
                reasoning=grade_data.get("reasoning"),
            )

        except Exception as e:
            self.logger.error(f"Error during model grading: {e}", exc_info=True)
            return ModelGradeResult(
                passed=False,
                score=0.0,
                feedback=f"Error during grading: {str(e)}",
                reasoning="An exception occurred during the grading process",
            )
