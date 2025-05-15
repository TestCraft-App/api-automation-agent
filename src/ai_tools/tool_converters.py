from typing import List, Any

from langchain_anthropic import ChatAnthropic
from langchain_anthropic.chat_models import convert_to_anthropic_tool
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI


def convert_tool_for_model(tool: BaseTool, model: BaseLanguageModel) -> Any:
    """
    Convert a tool to the appropriate format for a specific language model.

    Args:
        tool (BaseTool): The tool to convert
        model (BaseLanguageModel): Target language model

    Returns:
        Converted tool compatible with the model
    """
    try:
        if isinstance(model, ChatAnthropic):
            return convert_to_anthropic_tool(tool)
        elif isinstance(model, ChatOpenAI):
            return convert_to_openai_tool(tool)
        else:
            raise ValueError(f"Unsupported model type: {type(model)}")
    except Exception as e:
        raise ValueError(f"Tool conversion error: {e}")


def convert_tools_for_model(tools: List[BaseTool], model: BaseLanguageModel) -> List[Any]:
    """
    Convert multiple tools for a specific language model.

    Args:
        tools (List[BaseTool]): List of tools to convert
        model (BaseLanguageModel): Target language model

    Returns:
        List of converted tools
    """
    return [convert_tool_for_model(tool, model) for tool in tools]
