from typing import List

from pydantic import BaseModel, Field


class FileReadingInput(BaseModel):
    files: List[str] = Field(description="A list of file paths to be read.")
