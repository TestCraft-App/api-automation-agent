from pydantic import Field
from .model_creation_input import ModelCreationInput


class ModelFixInput(ModelCreationInput):
    changes: str = Field(
        description="A string describing the changes needed to fix issues in the provided files. Phrased it in 'Do not do X. Solution is Y'",
        examples=[
            "Do not introduce not-used var errors, include in the file only what you will use.",
            "Do not access Arrays without checking for null or undefined indexes first. Guard against out-of-bounds errors using if(falsy) throw new Error('...')",
            "Do not use non-null assertion operator (!). Properly handle null and undefined values using conditional checks.",
        ],
    )
