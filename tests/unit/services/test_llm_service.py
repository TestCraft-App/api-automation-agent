import pytest

from src.configuration.config import Config, Envs
from src.configuration.models import Model
from src.models.usage_data import LLMCallUsageData
from src.services.file_service import FileService
from src.services.llm_service import LLMService


@pytest.fixture
def temp_config(tmp_path):
    return Config(destination_folder=str(tmp_path), env=Envs.DEV)


@pytest.fixture
def llm_service(temp_config):
    return LLMService(temp_config, FileService())


def test_calculate_llm_call_cost_returns_expected_value(llm_service):
    usage_data = LLMCallUsageData(input_tokens=1_000, output_tokens=2_000)

    cost = llm_service._calculate_llm_call_cost(Model.GPT_4_O, usage_data)

    expected_cost = (1_000 / 1_000_000) * 2.5 + (2_000 / 1_000_000) * 10.0
    assert cost == pytest.approx(expected_cost)


def test_calculate_llm_call_cost_returns_none_on_error(llm_service, monkeypatch):
    def raise_error(_self):
        raise ValueError("boom")

    monkeypatch.setattr(Model, "get_costs", raise_error)
    usage_data = LLMCallUsageData(input_tokens=500, output_tokens=500)

    cost = llm_service._calculate_llm_call_cost(Model.GPT_4_O, usage_data)

    assert cost is None
