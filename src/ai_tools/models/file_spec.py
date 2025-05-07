from pydantic import BaseModel, Field


class FileSpec(BaseModel):
    path: str = Field(description="The relative file path including the filename.")
    fileContent: str = Field(
        description=(
            "The content of the file. This must be a valid JSON string. "
            "Any special characters that could cause issues when parsing "
            "the string as JSON should be escaped using a backslash (\\). "
            "Note: Do not escape single quotes ('), only special characters such as newlines, tabs, etc."
        ),
    )

    def to_json(self):
        return {"path": self.path, "fileContent": self.fileContent}
