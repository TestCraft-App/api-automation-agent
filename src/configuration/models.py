from enum import Enum
from typing import NamedTuple


class ModelCost(NamedTuple):
    input_cost_per_million_tokens: float
    output_cost_per_million_tokens: float


class Model(Enum):
    GPT_6_1_SOL = (
        "gpt-6.1-sol",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=10.0),
    )
    GPT_5_6_TERRA = (
        "gpt-5.6-terra",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    GPT_6_LUNA = (
        "gpt-6-luna",
        ModelCost(input_cost_per_million_tokens=0.1, output_cost_per_million_tokens=0.5),
    )
    CLAUDE_OPUS_5_5 = (
        "claude-opus-5-5",
        ModelCost(input_cost_per_million_tokens=4.0, output_cost_per_million_tokens=20.0),
    )
    CLAUDE_SONNET_5_5 = (
        "claude-sonnet-5-5",
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
    BEDROCK_CLAUDE_OPUS_5_5 = (
        "anthropic.claude-opus-5-5",
        ModelCost(input_cost_per_million_tokens=4.0, output_cost_per_million_tokens=20.0),
    )
    BEDROCK_CLAUDE_SONNET_5_5 = (
        "anthropic.claude-sonnet-5-5",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=10.0),
    )
    BEDROCK_CLAUDE_HAIKU_4_5 = (
        "anthropic.claude-haiku-4-5-20251001-v1:0",
        ModelCost(input_cost_per_million_tokens=1.0, output_cost_per_million_tokens=5.0),
    )
    # Standard short-context estimates; Sol's US inference profile includes the 10% AWS premium.
    BEDROCK_GPT_6_1_SOL = (
        "openai.gpt-6.1-sol",
        ModelCost(input_cost_per_million_tokens=2.2, output_cost_per_million_tokens=11.0),
    )
    BEDROCK_GPT_5_6_TERRA = (
        "openai.gpt-5.6-terra",
        ModelCost(input_cost_per_million_tokens=2.0, output_cost_per_million_tokens=12.0),
    )
    BEDROCK_GPT_6_LUNA = (
        "openai.gpt-6-luna",
        ModelCost(input_cost_per_million_tokens=0.1, output_cost_per_million_tokens=0.5),
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
            Model.CLAUDE_OPUS_5_5,
            Model.CLAUDE_SONNET_5_5,
            Model.CLAUDE_HAIKU_4_5,
        ]

    def uses_default_sampling(self, use_function_tools: bool = False) -> bool:
        """Whether provider-default sampling parameters must be omitted."""
        return self in [
            Model.CLAUDE_OPUS_5_5,
            Model.CLAUDE_SONNET_5_5,
            Model.BEDROCK_CLAUDE_OPUS_5_5,
            Model.BEDROCK_CLAUDE_SONNET_5_5,
            Model.GPT_6_1_SOL,
            Model.BEDROCK_GPT_6_1_SOL,
            Model.BEDROCK_GPT_6_LUNA,
        ] or (self == Model.GPT_6_LUNA and not use_function_tools)

    def is_openai(self) -> bool:
        return self.value.startswith(("gpt-", "openai."))

    def requires_responses_api(self) -> bool:
        return self == Model.GPT_6_1_SOL

    def tool_reasoning_effort(self) -> str:
        """Direct OpenAI reasoning setting for function-tool requests."""
        return "low" if self.requires_responses_api() else "none"

    def supports_forced_tool_use(self) -> bool:
        return self not in {
            Model.CLAUDE_OPUS_5_5,
            Model.CLAUDE_SONNET_5_5,
            Model.BEDROCK_CLAUDE_OPUS_5_5,
            Model.BEDROCK_CLAUDE_SONNET_5_5,
            Model.BEDROCK_GPT_6_1_SOL,
            Model.BEDROCK_GPT_6_LUNA,
        }

    @property
    def bedrock_invocation_id(self) -> str:
        """Resolve canonical configuration IDs to supported Runtime inference profiles."""
        if self.value.startswith("anthropic.") or self == Model.BEDROCK_GPT_6_LUNA:
            return f"global.{self.value}"
        if self == Model.BEDROCK_GPT_6_1_SOL:
            return f"us.{self.value}"
        return self.value

    @property
    def bedrock_provider(self) -> str:
        return self.value.split(".", 1)[0]

    @property
    def bedrock_tool_choice_values(self) -> tuple:
        return ("auto", "any", "tool") if self.supports_forced_tool_use() else ("auto",)

    def is_google(self) -> bool:
        return self in [
            Model.GEMINI_3_PRO_PREVIEW,
            Model.GEMINI_3_1_PRO_PREVIEW,
            Model.GEMINI_3_FLASH,
        ]

    def is_bedrock(self) -> bool:
        return self in [
            Model.BEDROCK_CLAUDE_OPUS_5_5,
            Model.BEDROCK_CLAUDE_SONNET_5_5,
            Model.BEDROCK_CLAUDE_HAIKU_4_5,
            Model.BEDROCK_GPT_6_1_SOL,
            Model.BEDROCK_GPT_5_6_TERRA,
            Model.BEDROCK_GPT_6_LUNA,
            Model.BEDROCK_GEMINI_3_PRO_PREVIEW,
            Model.BEDROCK_GEMINI_3_1_PRO_PREVIEW,
            Model.BEDROCK_GEMINI_3_FLASH,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
