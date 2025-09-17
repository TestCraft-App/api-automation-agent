from typing import List, Optional
from pydantic import BaseModel, Field
from .file_creation_input import FileCreationInput


class FixStop(BaseModel):
    reason: str = Field(
        description="Enum value indicating the reason for stopping further fixes.", enum=["bug", "auth"]
    )
    content: List[str] = Field(
        description="Content in natural language documenting the reason for stopping further fixes.",
        examples=[
            "The API returns 200 on deleteProvider",
            "The API requires authentication which is not provided",
            "An empty response is returned on createProvider",
            "The API asks for an Oauth token which is not provided",
        ],
    )


class TestFixInput(FileCreationInput):
    changes: str = Field(
        description="A string describing the changes needed to fix issues in the provided files. Phrased it in 'Do not do X. Solution is Y'",
        examples=[
            "Do not use larger than 32 chars names for firstName. Use short, unique names instead.",
            "Don't assert status for for order deletion with status 204. Expect 200 instead.",
            "Don't expect a string in the 'Create new Order' Test, use AddOrderReponse[] as the response generic type and expect a single item array.",
        ],
    )
    stop: Optional[FixStop] = Field(
        default=None, description="Documents the reason to stop further fixes"
    )
