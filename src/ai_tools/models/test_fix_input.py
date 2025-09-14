from pydantic import Field
from .file_creation_input import FileCreationInput


class TestFixInput(FileCreationInput):
    changes: str = Field(
        description="A string describing the changes needed to fix issues in the provided files. Phrased it in 'Do not do X. Solution is Y'",
        examples=[
            "Do not use larger than 32 chars names for firstName. Use short, unique names instead.",
            "Don't assert status for for order deletion with status 204. Expect 200 instead.",
            "Don't expect a string in the 'Create new Order' Test, use AddOrderReponse[] as the response generic type and expect a single item array.",
        ],
    )
