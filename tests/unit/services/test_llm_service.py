import pytest

from src.configuration.config import Config, Envs
from src.configuration.models import Model
from src.models.usage_data import LLMCallUsageData
from src.services.file_service import FileService
from src.services.llm_service import LLMService, ChatPromptTemplate


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


def test_create_ai_chain_appends_usage_metadata(llm_service, tmp_path, monkeypatch):
    class FakeResponse:
        def __init__(self, content, usage_metadata, tool_calls=None):
            self.content = content
            self.usage_metadata = usage_metadata
            self.tool_calls = tool_calls or []

    class FakeLLM:
        def __init__(self, response):
            self.response = response
            self.invocations = []

        def bind_tools(self, tools, tool_choice="auto"):
            return self

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return self.response

    class FakeChain:
        def __init__(self, llm, process_response):
            self.llm = llm
            self.process_response = process_response
            self.invocation_inputs = []

        def invoke(self, inputs):
            self.invocation_inputs.append(inputs)
            response = self.llm.invoke(inputs)
            return self.process_response(response)

    class FakePipeline:
        def __init__(self, llm):
            self.llm = llm

        def __or__(self, process_response):
            return FakeChain(self.llm, process_response)

    class FakePrompt:
        def __init__(self, template):
            self.template = template

        def __or__(self, llm):
            return FakePipeline(llm)

    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Prompt: {foo}")

    usage_payload = {"input_tokens": 600, "output_tokens": 400, "total_tokens": 1_000}
    fake_response = FakeResponse("final result", usage_payload)
    fake_llm = FakeLLM(fake_response)

    llm_service.config.model = Model.GPT_4_O

    monkeypatch.setattr(LLMService, "_select_language_model", lambda self, language_model=None: fake_llm)
    monkeypatch.setattr(
        ChatPromptTemplate,
        "from_template",
        classmethod(lambda cls, template: FakePrompt(template)),
    )

    chain = llm_service.create_ai_chain(str(prompt_path))

    result = chain.invoke({"foo": "bar"})

    assert result == "final result"
    assert chain.invocation_inputs == [{"foo": "bar"}]

    aggregated_usage = llm_service.get_aggregated_usage_metadata()

    expected_cost = (usage_payload["input_tokens"] / 1_000_000) * 2.5 + (
        usage_payload["output_tokens"] / 1_000_000
    ) * 10.0

    assert aggregated_usage.total_input_tokens == usage_payload["input_tokens"]
    assert aggregated_usage.total_output_tokens == usage_payload["output_tokens"]
    assert aggregated_usage.total_tokens == usage_payload["total_tokens"]
    assert aggregated_usage.total_cost == pytest.approx(expected_cost)
    assert len(aggregated_usage.call_details) == 1
    assert aggregated_usage.call_details[0].cost == pytest.approx(expected_cost)
    assert aggregated_usage.call_details[0].input_tokens == usage_payload["input_tokens"]


def test_create_ai_chain_usage_metadata_validation_fallback(llm_service, tmp_path, monkeypatch):
    """When usage metadata exists but is invalid (fails pydantic validation),
    the service should log a warning, create a default LLMCallUsageData() instance,
    and aggregate it without raising an exception.

    This test injects a usage_metadata payload with an invalid type for an int field
    (a dict instead of an int) to trigger validation failure.
    """

    class FakeResponse:
        def __init__(self, content, usage_metadata):
            self.content = content
            self.usage_metadata = usage_metadata
            self.tool_calls = []

    class FakeLLM:
        def __init__(self, response):
            self.response = response

        def bind_tools(self, tools, tool_choice="auto"):
            return self

        def invoke(self, inputs):
            return self.response

    class FakeChain:
        def __init__(self, llm, process_response):
            self.llm = llm
            self.process_response = process_response

        def invoke(self, inputs):
            response = self.llm.invoke(inputs)
            return self.process_response(response)

    class FakePipeline:
        def __init__(self, llm):
            self.llm = llm

        def __or__(self, process_response):
            return FakeChain(self.llm, process_response)

    class FakePrompt:
        def __init__(self, template):
            self.template = template

        def __or__(self, llm):
            return FakePipeline(llm)

    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Prompt: {x}")

    invalid_usage_payload = {"input_tokens": {"bad": "value"}, "output_tokens": 10, "total_tokens": 10}
    fake_response = FakeResponse("ok", invalid_usage_payload)
    fake_llm = FakeLLM(fake_response)

    from src.configuration.models import Model  # local import to avoid unused at module import

    llm_service.config.model = Model.GPT_4_O

    monkeypatch.setattr(LLMService, "_select_language_model", lambda self, language_model=None: fake_llm)
    monkeypatch.setattr(
        ChatPromptTemplate,
        "from_template",
        classmethod(lambda cls, template: FakePrompt(template)),
    )

    chain = llm_service.create_ai_chain(str(prompt_path))

    result = chain.invoke({"x": "y"})
    assert result == "ok"

    aggregated = llm_service.get_aggregated_usage_metadata()

    # Because validation failed, a default LLMCallUsageData() (all zeros) should have been added.
    assert aggregated.total_input_tokens == 0
    assert aggregated.total_output_tokens == 0
    assert aggregated.total_tokens == 0
    assert aggregated.total_cost == 0
    assert len(aggregated.call_details) == 1
    detail = aggregated.call_details[0]
    assert detail.input_tokens == 0
    assert detail.output_tokens == 0
    assert detail.total_tokens == 0
    assert detail.cost is None


