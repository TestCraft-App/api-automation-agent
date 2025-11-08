"""Service for model-based grading of generated files."""

import json
from typing import Optional, Sequence

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from evaluations.models.evaluation_dataset import EvaluationCriterionResult, ModelGradeResult
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
2. Assess each evaluation criterion individually and determine if it is met
3. Assign an overall score between 0.0 and 1.0 based on how well the criteria are satisfied
4. Summarize how the score was determined in the reasoning section

## Response Format:
You must respond with a JSON object in this exact format:
{{
    "score": 0.0 to 1.0,
    "evaluation": [
        {{
            "criteria": "Criterion text copied or paraphrased from the evaluation criteria",
            "met": true or false,
            "details": "One or two sentences explaining why the criterion was or was not met"
        }}
    ],
    "reasoning": "Focused explanation (one to three sentences) describing how the score was determined"
}}

### Formatting Requirements:
- The evaluation array must include every criterion, in order, and set "met" to true
  only when the criterion is fully satisfied.
- Use clear, actionable language in the details field. When a criterion is not met,
  explicitly state what is missing.
- Do not include any additional top-level fields or commentary outside of the JSON object.
- Respond ONLY with valid JSON.
"""

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

    def grade(self, generated_file_content: str, evaluation_criteria: Sequence[str]) -> ModelGradeResult:
        """
        Grade a generated file against evaluation criteria.

        Args:
            generated_file_content: Content of the generated test file
            evaluation_criteria: Ordered list of criteria to evaluate against

        Returns:
            ModelGradeResult with grading information
        """
        try:
            llm = self._get_llm()
            prompt = ChatPromptTemplate.from_template(self.GRADING_PROMPT_TEMPLATE)

            chain = prompt | llm
            criteria_block = (
                "\n".join(f"- {item}" for item in evaluation_criteria)
                if evaluation_criteria
                else "- No evaluation criteria provided."
            )

            response = chain.invoke(
                {
                    "generated_file_content": generated_file_content,
                    "evaluation_criteria": criteria_block,
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
                    score=0.0,
                    evaluation=[
                        EvaluationCriterionResult(
                            criteria="Model grader response",
                            met=False,
                            details=(
                                "Invalid JSON from grader; the response could not be parsed. "
                                f"Error: {str(e)}."
                            ),
                        )
                    ],
                    reasoning="Grader response was not valid JSON",
                )

            evaluation_entries = []
            raw_evaluation = grade_data.get("evaluation", [])

            if isinstance(raw_evaluation, list):
                for entry in raw_evaluation:
                    if not isinstance(entry, dict):
                        continue
                    criteria_text = str(entry.get("criteria", "")).strip()
                    if not criteria_text:
                        continue
                    evaluation_entries.append(
                        EvaluationCriterionResult(
                            criteria=criteria_text,
                            met=bool(entry.get("met", False)),
                            details=str(entry.get("details", "")).strip() or "No details provided",
                        )
                    )

            if not evaluation_entries:
                evaluation_entries.append(
                    EvaluationCriterionResult(
                        criteria="Evaluation details",
                        met=False,
                        details="No structured evaluation data was provided by the grader",
                    )
                )

            return ModelGradeResult(
                score=grade_data.get("score"),
                evaluation=evaluation_entries,
                reasoning=grade_data.get("reasoning"),
            )

        except Exception as e:
            self.logger.error(f"Error during model grading: {e}", exc_info=True)
            return ModelGradeResult(
                score=0.0,
                evaluation=[
                    EvaluationCriterionResult(
                        criteria="Model grading",
                        met=False,
                        details=f"An exception occurred during the grading process: {str(e)}",
                    )
                ],
                reasoning="An exception occurred during the grading process",
            )
