from enum import Enum
from dataclasses import dataclass

from .model_fix_input import ModelFixInput
from .test_fix_input import TestFixInput

from .file_creation_input import FileCreationInput
from .file_spec import FileSpec
from .model_creation_input import ModelCreationInput
from .model_file_spec import ModelFileSpec


@dataclass(frozen=True)
class FileOperation:
    tool_name: str
    description: str
    input: type
    output_spec: type


class FileOperation(Enum):
    CREATE_MODELS = FileOperation(
        tool_name="create_models",
        description="Create models from a given API definition.",
        input=ModelCreationInput,
        output_spec=ModelFileSpec,
    )

    FIX_MODELS_COMPILATION = FileOperation(
        tool_name="fix_models_compilation",
        description="Fix compilation errors on Service files and Interfaces.",
        input=ModelFixInput,
        output_spec=ModelFileSpec,
    )
    CREATE_TEST = FileOperation(
        tool_name="create_test",
        description="Create test files using various sources of data",
        input=FileCreationInput,
        output_spec=FileSpec,
    )
    FIX_TEST_COMPILATION = FileOperation(
        tool_name="fix_test_compilation",
        description="Fix compilation errors in the test file.",
        input=TestFixInput,
        output_spec=FileSpec,
    )
    FIX_TEST_EXECUTION = FileOperation(
        tool_name="fix_test_execution",
        description="Fix execution errors based on various sources of data",
        input=TestFixInput,
        output_spec=FileSpec,
    )
