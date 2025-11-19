import json
import pytest

from src.configuration.config import Config, Envs
from src.configuration.data_sources import DataSource
from src.services.file_service import FileService
from src.services.llm_service import LLMService


@pytest.fixture
def temp_config(tmp_path):
    return Config(destination_folder=str(tmp_path), env=Envs.DEV)


@pytest.fixture
def llm_service(temp_config):
    return LLMService(temp_config, FileService())


def test_generate_models_success_list_return(monkeypatch, llm_service):
    """generate_models should return a list of ModelFileSpec when chain.invoke returns a list of dicts."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return self.payload

    model_payload = [
        {
            "path": "./UserModel.ts",
            "fileContent": "export interface User { id: string; name: string }",
            "summary": "User model. Properties: id, name",
        },
        {
            "path": "./PetService.ts",
            "fileContent": "export class PetService {}",
            "summary": "Pet service: listPets, getPet",
        },
    ]

    fake_chain = FakeChain(model_payload)
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)

    result = llm_service.generate_models("openapi spec text")

    assert len(result) == 2
    assert result[0].path == "./UserModel.ts"
    assert result[0].summary.startswith("User model")
    assert result[1].path == "./PetService.ts"
    assert "Pet service" in result[1].summary


def test_generate_models_success_json_string(monkeypatch, llm_service):
    """generate_models should handle JSON string returned by chain.invoke."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload

        def invoke(self, inputs):
            return json.dumps(self.payload)

    model_payload = [
        {
            "path": "./OrderModel.ts",
            "fileContent": "export interface Order { id: string }",
            "summary": "Order model. Properties: id",
        }
    ]
    fake_chain = FakeChain(model_payload)
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)

    result = llm_service.generate_models("openapi spec text")
    assert len(result) == 1
    assert result[0].path == "./OrderModel.ts"
    assert result[0].summary.startswith("Order model")
    assert result[0].fileContent == "export interface Order { id: string }"


def test_generate_models_error_returns_empty_list(monkeypatch, llm_service):
    """If an exception occurs inside generate_models, it should return an empty list."""

    class FakeChain:
        def invoke(self, inputs):
            raise RuntimeError("boom")

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    result = llm_service.generate_models("whatever")
    assert result == []


def test_generate_models_chain_construction_arguments(monkeypatch, llm_service):
    """Ensure generate_models uses the expected prompt, must_use_tool flag, and FileCreationTool configured for models."""

    captured = {}

    class DummyChain:
        def invoke(self, _):
            return []

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        captured["must_use_tool"] = must_use_tool
        captured["tools"] = tools
        return DummyChain()

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    llm_service.generate_models("spec text")

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.MODELS
    assert captured["must_use_tool"] is True
    assert isinstance(captured["tools"], list) and len(captured["tools"]) == 1
    tool = captured["tools"][0]
    assert getattr(tool, "are_models", False) is True
    assert getattr(tool, "name", "") == "create_models"


def test_generate_models_malformed_json(monkeypatch, llm_service):
    """Malformed JSON from chain should cause generate_models to return an empty list."""

    class FakeChain:
        def invoke(self, _):
            return "{ bad json"

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    result = llm_service.generate_models("spec")
    assert result == []


def test_generate_models_non_list_json(monkeypatch, llm_service):
    """A JSON object (not list) response should yield an empty result list."""

    class FakeChain:
        def invoke(self, _):
            obj = {
                "path": "./SoloModel.ts",
                "fileContent": "export interface Solo {}",
                "summary": "Solo model.",
            }
            return json.dumps(obj)

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    result = llm_service.generate_models("spec")
    assert result == []


# ---------------------- Tests for generate_first_test ---------------------- #


def _build_generated_models():
    from src.models.generated_model import GeneratedModel

    return [
        GeneratedModel(
            path="./models/UserModel.ts", fileContent="export interface User {}", summary="User model"
        ),
        GeneratedModel(
            path="./services/UserService.ts",
            fileContent="export class UserService {}",
            summary="User service",
        ),
    ]


