from enum import Enum
from typing import NamedTuple


class ModelCost(NamedTuple):
    input_cost_per_million_tokens: float
    output_cost_per_million_tokens: float


class Model(Enum):
    GPT_5_MINI = (
        "gpt-5-mini",
        ModelCost(input_cost_per_million_tokens=0.25, output_cost_per_million_tokens=2.0),
    )
    GPT_4_1 = ("gpt-4.1", ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0))
    GPT_5 = ("gpt-5", ModelCost(input_cost_per_million_tokens=1.25, output_cost_per_million_tokens=10.0))
    GPT_5_1 = ("gpt-5.1", ModelCost(input_cost_per_million_tokens=1.25, output_cost_per_million_tokens=10.0))
    CLAUDE_SONNET_4 = (
        "claude-sonnet-4-20250514",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_SONNET_4_5 = (
        "claude-sonnet-4-5-20250929",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_HAIKU_4_5 = (
        "claude-haiku-4-5-20251001",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    CLAUDE_OPUS_4_5 = (
        "claude-opus-4-5-20251101",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
    )
    GEMINI_3_PRO_PREVIEW = (
        "gemini-3-pro-preview",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    BEDROCK_CLAUDE_SONNET_4 = (
        "anthropic.claude-sonnet-4-20250514-v1:0",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    BEDROCK_CLAUDE_SONNET_4_5 = (
        "anthropic.claude-sonnet-4-5-20250929-v1:0",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    BEDROCK_CLAUDE_HAIKU_4_5 = (
        "anthropic.claude-haiku-4-5-20251001-v1:0",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    BEDROCK_CLAUDE_OPUS_4_5 = (
        "anthropic.claude-opus-4-5-20251101-v1:0",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
    )
    BEDROCK_GPT_5_MINI = (
        "openai.gpt-5-mini",
        ModelCost(input_cost_per_million_tokens=0.25, output_cost_per_million_tokens=2.0),
    )
    BEDROCK_GPT_4_1 = (
        "openai.gpt-4.1",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0),
    )
    BEDROCK_GPT_5 = (
        "openai.gpt-5",
        ModelCost(input_cost_per_million_tokens=1.25, output_cost_per_million_tokens=10.0),
    )
    BEDROCK_GPT_5_1 = (
        "openai.gpt-5.1",
        ModelCost(input_cost_per_million_tokens=1.25, output_cost_per_million_tokens=10.0),
    )
    BEDROCK_GEMINI_3_PRO_PREVIEW = (
        "google.gemini-3-pro-preview",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )

    def __new__(cls, value, cost: ModelCost):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cost = cost
        return obj

    @property
    def model_name(self) -> str:
        return self.value

    def is_anthropic(self) -> bool:
        return self in [
            Model.CLAUDE_SONNET_4,
            Model.CLAUDE_SONNET_4_5,
            Model.CLAUDE_HAIKU_4_5,
            Model.CLAUDE_OPUS_4_5,
        ]

    def is_google(self) -> bool:
        return self in [
            Model.GEMINI_3_PRO_PREVIEW,
        ]

    def is_bedrock(self) -> bool:
        return self in [
            Model.BEDROCK_CLAUDE_SONNET_4,
            Model.BEDROCK_CLAUDE_SONNET_4_5,
            Model.BEDROCK_CLAUDE_HAIKU_4_5,
            Model.BEDROCK_CLAUDE_OPUS_4_5,
            Model.BEDROCK_GPT_5_MINI,
            Model.BEDROCK_GPT_4_1,
            Model.BEDROCK_GPT_5,
            Model.BEDROCK_GPT_5_1,
            Model.BEDROCK_GEMINI_3_PRO_PREVIEW,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
