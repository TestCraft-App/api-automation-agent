from enum import Enum
from typing import NamedTuple


class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"


class ModelCost(NamedTuple):
    input_cost_per_million_tokens: float
    output_cost_per_million_tokens: float


class Model(Enum):
    GPT_5_MINI = (
        "gpt-5-mini",
        ModelCost(input_cost_per_million_tokens=0.25, output_cost_per_million_tokens=2.0),
        Provider.OPENAI,
    )
    GPT_4_1 = (
        "gpt-4.1",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0),
        Provider.OPENAI,
    )
    GPT_5 = (
        "gpt-5",
        ModelCost(input_cost_per_million_tokens=1.25, output_cost_per_million_tokens=10.0),
        Provider.OPENAI,
    )
    CLAUDE_SONNET_4 = (
        "claude-sonnet-4-20250514",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
        Provider.ANTHROPIC,
    )
    CLAUDE_SONNET_4_5 = (
        "claude-sonnet-4-5-20250929",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
        Provider.ANTHROPIC,
    )
    CLAUDE_HAIKU_4_5 = (
        "claude-haiku-4-5-20251001",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
        Provider.ANTHROPIC,
    )
    CLAUDE_SONNET_4_5_BEDROCK = (
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
        Provider.BEDROCK,
    )

    def __new__(cls, value, cost: ModelCost, provider: Provider):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cost = cost
        obj.provider = provider
        return obj

    @property
    def model_name(self) -> str:
        return self.value

    def is_anthropic(self) -> bool:
        return self in [
            Model.CLAUDE_SONNET_4,
            Model.CLAUDE_SONNET_4_5,
            Model.CLAUDE_HAIKU_4_5,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
