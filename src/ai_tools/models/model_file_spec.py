from pydantic import Field

from .file_spec import FileSpec


class ModelFileSpec(FileSpec):
    summary: str = Field(
        description=(
            "A concise summary of the file's content using this format: "
            "For services: '<Name> service: <comma-separated list of methods>' "
            "For models: '<Name> model. Properties: <comma-separated list of properties>' "
            "For other files: A single sentence describing the file's main purpose."
        )
    )

    def to_json(self):
        return {
            "path": self.path,
            "fileContent": self.fileContent,
            "summary": self.summary,
        }
