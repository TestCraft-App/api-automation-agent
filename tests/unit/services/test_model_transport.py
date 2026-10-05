"""Verify provider wire requests using real LangChain clients and mocked transports."""

import json

import httpx
import pytest
from langchain_aws import ChatBedrockConverse
from langchain_openai import ChatOpenAI

from src.ai_tools.file_creation_tool import FileCreationTool
from src.configuration.config import Config
from src.configuration.models import Model
from src.services.file_service import FileService
from src.services.llm_service import LLMService


@pytest.mark.parametrize("model", [Model.GPT_6_1_SOL, Model.GPT_5_6_TERRA, Model.GPT_6_LUNA])
def test_openai_generation_sends_supported_tool_request(model, monkeypatch, tmp_path):
    args = {"files": [{"path": "sample.ts", "fileContent": "export const value = 1;"}]}
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        if model == Model.GPT_6_1_SOL:
            assert request.url.path == "/v1/responses"
            assert body["reasoning"] == {"effort": "low"}
            assert "temperature" not in body
            result = {
                "id": "resp_1",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": model.value,
                "output": [
                    {
                        "id": "fc_1",
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "create_files",
                        "arguments": json.dumps(args),
                        "status": "completed",
                    }
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "total_tokens": 12,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            }
        else:
            assert request.url.path == "/v1/chat/completions"
            assert body["reasoning_effort"] == "none"
            assert body["temperature"] == 1
            result = {
                "id": "chatcmpl_1",
                "object": "chat.completion",
                "created": 1,
                "model": model.value,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "create_files",
                                        "arguments": json.dumps(args),
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            }
        assert body["model"] == model.value
        assert body["tool_choice"] == "required"
        return httpx.Response(200, json=result)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(
            "src.services.llm_service.ChatOpenAI", lambda **kwargs: ChatOpenAI(**kwargs, http_client=client)
        )
        service = LLMService(
            Config(model=model, openai_api_key="test-key", destination_folder=str(tmp_path)), FileService()
        )
        tool = FileCreationTool(service.config, service.file_service)
        prompt_path = tmp_path / "prompt.txt"
        prompt_path.write_text("{task}")
        result = service.create_ai_chain(str(prompt_path), [tool], must_use_tool=True).invoke(
            {"task": "create sample.ts"}
        )
    assert len(requests) == 1
    assert "sample.ts" in result
    assert (tmp_path / "sample.ts").read_text() == "export const value = 1;"
    assert service.get_aggregated_usage_metadata().total_tokens == 12


@pytest.mark.parametrize(
    "model",
    [
        Model.BEDROCK_CLAUDE_OPUS_5_5,
        Model.BEDROCK_CLAUDE_SONNET_5_5,
        Model.BEDROCK_CLAUDE_HAIKU_4_5,
        Model.BEDROCK_GPT_6_1_SOL,
        Model.BEDROCK_GPT_5_6_TERRA,
        Model.BEDROCK_GPT_6_LUNA,
    ],
)
def test_bedrock_generation_sends_profile_and_supported_tool_choice(model, monkeypatch, tmp_path):
    requests = []

    class Client:
        def converse(self, **request):
            requests.append(request)
            return {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "toolUse": {
                                    "toolUseId": "call_1",
                                    "name": "create_files",
                                    "input": {
                                        "files": [
                                            {"path": "sample.ts", "fileContent": "export const value = 1;"}
                                        ],
                                    },
                                }
                            }
                        ],
                    }
                },
                "usage": {"inputTokens": 10, "outputTokens": 2, "totalTokens": 12},
                "stopReason": "tool_use",
                "metrics": {"latencyMs": 1},
                "ResponseMetadata": {"RequestId": "request_1", "HTTPStatusCode": 200},
            }

    monkeypatch.setattr(
        "src.services.llm_service.ChatBedrockConverse",
        lambda **kwargs: ChatBedrockConverse(
            **kwargs,
            client=Client(),
            bedrock_client=object(),
        ),
    )
    service = LLMService(Config(model=model, destination_folder=str(tmp_path)), FileService())
    tool = FileCreationTool(service.config, service.file_service)
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("{task}")
    result = service.create_ai_chain(str(prompt_path), [tool], must_use_tool=True).invoke(
        {"task": "create sample.ts"}
    )
    assert len(requests) == 1
    assert requests[0]["modelId"] == model.bedrock_invocation_id
    expected_choice = "any" if model.supports_forced_tool_use() else "auto"
    assert requests[0]["toolConfig"]["toolChoice"] == {expected_choice: {}}
    assert ("temperature" not in requests[0]["inferenceConfig"]) == model.uses_default_sampling()
    assert "sample.ts" in result
    assert service.get_aggregated_usage_metadata().total_tokens == 12