def test_create_ai_chain_tool_choice_selection(llm_service, monkeypatch, tmp_path):
    """Verify tool_choice value chosen for OpenAI vs Anthropic models with must_use_tool flag.

    Expectations:
      - If tools provided:
          default tool_choice = 'auto'
          Anthropic + must_use_tool True  -> 'any'
          OpenAI (non-Anthropic) + must_use_tool True -> 'required'
          must_use_tool False -> stays 'auto'
    We simulate both providers by setting llm_service.config.model accordingly and monkeypatching
    _select_language_model to return a FakeLLM whose bind_tools captures the tool_choice passed.
    """

    class DummyTool:
        def __init__(self, name="dummy"):
            self.name = name

        def invoke(self, args):
            return args

    captured = []

    class FakeLLM:
        def __init__(self):
            self.bound = []  # collected tool_choice values
            self.bind_calls = 0

        def bind_tools(self, tools, tool_choice="auto"):
            self.bind_calls += 1
            self.bound.append(tool_choice)
            return self

        def __or__(self, rhs):  # rhs will be process_response callable
            class _Chain:
                def invoke(self_inner, _inputs):
                    class _Resp:
                        content = None
                        usage_metadata = None
                        tool_calls = []

                    return rhs(_Resp())

            return _Chain()

    class FakePrompt:
        def __init__(self, template):
            self.template = template

        def __or__(self, llm):
            # Return a simple pipeline that passes through to a processor closure,
            # but we only need to support chaining prompt | llm | process_response.
            return llm

    # Patch prompt template creation to return our fake prompt.
    monkeypatch.setattr(
        ChatPromptTemplate,
        "from_template",
        classmethod(lambda cls, template: FakePrompt(template)),
    )

    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Prompt: {x}")

    # Shared fake llm instance reused so we can inspect bound tool choices sequentially.
    fake_llm = FakeLLM()
    monkeypatch.setattr(LLMService, "_select_language_model", lambda self, language_model=None: fake_llm)

    scenarios = [
        # (model_enum, must_use_tool, expected_tool_choice, label, tools_provider)
        # Single tool cases
        (Model.GPT_4_O, False, "auto", "openai_no_force_single", lambda: [DummyTool()]),
        (Model.GPT_4_O, True, "required", "openai_force_single", lambda: [DummyTool()]),
        (Model.CLAUDE_SONNET_4, False, "auto", "anthropic_no_force_single", lambda: [DummyTool()]),
        (Model.CLAUDE_SONNET_4, True, "any", "anthropic_force_single", lambda: [DummyTool()]),
        # Multiple tools cases (should behave identically wrt tool_choice)
        (Model.GPT_4_O, True, "required", "openai_force_multi", lambda: [DummyTool("a"), DummyTool("b")]),
        (
            Model.CLAUDE_SONNET_4,
            True,
            "any",
            "anthropic_force_multi",
            lambda: [DummyTool("a"), DummyTool("b")],
        ),
    ]

    initial_bind_calls = 0
    for model_enum, must_use, expected_choice, label, tools_fn in scenarios:
        llm_service.config.model = model_enum
        chain = llm_service.create_ai_chain(
            str(prompt_path),
            tools=tools_fn(),
            must_use_tool=must_use,
            language_model=model_enum,
        )
        try:
            chain.invoke({"x": "value"})
        except Exception:
            pass

        # The last recorded bind_tools choice corresponds to this scenario.
        actual_choice = fake_llm.bound[-1]
        captured.append((label, expected_choice, actual_choice))
        assert (
            fake_llm.bind_calls == initial_bind_calls + 1
        ), "bind_tools should be called exactly once per tools scenario"
        initial_bind_calls = fake_llm.bind_calls

    # No-tools scenarios: ensure bind_tools NOT called and chain creation still works.
    for model_enum in (Model.GPT_4_O, Model.CLAUDE_SONNET_4):
        llm_service.config.model = model_enum
        chain = llm_service.create_ai_chain(
            str(prompt_path), tools=None, must_use_tool=False, language_model=model_enum
        )
        # Should not increase bind_calls because tools list is None
        assert fake_llm.bind_calls == initial_bind_calls, "bind_tools should not be called when tools is None"
        try:
            chain.invoke({"x": "value"})
        except Exception:
            pass

    for label, expected, actual in captured:
        assert actual == expected, f"Scenario {label} expected tool_choice {expected} but got {actual}"
