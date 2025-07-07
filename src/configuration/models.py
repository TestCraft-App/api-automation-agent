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
    GPT_4_O = (
        "gpt-4o",
        ModelCost(input_cost_per_million_tokens=2.5, output_cost_per_million_tokens=10.0),
        Provider.OPENAI,
    )
    GPT_4_1 = (
        "gpt-4.1",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0),
        Provider.OPENAI,
    )
    O3 = (
        "o3",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0),
        Provider.OPENAI,
    )
    CLAUDE_SONNET_3_5 = (
        "claude-3-5-sonnet-latest",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
        Provider.ANTHROPIC,
    )
    CLAUDE_SONNET_3_7 = (
        "claude-3-7-sonnet-latest",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
        Provider.ANTHROPIC,
    )
    CLAUDE_SONNET_4 = (
        "claude-sonnet-4-20250514",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
        Provider.ANTHROPIC,
    )
    CLAUDE_3_5_SONNET_BEDROCK = (
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
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
            Model.CLAUDE_SONNET_3_5,
            Model.CLAUDE_SONNET_3_7,
            Model.CLAUDE_SONNET_4,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
