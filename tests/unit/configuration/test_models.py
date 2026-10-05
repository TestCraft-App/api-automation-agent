import pytest

from src.configuration.models import Model


def test_supported_direct_openai_models_are_only_selected_current_tiers():
    direct_openai_models = {model.value for model in Model if model.value.startswith("gpt-")}

    assert direct_openai_models == {"gpt-6.1-sol", "gpt-5.6-terra", "gpt-6-luna"}


def test_supported_bedrock_openai_models_are_only_selected_current_tiers():
    bedrock_openai_models = {model.value for model in Model if model.value.startswith("openai.")}

    assert bedrock_openai_models == {
        "openai.gpt-6.1-sol",
        "openai.gpt-5.6-terra",
        "openai.gpt-6-luna",
    }


def test_all_bedrock_openai_models_are_classified_as_bedrock():
    bedrock_openai_models = [model for model in Model if model.value.startswith("openai.")]

    assert all(model.is_bedrock() for model in bedrock_openai_models)


def test_supported_direct_anthropic_models_are_only_current_claude_models():
    direct_anthropic_models = {model.value for model in Model if model.is_anthropic()}

    assert direct_anthropic_models == {
        "claude-opus-5-5",
        "claude-sonnet-5-5",
        "claude-haiku-4-5",
    }


def test_supported_bedrock_anthropic_models_are_only_current_claude_models():
    bedrock_anthropic_models = {model.value for model in Model if model.value.startswith("anthropic.")}

    assert bedrock_anthropic_models == {
        "anthropic.claude-opus-5-5",
        "anthropic.claude-sonnet-5-5",
        "anthropic.claude-haiku-4-5-20251001-v1:0",
    }
    assert all(Model(value).is_bedrock() for value in bedrock_anthropic_models)


def test_legacy_anthropic_model_identifiers_are_not_supported():
    legacy_identifiers = {
        "claude-sonnet-4",
        "claude-sonnet-4-5",
        "claude-opus-4-5",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "anthropic.claude-sonnet-4-v1:0",
        "anthropic.claude-sonnet-4-5-v1:0",
        "anthropic.claude-haiku-4-5-v1:0",
        "anthropic.claude-opus-4-5-v1:0",
        "anthropic.claude-sonnet-4-6-v1:0",
        "anthropic.claude-opus-4-6-v1:0",
    }

    assert legacy_identifiers.isdisjoint(model.value for model in Model)


@pytest.mark.parametrize(
    "identifier",
    [
        "claude-fable-5-1",
        "claude-opus-5",
        "claude-sonnet-5",
        "anthropic.claude-fable-5-1",
        "anthropic.claude-opus-5",
        "anthropic.claude-sonnet-5",
        "gpt-5.6-sol",
        "gpt-5.6-luna",
        "openai.gpt-5.6-sol",
        "openai.gpt-5.6-luna",
        "gpt-6-astra",
    ],
)
def test_removed_model_identifier_is_rejected(identifier):
    with pytest.raises(ValueError):
        Model(identifier)


@pytest.mark.parametrize(
    "model,invocation_id,input_rate,output_rate",
    [
        (Model.BEDROCK_CLAUDE_OPUS_5_5, "global.anthropic.claude-opus-5-5", 4, 20),
        (Model.BEDROCK_CLAUDE_SONNET_5_5, "global.anthropic.claude-sonnet-5-5", 2, 10),
        (Model.BEDROCK_CLAUDE_HAIKU_4_5, "global.anthropic.claude-haiku-4-5-20251001-v1:0", 1, 5),
        (Model.BEDROCK_GPT_6_1_SOL, "us.openai.gpt-6.1-sol", 2.2, 11),
        (Model.BEDROCK_GPT_6_LUNA, "global.openai.gpt-6-luna", 0.1, 0.5),
        (Model.BEDROCK_GPT_5_6_TERRA, "openai.gpt-5.6-terra", 2, 12),
    ],
)
def test_bedrock_invocation_profile_and_estimated_price(model, invocation_id, input_rate, output_rate):
    assert model.bedrock_invocation_id == invocation_id
    assert model.get_costs() == (input_rate, output_rate)
    assert Model(model.value) is model