def test_generate_first_test_success_list_return_swagger(monkeypatch, llm_service):
    """generate_first_test should return a list[FileSpec] when chain.invoke returns list of dicts (SWAGGER path)."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return self.payload

    test_payload = [
        {
            "path": "./tests/Get-GetUser.spec.ts",
            "fileContent": "import 'chai'; describe('x', () => { it('y', () => {})});",
        }
    ]

    fake_chain = FakeChain(test_payload)
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)

    models = _build_generated_models()
    result = llm_service.generate_first_test("openapi spec", models)

    assert len(result) == 1
    assert result[0].path == "./tests/Get-GetUser.spec.ts"
    assert result[0].fileContent.startswith("import")

    # Ensure the models were passed serialized (list of dicts) to invoke
    assert "models" in fake_chain.invocations[0]
    assert isinstance(fake_chain.invocations[0]["models"], list)
    assert fake_chain.invocations[0]["models"][0]["path"].endswith("UserModel.ts")


def test_generate_first_test_success_json_string_postman(monkeypatch, llm_service, temp_config):
    """When data_source is POSTMAN the POSTMAN prompt should be used and JSON string results handled."""

    temp_config.data_source = DataSource.POSTMAN

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return json.dumps(self.payload)

    test_payload = [
        {
            "path": "./tests/Post-CreateUser.spec.ts",
            "fileContent": "import 'chai'; describe('create', () => { it('ok', () => {})});",
        }
    ]

    captured = {}

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        return FakeChain(test_payload)

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    models = _build_generated_models()
    result = llm_service.generate_first_test("postman collection", models)

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.FIRST_TEST_POSTMAN
    assert len(result) == 1 and result[0].path.endswith("Post-CreateUser.spec.ts")


def test_generate_first_test_error_returns_empty(monkeypatch, llm_service):
    """If create_ai_chain.invoke raises an error, generate_first_test returns []."""

    class FakeChain:
        def invoke(self, _):
            raise ValueError("fail")

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    result = llm_service.generate_first_test("spec", _build_generated_models())
    assert result == []


def test_generate_first_test_chain_construction_arguments(monkeypatch, llm_service):
    """Ensure generate_first_test uses expected prompt and FileCreationTool for Swagger data source."""

    captured = {}

    class DummyChain:
        def invoke(self, _):
            return []

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        captured["must_use_tool"] = must_use_tool
        captured["tools"] = tools
        return DummyChain()

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    llm_service.generate_first_test("spec", _build_generated_models())

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.FIRST_TEST
    assert captured["must_use_tool"] is True
    assert isinstance(captured["tools"], list) and len(captured["tools"]) == 1
    tool = captured["tools"][0]
    assert getattr(tool, "are_models", True) is False
    assert getattr(tool, "name", "") == "create_files"


def test_generate_first_test_malformed_json(monkeypatch, llm_service):
    """Malformed JSON response should cause generate_first_test to return empty list."""

    class FakeChain:
        def invoke(self, _):
            return "{ bad json"

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    result = llm_service.generate_first_test("spec", _build_generated_models())
    assert result == []


def test_generate_first_test_non_list_json(monkeypatch, llm_service):
    """A JSON object (not list) response should yield an empty result list for generate_first_test."""

    class FakeChain:
        def invoke(self, _):
            obj = {"path": "./tests/Single.spec.ts", "fileContent": "// test"}
            return json.dumps(obj)

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    result = llm_service.generate_first_test("spec", _build_generated_models())
    assert result == []


# ---------------------- Tests for get_additional_models ---------------------- #


def _build_api_models():
    from src.models.api_model import APIModel

    return [
        APIModel(path="./services/UserService.ts", files=["UserService.ts"], models=[]),
        APIModel(path="./models/UserModel.ts", files=["UserModel.ts"], models=[]),
    ]


def test_get_additional_models_success_list(monkeypatch, llm_service):
    """get_additional_models returns list[FileSpec] when chain returns list payload."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return self.payload

    payload = [
        {"path": "./models/BookingModel.ts", "fileContent": "export interface Booking {}"},
        {"path": "./models/HotelModel.ts", "fileContent": "export interface Hotel {}"},
    ]
    fake_chain = FakeChain(payload)
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)

    result = llm_service.get_additional_models(_build_generated_models(), _build_api_models())

    assert len(result) == 2
    assert result[0].path.endswith("BookingModel.ts")
    assert result[1].path.endswith("HotelModel.ts")
    # verify invocation payload structure
    first_invocation = fake_chain.invocations[0]
    assert "relevant_models" in first_invocation and isinstance(first_invocation["relevant_models"], list)
    assert "available_models" in first_invocation and isinstance(first_invocation["available_models"], list)


