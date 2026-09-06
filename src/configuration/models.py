from enum import Enum
from typing import NamedTuple


class ModelCost(NamedTuple):
    input_cost_per_million_tokens: float
    output_cost_per_million_tokens: float


class Model(Enum):
    GPT_5_6_SOL = (
        "gpt-5.6-sol",
        ModelCost(input_cost_per_million_tokens=4.0, output_cost_per_million_tokens=20.0),
    )
    GPT_5_6_TERRA = (
        "gpt-5.6-terra",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    GPT_5_6_LUNA = (
        "gpt-5.6-luna",
        ModelCost(input_cost_per_million_tokens=0.2, output_cost_per_million_tokens=1.2),
    )
    CLAUDE_FABLE_5_1 = (
        "claude-fable-5-1",
        ModelCost(input_cost_per_million_tokens=10.0, output_cost_per_million_tokens=50.0),
    )
    CLAUDE_OPUS_5 = (
        "claude-opus-5",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
    )
    CLAUDE_SONNET_5 = (
        "claude-sonnet-5",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=10.0),
    )
    CLAUDE_HAIKU_4_5 = (
        "claude-haiku-4-5",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    GEMINI_3_PRO_PREVIEW = (
        "gemini-3-pro-preview",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    GEMINI_3_1_PRO_PREVIEW = (
        "gemini-3.1-pro-preview",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    GEMINI_3_FLASH = (
        "gemini-3-flash",
        ModelCost(input_cost_per_million_tokens=0.5, output_cost_per_million_tokens=3.0),
    )
    # Bedrock pricing can differ from direct Anthropic API pricing. These rates are estimates based
    # on the corresponding Anthropic base input/output rates, consistent with the existing cost model.
    BEDROCK_CLAUDE_FABLE_5_1 = (
        "anthropic.claude-fable-5-1",
        ModelCost(input_cost_per_million_tokens=10.0, output_cost_per_million_tokens=50.0),
    )
    BEDROCK_CLAUDE_OPUS_5 = (
        "anthropic.claude-opus-5",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
    )
    BEDROCK_CLAUDE_SONNET_5 = (
        "anthropic.claude-sonnet-5",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=10.0),
    )
    BEDROCK_CLAUDE_HAIKU_4_5 = (
        "anthropic.claude-haiku-4-5-20251001-v1:0",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    # Bedrock pricing can differ from direct OpenAI API pricing. These rates are estimates based on
    # the corresponding OpenAI standard short-context rates, consistent with the existing cost model.
    BEDROCK_GPT_5_6_SOL = (
        "openai.gpt-5.6-sol",
        ModelCost(input_cost_per_million_tokens=4.0, output_cost_per_million_tokens=20.0),
    )
    BEDROCK_GPT_5_6_TERRA = (
        "openai.gpt-5.6-terra",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    BEDROCK_GPT_5_6_LUNA = (
        "openai.gpt-5.6-luna",
        ModelCost(input_cost_per_million_tokens=0.2, output_cost_per_million_tokens=1.2),
    )
    BEDROCK_GEMINI_3_PRO_PREVIEW = (
        "google.gemini-3-pro-preview",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    BEDROCK_GEMINI_3_1_PRO_PREVIEW = (
        "google.gemini-3.1-pro-preview",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    BEDROCK_GEMINI_3_FLASH = (
        "google.gemini-3-flash",
        ModelCost(input_cost_per_million_tokens=0.5, output_cost_per_million_tokens=3.0),
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
            Model.CLAUDE_FABLE_5_1,
            Model.CLAUDE_OPUS_5,
            Model.CLAUDE_SONNET_5,
            Model.CLAUDE_HAIKU_4_5,
        ]

    def uses_default_sampling(self) -> bool:
        """Whether provider-default sampling parameters must be omitted."""
        return self in [
            Model.CLAUDE_FABLE_5_1,
            Model.CLAUDE_OPUS_5,
            Model.CLAUDE_SONNET_5,
            Model.BEDROCK_CLAUDE_FABLE_5_1,
            Model.BEDROCK_CLAUDE_OPUS_5,
            Model.BEDROCK_CLAUDE_SONNET_5,
        ]

    def is_gpt_5_6(self) -> bool:
        """Whether this is a direct or Bedrock GPT-5.6 model."""
        return self in [
            Model.GPT_5_6_SOL,
            Model.GPT_5_6_TERRA,
            Model.GPT_5_6_LUNA,
            Model.BEDROCK_GPT_5_6_SOL,
            Model.BEDROCK_GPT_5_6_TERRA,
            Model.BEDROCK_GPT_5_6_LUNA,
        ]

    def is_google(self) -> bool:
        return self in [
            Model.GEMINI_3_PRO_PREVIEW,
            Model.GEMINI_3_1_PRO_PREVIEW,
            Model.GEMINI_3_FLASH,
        ]

    def is_bedrock(self) -> bool:
        return self in [
            Model.BEDROCK_CLAUDE_FABLE_5_1,
            Model.BEDROCK_CLAUDE_OPUS_5,
            Model.BEDROCK_CLAUDE_SONNET_5,
            Model.BEDROCK_CLAUDE_HAIKU_4_5,
            Model.BEDROCK_GPT_5_6_SOL,
            Model.BEDROCK_GPT_5_6_TERRA,
            Model.BEDROCK_GPT_5_6_LUNA,
            Model.BEDROCK_GEMINI_3_PRO_PREVIEW,
            Model.BEDROCK_GEMINI_3_1_PRO_PREVIEW,
            Model.BEDROCK_GEMINI_3_FLASH,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
