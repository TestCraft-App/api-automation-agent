from enum import Enum
from typing import NamedTuple


class ModelCost(NamedTuple):
    input_cost_per_million_tokens: float
    output_cost_per_million_tokens: float


class Model(Enum):
    GPT_4_O = ("gpt-4o", ModelCost(input_cost_per_million_tokens=2.5, output_cost_per_million_tokens=10.0))
    GPT_4_1 = ("gpt-4.1", ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0))
    GPT_5 = ("gpt-5", ModelCost(input_cost_per_million_tokens=1.25, output_cost_per_million_tokens=10.0))
    O3 = (
        "o3",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=8.0),
    )
    CLAUDE_SONNET_3_5 = (
        "claude-3-5-sonnet-latest",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_SONNET_3_7 = (
        "claude-3-7-sonnet-latest",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
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
            Model.CLAUDE_SONNET_3_5,
            Model.CLAUDE_SONNET_3_7,
            Model.CLAUDE_SONNET_4,
            Model.CLAUDE_SONNET_4_5,
            Model.CLAUDE_HAIKU_4_5,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
