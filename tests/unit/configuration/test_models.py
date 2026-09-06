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
