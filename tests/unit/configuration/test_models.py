from src.configuration.models import Model


def test_supported_direct_openai_models_are_only_gpt_5_6_tiers():
    direct_openai_models = {model.value for model in Model if model.value.startswith("gpt-")}

    assert direct_openai_models == {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}


def test_supported_bedrock_openai_models_are_only_gpt_5_6_tiers():
    bedrock_openai_models = {model.value for model in Model if model.value.startswith("openai.")}

    assert bedrock_openai_models == {
        "openai.gpt-5.6-sol",
        "openai.gpt-5.6-terra",
        "openai.gpt-5.6-luna",
    }


def test_all_bedrock_openai_models_are_classified_as_bedrock():
    bedrock_openai_models = [model for model in Model if model.value.startswith("openai.")]

    assert all(model.is_bedrock() for model in bedrock_openai_models)


def test_supported_direct_anthropic_models_are_only_current_claude_models():
    direct_anthropic_models = {model.value for model in Model if model.is_anthropic()}

    assert direct_anthropic_models == {
        "claude-fable-5-1",
        "claude-opus-5",
        "claude-sonnet-5",
        "claude-haiku-4-5",
    }


def test_supported_bedrock_anthropic_models_are_only_current_claude_models():
    bedrock_anthropic_models = {model.value for model in Model if model.value.startswith("anthropic.")}

    assert bedrock_anthropic_models == {
        "anthropic.claude-fable-5-1",
        "anthropic.claude-opus-5",
        "anthropic.claude-sonnet-5",
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