def test_get_additional_models_success_json_string(monkeypatch, llm_service):
    """get_additional_models handles JSON string output."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload

        def invoke(self, _):
            return json.dumps(self.payload)

    payload = [
        {"path": "./models/ExtraModel.ts", "fileContent": "export interface Extra {}"},
    ]
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain(payload))

    result = llm_service.get_additional_models(_build_generated_models(), _build_api_models())
    assert len(result) == 1 and result[0].path.endswith("ExtraModel.ts")


def test_get_additional_models_error_returns_empty(monkeypatch, llm_service):
    """Errors during chain invoke cause empty list return."""

    class FakeChain:
        def invoke(self, _):
            raise RuntimeError("boom")

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())
    result = llm_service.get_additional_models(_build_generated_models(), _build_api_models())
    assert result == []


def test_get_additional_models_chain_construction_arguments(monkeypatch, llm_service):
    """Ensure get_additional_models uses ADD_INFO prompt and FileReadingTool with must_use_tool True."""

    captured = {}

    class DummyChain:
        def invoke(self, _):
            return []

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        captured["must_use_tool"] = must_use_tool
        captured["tools"] = tools
        return DummyChain()

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    llm_service.get_additional_models(_build_generated_models(), _build_api_models())

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.ADD_INFO
    assert captured["must_use_tool"] is True
    assert isinstance(captured["tools"], list) and len(captured["tools"]) == 1
    tool = captured["tools"][0]
    assert getattr(tool, "name", "") == "read_files"


def test_get_additional_models_malformed_json(monkeypatch, llm_service):
    """Malformed JSON should produce empty list."""

    class FakeChain:
        def invoke(self, _):
            return "{ malformed"

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())
    result = llm_service.get_additional_models(_build_generated_models(), _build_api_models())
    assert result == []


def test_get_additional_models_non_list_json(monkeypatch, llm_service):
    """Non-list JSON object should yield empty list."""

    class FakeChain:
        def invoke(self, _):
            return json.dumps({"path": "./models/Single.ts", "fileContent": "// x"})

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())
    result = llm_service.get_additional_models(_build_generated_models(), _build_api_models())
    assert result == []


def test_get_additional_models_empty_list(monkeypatch, llm_service):
    """Empty list response should produce empty list of FileSpec objects (no error)."""

    class FakeChain:
        def __init__(self):
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return json.dumps([])

    fake_chain = FakeChain()
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)

    result = llm_service.get_additional_models(_build_generated_models(), _build_api_models())
    assert result == []
    # verify we still passed the correct shape to the chain
    assert len(fake_chain.invocations) == 1
    inv = fake_chain.invocations[0]
    assert isinstance(inv.get("relevant_models"), list)
    assert isinstance(inv.get("available_models"), list)


# ---------------------- Tests for generate_additional_tests ---------------------- #


def _build_file_specs_for_additional_tests():
    from src.ai_tools.models.file_spec import FileSpec

    return [
        FileSpec(path="./tests/Get-GetUser.spec.ts", fileContent="// original test"),
        FileSpec(path="./tests/Post-CreateUser.spec.ts", fileContent="// original create test"),
    ]


def test_generate_additional_tests_success_list(monkeypatch, llm_service):
    """generate_additional_tests returns list[FileSpec] when chain returns list payload."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return self.payload

    payload = [
        {"path": "./tests/Delete-DeleteUser.spec.ts", "fileContent": "// delete test"},
        {"path": "./tests/Put-UpdateUser.spec.ts", "fileContent": "// update test"},
    ]
    fake_chain = FakeChain(payload)
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)

    models = _build_generated_models()
    existing_tests = _build_file_specs_for_additional_tests()
    result = llm_service.generate_additional_tests(existing_tests, models, "spec content")

    assert len(result) == 2
    assert result[0].path.endswith("Delete-DeleteUser.spec.ts")
    assert result[1].path.endswith("Put-UpdateUser.spec.ts")
    # Ensure invocation includes transformed inputs
    assert len(fake_chain.invocations) == 1
    inv = fake_chain.invocations[0]
    assert "tests" in inv and isinstance(inv["tests"], list)
    assert "models" in inv and isinstance(inv["models"], list)
    assert inv["api_definition"] == "spec content"


