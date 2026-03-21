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
    GPT_5_2 = ("gpt-5.2", ModelCost(input_cost_per_million_tokens=1.75, output_cost_per_million_tokens=14.0))
    GPT_5_3_CODEX = (
        "gpt-5.3-codex",
        ModelCost(input_cost_per_million_tokens=1.75, output_cost_per_million_tokens=14.0),
    )
    GPT_5_4 = ("gpt-5.4", ModelCost(input_cost_per_million_tokens=2.5, output_cost_per_million_tokens=15.0))
    GPT_5_4_MINI = (
        "gpt-5.4-mini",
        ModelCost(input_cost_per_million_tokens=0.75, output_cost_per_million_tokens=4.5),
    )
    GPT_5_4_NANO = (
        "gpt-5.4-nano",
        ModelCost(input_cost_per_million_tokens=0.2, output_cost_per_million_tokens=1.25),
    )
    CLAUDE_SONNET_4 = (
        "claude-sonnet-4",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_SONNET_4_5 = (
        "claude-sonnet-4-5",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_HAIKU_4_5 = (
        "claude-haiku-4-5",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    CLAUDE_OPUS_4_5 = (
        "claude-opus-4-5",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
    )
    CLAUDE_SONNET_4_6 = (
        "claude-sonnet-4-6",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_OPUS_4_6 = (
        "claude-opus-4-6",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
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
    BEDROCK_CLAUDE_SONNET_4 = (
        "anthropic.claude-sonnet-4-v1:0",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    BEDROCK_CLAUDE_SONNET_4_5 = (
        "anthropic.claude-sonnet-4-5-v1:0",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    BEDROCK_CLAUDE_HAIKU_4_5 = (
        "anthropic.claude-haiku-4-5-v1:0",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    BEDROCK_CLAUDE_OPUS_4_5 = (
        "anthropic.claude-opus-4-5-v1:0",
        ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=25.0),
    )
    BEDROCK_CLAUDE_SONNET_4_6 = (
        "anthropic.claude-sonnet-4-6-v1:0",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    BEDROCK_CLAUDE_OPUS_4_6 = (
        "anthropic.claude-opus-4-6-v1:0",
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
    BEDROCK_GPT_5_2 = (
        "openai.gpt-5.2",
        ModelCost(input_cost_per_million_tokens=1.75, output_cost_per_million_tokens=14.0),
    )
    BEDROCK_GPT_5_3_CODEX = (
        "openai.gpt-5.3-codex",
        ModelCost(input_cost_per_million_tokens=1.75, output_cost_per_million_tokens=14.0),
    )
    BEDROCK_GPT_5_4 = (
        "openai.gpt-5.4",
        ModelCost(input_cost_per_million_tokens=2.5, output_cost_per_million_tokens=15.0),
    )
    BEDROCK_GPT_5_4_MINI = (
        "openai.gpt-5.4-mini",
        ModelCost(input_cost_per_million_tokens=0.75, output_cost_per_million_tokens=4.5),
    )
    BEDROCK_GPT_5_4_NANO = (
        "openai.gpt-5.4-nano",
        ModelCost(input_cost_per_million_tokens=0.2, output_cost_per_million_tokens=1.25),
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
            Model.CLAUDE_SONNET_4,
            Model.CLAUDE_SONNET_4_5,
            Model.CLAUDE_HAIKU_4_5,
            Model.CLAUDE_OPUS_4_5,
            Model.CLAUDE_SONNET_4_6,
            Model.CLAUDE_OPUS_4_6,
        ]

    def is_google(self) -> bool:
        return self in [
            Model.GEMINI_3_PRO_PREVIEW,
            Model.GEMINI_3_1_PRO_PREVIEW,
            Model.GEMINI_3_FLASH,
        ]

    def is_bedrock(self) -> bool:
        return self in [
            Model.BEDROCK_CLAUDE_SONNET_4,
            Model.BEDROCK_CLAUDE_SONNET_4_5,
            Model.BEDROCK_CLAUDE_HAIKU_4_5,
            Model.BEDROCK_CLAUDE_OPUS_4_5,
            Model.BEDROCK_CLAUDE_SONNET_4_6,
            Model.BEDROCK_CLAUDE_OPUS_4_6,
            Model.BEDROCK_GPT_5_MINI,
            Model.BEDROCK_GPT_4_1,
            Model.BEDROCK_GPT_5,
            Model.BEDROCK_GPT_5_1,
            Model.BEDROCK_GPT_5_2,
            Model.BEDROCK_GPT_5_3_CODEX,
            Model.BEDROCK_GPT_5_4,
            Model.BEDROCK_GPT_5_4_MINI,
            Model.BEDROCK_GPT_5_4_NANO,
            Model.BEDROCK_GEMINI_3_PRO_PREVIEW,
            Model.BEDROCK_GEMINI_3_1_PRO_PREVIEW,
            Model.BEDROCK_GEMINI_3_FLASH,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