def test_generate_additional_tests_success_json_string(monkeypatch, llm_service):
    """generate_additional_tests handles JSON string output."""

    class FakeChain:
        def __init__(self, payload):
            self.payload = payload

        def invoke(self, _):
            return json.dumps(self.payload)

    payload = [
        {"path": "./tests/Patch-PartialUpdateUser.spec.ts", "fileContent": "// patch test"},
    ]
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain(payload))

    models = _build_generated_models()
    existing_tests = _build_file_specs_for_additional_tests()
    result = llm_service.generate_additional_tests(existing_tests, models, "spec content")
    assert len(result) == 1 and result[0].path.endswith("Patch-PartialUpdateUser.spec.ts")


def test_generate_additional_tests_chain_construction_arguments(monkeypatch, llm_service):
    """Ensure generate_additional_tests uses ADDITIONAL_TESTS prompt, FileCreationTool, must_use_tool True."""

    captured = {}

    class DummyChain:
        def invoke(self, _):
            return []

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        captured["must_use_tool"] = must_use_tool
        captured["tools"] = tools
        return DummyChain()

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    models = _build_generated_models()
    existing_tests = _build_file_specs_for_additional_tests()
    llm_service.generate_additional_tests(existing_tests, models, "spec content")

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.ADDITIONAL_TESTS
    assert captured["must_use_tool"] is True
    assert isinstance(captured["tools"], list) and len(captured["tools"]) == 1
    tool = captured["tools"][0]
    assert getattr(tool, "name", "") == "create_files"
    assert getattr(tool, "are_models", True) is False


def test_generate_additional_tests_malformed_json(monkeypatch, llm_service):
    """Malformed JSON should cause convert_to_file_spec to return empty list (handled upstream)."""

    class FakeChain:
        def invoke(self, _):
            return "{ malformed"

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())

    models = _build_generated_models()
    existing_tests = _build_file_specs_for_additional_tests()

    # Previously this raised JSONDecodeError. Behavior changed: service catches and returns [].
    result = llm_service.generate_additional_tests(existing_tests, models, "spec content")
    assert result == []


def test_generate_additional_tests_non_list_json(monkeypatch, llm_service):
    """Non-list JSON object should yield empty list."""

    class FakeChain:
        def invoke(self, _):
            return json.dumps({"path": "./tests/Single.spec.ts", "fileContent": "// single"})

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: FakeChain())
    models = _build_generated_models()
    existing_tests = _build_file_specs_for_additional_tests()
    result = llm_service.generate_additional_tests(existing_tests, models, "spec content")
    assert result == []


def test_generate_additional_tests_empty_list(monkeypatch, llm_service):
    """Empty list response should produce empty list output."""

    class FakeChain:
        def __init__(self):
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return []

    fake_chain = FakeChain()
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: fake_chain)
    models = _build_generated_models()
    existing_tests = _build_file_specs_for_additional_tests()
    result = llm_service.generate_additional_tests(existing_tests, models, "spec content")
    assert result == []
    assert len(fake_chain.invocations) == 1


# ---------------------- Tests for fix_typescript ---------------------- #


def _build_files_for_fix():
    from src.ai_tools.models.file_spec import FileSpec

    return [
        FileSpec(path="./src/models/UserModel.ts", fileContent="export interface User { id: string }"),
        FileSpec(path="./src/services/UserService.ts", fileContent="export class UserService {}"),
    ]


def test_fix_typescript_invokes_creation_tool_regular(monkeypatch, llm_service):
    """fix_typescript should construct a chain with FIX_TYPESCRIPT prompt and create_files tool (are_models False)."""

    captured = {}

    class DummyChain:
        def __init__(self):
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return []

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        captured["must_use_tool"] = must_use_tool
        captured["tools"] = tools
        return DummyChain()

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    files = _build_files_for_fix()
    messages = ["TS2345: Argument of type 'X' is not assignable to parameter of type 'Y'."]
    llm_service.fix_typescript(files, messages, are_models=False)

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.FIX_TYPESCRIPT
    assert captured["must_use_tool"] is True
    assert isinstance(captured["tools"], list) and len(captured["tools"]) == 1
    tool = captured["tools"][0]
    assert getattr(tool, "name", "") == "create_files"
    assert getattr(tool, "are_models", True) is False
    assert llm_service.get_aggregated_usage_metadata().total_fix_attempts == 1


def test_fix_typescript_invokes_creation_tool_models(monkeypatch, llm_service):
    """fix_typescript with are_models=True should set tool.are_models True and use same prompt."""

    captured = {}

    class DummyChain:
        def __init__(self):
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return []

    def spy_create_ai_chain(self, prompt_path, tools=None, must_use_tool=False, language_model=None):
        captured["prompt_path"] = prompt_path
        captured["tools"] = tools
        captured["must_use_tool"] = must_use_tool
        return DummyChain()

    monkeypatch.setattr(LLMService, "create_ai_chain", spy_create_ai_chain)

    files = _build_files_for_fix()
    llm_service.fix_typescript(files, ["error"], are_models=True)

    from src.services.llm_service import PromptConfig

    assert captured["prompt_path"] == PromptConfig.FIX_TYPESCRIPT
    assert captured["must_use_tool"] is True
    tool = captured["tools"][0]
    assert getattr(tool, "name", "") == "create_models"  # name changes when are_models True
    assert getattr(tool, "are_models", False) is True


def test_fix_typescript_empty_files(monkeypatch, llm_service):
    """Calling fix_typescript with empty files list should still invoke the chain (tool sees empty files)."""

    class DummyChain:
        def __init__(self):
            self.invocations = []

        def invoke(self, inputs):
            self.invocations.append(inputs)
            return []

    chain_instance = DummyChain()
    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: chain_instance)

    llm_service.fix_typescript([], ["no files errors"], are_models=False)

    # One invocation with empty list
    assert len(chain_instance.invocations) == 1
    invocation_payload = chain_instance.invocations[0]
    assert invocation_payload["files"] == []
    assert invocation_payload["messages"] == ["no files errors"]


def test_fix_typescript_handles_chain_exception_soft(monkeypatch, llm_service):
    """If the underlying chain raises, fix_typescript should log and swallow (soft-fail)."""

    class ExplodingChain:
        def invoke(self, _):
            raise RuntimeError("tool failure")

    monkeypatch.setattr(LLMService, "create_ai_chain", lambda self, *a, **k: ExplodingChain())

    files = _build_files_for_fix()
    # Should not raise after soft-fail change
    llm_service.fix_typescript(files, ["boom"], are_models=False)
